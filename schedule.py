from typing import Callable
from datetime import date

from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def logging(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        logger.info(f"{func.__name__}: {date.today()}")
        return func(*args, **kwargs)

    return wrapper


def schedule(func: Callable, args: tuple, hour: int, minute: int) -> None:
    scheduler = BackgroundScheduler()
    wrapped_func = logging(func)

    scheduler.add_job(wrapped_func, trigger=CronTrigger(hour=hour, minute=minute), args=args)
    scheduler.start()

    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
