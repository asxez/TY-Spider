from typing import Any

from loguru import logger
from pymongo import MongoClient

from config import mongodb_host, mongodb_port


class MongoDB:
    def __init__(self, db_name: str, col_name: str):
        self.client = None
        self.db = None
        self.col = None
        self.closed = False
        self.db_name = db_name
        self.col_name = col_name

    def __enter__(self) -> 'MongoDB':
        self.client = MongoClient(host=mongodb_host, port=mongodb_port)
        self.db = self.client[self.db_name]
        self.col = self.db[self.col_name]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if not self.closed:
                if exc_type is not None:
                    logger.error(f'出现错误：{exc_type}-{exc_val}-{exc_tb}')
                self.client.close()
                self.closed = True
        finally:
            if self.client:
                self.client.close()
