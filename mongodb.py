from typing import Any, Mapping

from loguru import logger
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.cursor import Cursor

from utils import cost_time


@cost_time
def save_data(datas: list, col: Collection) -> None:
    if len(datas) == 0:
        logger.info("保存数据时所接受的列表为空")
        return None
    col.insert_many(datas)


@cost_time
def del_repeat(col: Collection, text: str, out: str) -> None:
    pipeline = [
        {
            "$group": {
                "_id": f"${text}",  # 根据{text}字段去重
                "doc_id": {"$first": "$_id"},  # 保留第一个文档的_id字段
                "doc": {"$first": "$$ROOT"}  # 保留第一个完整文档
            }
        },
        {
            "$replaceRoot": {
                "newRoot": "$doc"  # 使用$replaceRoot将文档重新变回根文档，保留原始字段
            }
        },
        {
            "$out": f"{out}"  # 将去重后的结果写入新集合，此处为覆盖原集合
        }
    ]
    col.aggregate(pipeline=pipeline)


@cost_time
def delete_keywords_and_description(
        col: Collection,
        description: str = "",
        word: str = "",
        title: str = ""
) -> None:
    query = {
        "$and": [
            {"description": {"$eq": description}},
            {"keywords": {"$eq": word}},
            {"title": {"$eq": title}}
        ]
    }
    result = col.delete_many(query)
    logger.info(f"删除了 {result.deleted_count} 条数据")


@cost_time
def search_data(text: str, col: Collection) -> Cursor[Mapping[str, Any]]:
    query = {
        "$or": [
            {"keywords": {"$regex": text, "$options": "i"}},
            {"description": {"$regex": text, "$options": "i"}},
            {"title": {"$regex": text, "$options": "i"}}
        ]
    }
    results = col.find(query, projection={"_id": 0})
    return results


@cost_time
def find_all(col: Collection) -> Cursor[Mapping[str, Any]]:
    return col.find()


@cost_time
def creat_index(col: Collection) -> None:
    index = [("description", ASCENDING), ("keywords", ASCENDING), ("title", ASCENDING)]
    col.create_index(index)


@cost_time
def update(col: Collection, query: dict[str, str], new_value: dict[dict[str, str]]) -> None:
    result = col.update_one(query, new_value)
    if result.modified_count > 0:
        logger.info('数据更新成功')
    else:
        logger.warning('数据更新失败')
