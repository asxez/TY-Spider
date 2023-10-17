from loguru import logger
from pymongo import MongoClient

from config import mongodb_host, mongodb_port


class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.col = None
        self.closed = False

    def __enter__(self):
        self.client = MongoClient(host=mongodb_host, port=mongodb_port)
        self.db = self.client['datas']
        self.col = self.db['sites']
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.closed:
            if exc_type is not None:
                logger.error(f'出现错误：{exc_type}-{exc_val}-{exc_tb}')
            self.client.close()
            self.closed = True
