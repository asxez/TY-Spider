import time
import pymongo
from typing import Any, Mapping, Callable
from pymongo.cursor import Cursor
from loguru import logger
from database import MongoDB


def cost_time(func: Callable) -> Callable:
    def fun(*args, **kwargs):
        t = time.perf_counter()
        result = func(*args, **kwargs)
        logger.info(f'{func.__name__} 耗时：{time.perf_counter() - t:.8f}s')
        return result

    return fun


@cost_time
def save_data(datas: list, col: pymongo.MongoClient) -> None:
    if len(datas) == 0:
        logger.info('保存数据时所接受的列表为空')
        return
    col.insert_many(datas)


@cost_time
def del_repeat(col: pymongo.MongoClient) -> None:
    pipeline = [
        {
            '$group': {
                '_id': '$href',  # 根据href字段去重
                'doc_id': {'$first': '$_id'},  # 保留第一个文档的_id字段
                'doc': {'$first': '$$ROOT'}  # 保留第一个完整文档
            }
        },
        {
            '$replaceRoot': {
                'newRoot': '$doc'  # 使用$replaceRoot将文档重新变回根文档，保留原始字段
            }
        },
        {
            '$out': 'sites'  # 将去重后的结果写入新集合，此处为覆盖原集合
        }
    ]
    col.aggregate(pipeline=pipeline)


@cost_time
def delete_keywords_and_description(col: pymongo.MongoClient, description: str = "", word: str = "",
                                    title: str = "") -> None:
    query = {
        "$and": [
            {"description": {"$eq": description}},
            {"word": {"$eq": word}},
            {"title": {"$eq": title}}
        ]
    }
    result = col.delete_many(query)
    logger.info(f'删除了 {result.deleted_count} 条数据')


@cost_time
def search_data(text: str, col: pymongo.MongoClient) -> Cursor[Mapping[str, Any]]:
    query = {
        "$or": [
            {"word": {"$regex": text, "$options": "i"}},
            {"description": {"$regex": text, "$options": "i"}},
            {"title": {"$regex": text, "$options": "i"}}
        ]
    }
    results = col.find(query)
    return results


@cost_time
def creat_index(col: pymongo.MongoClient) -> None:
    index = [('description', pymongo.ASCENDING), ('word', pymongo.ASCENDING), ('title', pymongo.ASCENDING)]
    col.create_index(index)


if __name__ == '__main__':
    with MongoDB() as db:
        del_repeat(db.col)
    # threading.Thread(target=get_response_from_bfs).start()
