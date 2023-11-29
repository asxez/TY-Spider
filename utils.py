from time import perf_counter
from typing import Callable

from loguru import logger


def cost_time(func: Callable) -> Callable:
    def fun(*args, **kwargs):
        t = perf_counter()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} 耗时：{perf_counter() - t:.8f}s")
        return result

    return fun
