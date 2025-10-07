# scraper_cron_job.py
import asyncio
import argparse
from datetime import datetime, timedelta, timezone

from app.tasks import scrape_and_save_trail
from app.database import connect_to_mongo, close_mongo_connection
from app import database_service
from app.services.data_fetcher import get_all_reviews_for_trail


async def update_reviews_for_trail(trail_id: int):
    """只更新指定步道的評論和最後更新時間"""
    print(f"增量更新：正在更新步道 {trail_id} 的評論...")
    new_reviews = await get_all_reviews_for_trail(trail_id)

    if new_reviews:
        await database_service.add_new_reviews_to_trail(
            trail_id, new_reviews, datetime.now(timezone.utc)
        )
    else:
        # 即使沒有抓到評論，也更新時間，表示我們檢查過了
        await database_service.add_new_reviews_to_trail(
            trail_id, [], datetime.now(timezone.utc)
        )


async def run_full_scan(start_id: int, end_id: int):
    """執行全量掃描"""
    print(f"全量掃描啟動：開始爬取步道 ID 從 {start_id} 到 {end_id}...")
    for trail_id in range(start_id, end_id + 1):
        if not await database_service.is_trail_valid(trail_id):
            print(f"Skipping known invalid ID: {trail_id}")
            continue
        try:
            await scrape_and_save_trail(trail_id)
        except Exception as e:
            print(f"處理步道 ID {trail_id} 時發生嚴重錯誤: {e}")
        await asyncio.sleep(1)


async def run_incremental_scan(probe_limit: int):
    """執行增量掃描"""
    # --- 階段一：探測新 ID ---
    print("--- 階段一：探測新 ID ---")
    max_id = await database_service.get_max_trail_id()
    print(f"目前資料庫中最大 ID 為: {max_id}")

    consecutive_failures = 0
    for new_id in range(max_id + 1, max_id + 1 + probe_limit):
        if not await database_service.is_trail_valid(new_id):
            print(f"Skipping known invalid ID: {new_id}")
            continue

        await scrape_and_save_trail(new_id)

        if await database_service.get_trail_by_id(new_id):
            consecutive_failures = 0
        else:
            consecutive_failures += 1

        if consecutive_failures >= 20:
            print("連續 20 次探測失敗，結束探測階段。")
            break
        await asyncio.sleep(1)

    # --- 階段二：僅更新舊有資料的評論 ---
    print("--- 階段二：僅更新舊有資料的評論 ---")
    all_ids = await database_service.get_all_trail_ids()
    print(f"將對 {len(all_ids)} 筆已存在資料進行評論增量更新...")
    for trail_id in all_ids:
        try:
            # 檢查上次更新時間
            last_scraped = await database_service.get_trail_last_scraped_at(trail_id)
            if last_scraped and (datetime.now(timezone.utc) - last_scraped) < timedelta(
                days=6
            ):
                print(f"Skipping trail ID: {trail_id}, last updated within 6 days.")
                continue

            await update_reviews_for_trail(trail_id)
        except Exception as e:
            print(f"更新步道 {trail_id} 評論時發生錯誤: {e}")

        # 確認每筆處理之間都有間隔
        await asyncio.sleep(1)


async def main():
    parser = argparse.ArgumentParser(description="健行筆記步道資料爬取排程作業")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "incremental"],
        required=True,
        help="執行模式：'full' (全量掃描), 'incremental' (增量更新)",
    )
    parser.add_argument("--start-id", type=int, default=1, help="全量掃描的起始 ID")
    parser.add_argument("--end-id", type=int, default=2300, help="全量掃描的結束 ID")
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=400,
        help="增量更新時，向上探測新 ID 的最大數量",
    )
    args = parser.parse_args()

    await connect_to_mongo()

    if args.mode == "full":
        await run_full_scan(args.start_id, args.end_id)
    elif args.mode == "incremental":
        await run_incremental_scan(args.probe_limit)

    await close_mongo_connection()
    print("排程作業完成。")


if __name__ == "__main__":
    asyncio.run(main())
