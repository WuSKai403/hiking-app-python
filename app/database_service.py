# app/database_service.py

from app.database import db_client
from app.models import TrailDocument
from typing import Optional
from datetime import datetime
import os
from fastapi import HTTPException

# 定義集合名稱，允許被環境變數覆蓋以利測試
TRAIL_COLLECTION = os.getenv("TRAIL_COLLECTION_NAME", "trails")
INVALID_ID_COLLECTION = os.getenv("INVALID_ID_COLLECTION_NAME", "invalid_trail_ids")


async def add_invalid_trail_id(trail_id: int):
    """將無效的 trail_id 記錄到資料庫中"""
    collection = db_client.db[INVALID_ID_COLLECTION]
    # 使用 upsert 避免重複記錄
    await collection.update_one(
        {"_id": trail_id}, {"$set": {"_id": trail_id}}, upsert=True
    )


async def is_invalid_trail_id(trail_id: int) -> bool:
    """檢查指定的 trail_id 是否已被記錄為無效"""
    collection = db_client.db[INVALID_ID_COLLECTION]
    return await collection.find_one({"_id": trail_id}) is not None


async def get_trail_by_id(trail_id: int) -> Optional[TrailDocument]:
    """
    根據 trail_id 從 MongoDB 中查找步道資料。
    """
    collection = db_client.db[TRAIL_COLLECTION]
    trail_data = await collection.find_one({"_id": trail_id})
    if trail_data:
        return TrailDocument(**trail_data)
    return None


async def update_trail(trail_document: TrailDocument) -> None:
    """
    將步道資料更新或插入 (upsert) 到 MongoDB 中。
    """
    collection = db_client.db[TRAIL_COLLECTION]
    await collection.replace_one(
        {"_id": trail_document.id},
        trail_document.model_dump(by_alias=True),
        upsert=True,
    )


async def get_max_trail_id() -> int:
    """獲取目前資料庫中最大的 trail_id"""
    collection = db_client.db[TRAIL_COLLECTION]
    max_id_doc = await collection.find_one(sort=[("_id", -1)])
    return max_id_doc["_id"] if max_id_doc else 0


async def get_all_trail_ids() -> list[int]:
    """獲取資料庫中所有已存在的 trail_id"""
    collection = db_client.db[TRAIL_COLLECTION]
    cursor = collection.find({}, {"_id": 1})
    return [doc["_id"] async for doc in cursor]


async def get_trail_last_scraped_at(trail_id: int) -> Optional[datetime]:
    """獲取指定 trail_id 的最後抓取時間"""
    collection = db_client.db[TRAIL_COLLECTION]
    doc = await collection.find_one({"_id": trail_id}, {"last_scraped_at": 1})
    return doc["last_scraped_at"] if doc else None


async def get_trail_data_from_db(trail_id: int) -> TrailDocument:
    """
    從資料庫獲取步道資料，如果不存在，則拋出 404 錯誤。
    """
    trail_data = await get_trail_by_id(trail_id)
    if not trail_data:
        raise HTTPException(
            status_code=404,
            detail=f"資料庫中尚無步道 ID: {trail_id} 的資料，請先執行爬蟲。",
        )
    return trail_data


async def add_new_reviews_to_trail(
    trail_id: int, new_reviews: list, last_scraped_at: datetime
):
    """
    將新的評論增量更新到指定的 trail_id。
    只寫入資料庫中不存在的新評論。
    """
    collection = db_client.db[TRAIL_COLLECTION]

    # 1. 獲取現有文檔
    trail_doc = await collection.find_one({"_id": trail_id})
    if not trail_doc:
        print(f"警告: 嘗試為不存在的 trail_id={trail_id} 更新評論。")
        return

    # 2. 將現有評論轉換為一個可快速查找的集合 (set)
    existing_reviews_set = {
        (review["user_id"], review["review_date"], review["content"])
        for review in trail_doc.get("reviews", [])
    }

    # 3. 找出真正新的評論
    reviews_to_add = []
    for new_review in new_reviews:
        review_tuple = (new_review.user_id, new_review.review_date, new_review.content)
        if review_tuple not in existing_reviews_set:
            reviews_to_add.append(new_review)

    # 4. 如果有新評論，則使用 $addToSet 和 $set 進行更新
    if reviews_to_add:
        print(f"發現 {len(reviews_to_add)} 則新評論 for trail_id={trail_id}。")
        await collection.update_one(
            {"_id": trail_id},
            {
                "$addToSet": {
                    "reviews": {"$each": [r.model_dump() for r in reviews_to_add]}
                },
                "$set": {"last_scraped_at": last_scraped_at},
            },
        )
    else:
        print(f"Trail_id={trail_id} 沒有新評論，只更新時間。")
        # 即使沒有新評論，也更新最後抓取時間
        await collection.update_one(
            {"_id": trail_id}, {"$set": {"last_scraped_at": last_scraped_at}}
        )
