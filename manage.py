import time
from datetime import date
from random import uniform
from time import sleep
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config import db_name, data_col_name, key_col_name
from data_process import ReverseIndex
from database import MongoDB
from log_lg import ManageLog
from mongodb import del_repeat, find_all


def _logging(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        now_time = time.localtime()
        logger.info(f"{func.__name__}: {date.today()} {now_time.tm_hour}:{now_time.tm_min}")
        return func(*args, **kwargs)

    return wrapper


def schedule(funcs: list[dict[str, Callable | int | tuple]]) -> None:
    scheduler = BackgroundScheduler()
    for func in funcs:
        wrapped_func = _logging(func['function'])
        scheduler.add_job(
            wrapped_func,
            trigger=CronTrigger(hour=func['hour'], minute=func['minute']),
            args=func['args']
        )
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


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
    schedule([task1, task2])
