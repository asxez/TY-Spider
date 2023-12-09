import ctypes
import sys
import time
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Callable
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

_lang_model = None  # 全局变量，以免重复加载模型


@dataclass
class _C_U:
    c_ulong = ctypes.c_ulong
    c_ulonglong = ctypes.c_ulonglong


def cost_time(func: Callable) -> Callable:
    def fun(*args, **kwargs):
        t = perf_counter()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} 耗时：{perf_counter() - t:.8f}s")
        return result

    return fun


def check_lang(s: str) -> tuple[str, float]:
    global _lang_model
    if not _lang_model:
        import fasttext
        try:
            fasttext.FastText.eprint = lambda *args, **kwargs: None
        except Exception:
            pass
        _lang_model = fasttext.load_model('lid.176.ftz')
    res = _lang_model.predict(s.replace('\n', ''))
    lang = res[0][0][9:]
    like = res[1][0]
    return str(lang), float(like)


class Schedule:
    """
    定时模块
    _logging()  输出日志
    schedule_cron()  Linux-cron类型定时
    schedule_interval()  间隔时间定时
    """

    def __init__(self):
        self.results = {}

    @staticmethod
    def _logging(function: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            now_time = time.localtime()
            logger.info(f"{function.__name__}: {date.today()} {now_time.tm_hour}:{now_time.tm_min}")
            return function(*args, **kwargs)

        return wrapper

    def schedule_cron(self, funcs: list[dict[str, Callable | int | tuple]]) -> None:
        scheduler = BackgroundScheduler()
        for func in funcs:
            wrapped_func = self._logging(func['function'])
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

    def schedule_interval(self, funcs: list[dict[str, Callable | int]]) -> None:
        scheduler = BackgroundScheduler()
        for func in funcs:
            wrapped_func = self._logging(func['function'])

            # 因为需要将func输出的结果保存，因此构造这个函数
            def _store_result():
                result = wrapped_func()
                self.results['percentage'] = result

            scheduler.add_job(
                _store_result,
                trigger=IntervalTrigger(seconds=func['seconds']),
            )
        scheduler.start()
        try:
            while True:
                if 'is_ok' in self.results:
                    if self.results['percentage'] > 0.1:
                        break
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()


class Memory:
    @staticmethod
    def get_memory_info() -> dict | bool:
        if sys.platform == 'win32':
            kernel32 = ctypes.windll.kernel32

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", _C_U.c_ulong),
                    ("dwMemoryLoad", _C_U.c_ulong),
                    ("ullTotalPhys", _C_U.c_ulonglong),
                    ("ullAvailPhys", _C_U.c_ulonglong),
                    ("ullTotalPageFile", _C_U.c_ulonglong),
                    ("ullAvailPageFile", _C_U.c_ulonglong),
                    ("ullTotalVirtual", _C_U.c_ulonglong),
                    ("ullAvailVirtual", _C_U.c_ulonglong),
                    ("sullAvailExtendedVirtual", _C_U.c_ulonglong)
                ]

            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(memory_status)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))

            meminfo = {
                "TPM": memory_status.ullTotalPhys,
                "APM": memory_status.ullAvailPhys,
            }
            return meminfo
        return False

    def canuse_memory_percentage(self) -> int:
        memory_info = self.get_memory_info()
        return round((memory_info['APM'] / (1024 ** 3)) / (memory_info['TPM'] / (1024 ** 3)), 3)


class ParserLink:
    def __init__(self, url):
        self.netloc = None
        self.scheme = None
        self.path = None
        self._parser(url)

    def _parser(self, url):
        res = urlparse(url)
        self.netloc = res.netloc
        self.scheme = res.scheme
        self.path = res.path
