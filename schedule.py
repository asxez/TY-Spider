import time
from datetime import date
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


def logging(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        now_time = time.localtime()
        logger.info(f"{func.__name__}: {date.today()} {now_time.tm_hour}:{now_time.tm_min}")
        return func(*args, **kwargs)

    return wrapper


def schedule(funcs: list[dict[str, Callable | int | tuple]]) -> None:
    scheduler = BackgroundScheduler()
    for func in funcs:
        wrapped_func = logging(func['function'])
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
