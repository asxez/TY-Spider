from random import uniform
from time import sleep

from loguru import logger

from config import db_name, data_col_name, key_col_name
from data_process import ReverseIndex, BackLink
from database import MongoDB
from log_lg import ManageLog
from mongodb import del_repeat, find_all
from utils import Schedule, ParserLink, cost_time


class Task:
    def __init__(self):
        ManageLog()

    @staticmethod
    def mongodb() -> None:
        with MongoDB(db_name, data_col_name) as db:
            del_repeat(db.col, 'href', data_col_name)
        with MongoDB(db_name, key_col_name) as db:
            del_repeat(db.col, 'key', key_col_name)

    @staticmethod
    @cost_time
    def make_index() -> None:
        index = ReverseIndex()
        i = 1
        with MongoDB(db_name, data_col_name) as db:
            a = list(find_all(db.col))
        while True:
            ans = index.build_index(a[i * 20 - 20:i * 20], i - 1)
            if ans:
                index.save_index()
                i = i + 1
                sleep(uniform(0.1, 0.4))
            else:
                break

    @staticmethod
    @cost_time
    def back_link():
        bl = BackLink()
        with MongoDB(db_name, data_col_name) as db:
            datas = list(find_all(db.col, {
                '_id': 0,
                'keywords': 0,
                'description': 0,
                'netloc': 0,
                'weight': 0,
                'title': 0
            }))
        for data in datas:
            a = data['href']  # 数据库内所有链接
            netloc = ParserLink(a).netloc
            hrefs = bl.requests(a)
            if hrefs:
                for href in hrefs:
                    bl.add(str(netloc), str(href))
                    logger.info(f'{href}已处理')

        for url, locs in bl.map.items():
            length = len(locs)
            _sum = 0
            for loc in locs:
                with MongoDB(db_name, data_col_name) as db:
                    col = db.col
                    weights = [weight['weight'] for weight in col.find({'netloc': loc}, projection={
                        '_id': 0,
                        'keywords': 0,
                        'description': 0,
                        'netloc': 0,
                        'href': 0,
                        'title': 0
                    })]
                    logger.info(weights)
                _sum = sum(weights) + _sum
            with MongoDB(db_name, data_col_name) as db:
                col = db.col
                col.update_many({'href': url}, {'$inc': {'weight': _sum / length}})


if __name__ == '__main__':
    task = Task()
    task1 = {
        'function': task.mongodb,
        'hour': 0,
        'minute': 0,
        'args': None
    }
    task2 = {
        'function': task.make_index,
        'hour': 0,
        'minute': 10,
        'args': None
    }
    task3 = {
        'function': task.back_link,
        'hour': 3,
        'minute': 0,
        'args': None
    }
    Schedule().schedule_cron([task1, task2, task3])
