# app/tasks.py
import asyncio
from datetime import datetime, timezone

from app import database_service
from app.logger import logger
from app.models import TrailDocument
from app.services.data_fetcher import get_all_reviews_for_trail
from app.services.trail_scraper import scrape_trail_details


async def scrape_and_save_trail(trail_id: int):
    """
    整合爬取和儲存單個步道資料的完整流程。
    """
    logger.info(f"開始爬取步道 ID: {trail_id}...")

    details_task = scrape_trail_details(trail_id)
    reviews_task = get_all_reviews_for_trail(trail_id)

    details, reviews = await asyncio.gather(details_task, reviews_task)

    if not details:
        logger.warning(f"無法獲取步道 {trail_id} 的基本資料，將其標記為無效 ID。")
        await database_service.add_invalid_trail_id(trail_id)
        return

    trail_doc = TrailDocument(
        _id=trail_id,
        last_scraped_at=datetime.now(timezone.utc),
        reviews=reviews,
        **details,
    )

    await database_service.update_trail(trail_doc)
    logger.info(f"成功儲存步道 ID: {trail_id} 的資料。")
