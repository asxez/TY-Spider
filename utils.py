import copy
import ctypes
import math
import pickle
import sys
import time
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Callable, Any
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

try:
    import bitarray
except ImportError:
    raise ImportError('Requires bitarray')

try:
    import mmh3
except ImportError:
    raise ImportError('Requires mmh3')

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

    def schedule_interval(self, funcs: list[dict[str, Callable | int]], result: Any) -> None:
        scheduler = BackgroundScheduler()
        for func in funcs:
            if func['seconds'] > 60:  # 避免频繁的日志输出
                wrapped_func = self._logging(func['function'])
            else:
                wrapped_func = func['function']

            # 因为需要将func输出的结果保存，因此构造这个函数
            def _store_result() -> None:
                temp_result = wrapped_func()
                self.results['percentage'] = temp_result

            scheduler.add_job(
                _store_result,
                trigger=IntervalTrigger(seconds=func['seconds']),
            )
        scheduler.start()
        try:
            while True:
                if 'percentage' in self.results:
                    if self.results['percentage'] > result:
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

    def _parser(self, url) -> None:
        res = urlparse(url)
        self.netloc = res.netloc
        self.scheme = res.scheme
        self.path = res.path


class BloomFilter:

    def __init__(self, data_size: int, error_rate: float = 0.001):
        """
        :param data_size: 所需存放数据的数量
        :param error_rate:  误报率，默认0.001
        """

        if not data_size > 0:
            raise ValueError("数据量必须大于0")
        if not (0 < error_rate < 1):
            raise ValueError("错误率需在0到1之间")

        self._data_size = data_size
        self._error_rate = error_rate
        self._file_name = 'bloom.pkl'

        self._init_filter()

    def _init_filter(self) -> None:
        try:
            with open(f'./temp/{self._file_name}', 'rb') as file:
                data = pickle.load(file)
            self.__dict__.update(data)

        except (FileNotFoundError, pickle.UnpicklingError):
            bit_num, hash_num = self._adjust_param(self._data_size, self._error_rate)
            self._bit_array = bitarray.bitarray(bit_num)
            self._bit_array.setall(0)
            self._bit_num = bit_num
            self._hash_num = hash_num

            # 将哈希种子固定为 1 - hash_num （预留持久化过滤的可能）
            self._hash_seed = [i for i in range(1, hash_num + 1)]

            # 已存数据量
            self._data_count: int = 0
            self._save_state()

    @cost_time
    def _save_state(self) -> None:
        with open(f'./temp/{self._file_name}', 'wb') as file:
            pickle.dump(self.__dict__, file)

    def add(self, key: str) -> bool:
        for times in range(self._hash_num):
            key_hashed_idx = mmh3.hash(key, self._hash_seed[times]) % self._bit_num
            self._bit_array[key_hashed_idx] = 1

        self._data_count += 1
        self._save_state()
        return True

    def _contains(self, key: str) -> bool:
        """
        判断该值是否存在
        有任意一位为0 则肯定不存在
        """
        for times in range(self._hash_num):
            key_hashed_idx = mmh3.hash(key, self._hash_seed[times]) % self._bit_num
            if not self._bit_array[key_hashed_idx]:
                return False
        return True

    def copy(self) -> 'BloomFilter':
        """
        :return: 返回一个完全相同的布隆过滤器实例

        复制一份布隆过滤器的实例
        """
        new_filter = BloomFilter(self._data_size, self._error_rate)
        return self._copy_param(new_filter)

    def _copy_param(self, filter: 'BloomFilter') -> 'BloomFilter':
        filter._bit_array = copy.deepcopy(self._bit_array)
        filter._bit_num = self._bit_num
        filter._hash_num = self._hash_num
        filter._hash_seed = copy.deepcopy(self._hash_seed)
        filter._data_count = self._data_count
        return filter

    @staticmethod
    def _adjust_param(data_size: int, error_rate: float) -> tuple[int, int]:
        """
        :param data_size:
        :param error_rate:
        :return:

        通过数据量和期望的误报率 计算出 位数组大小 和 哈希函数的数量
        k为哈希函数个数    m为位数组大小
        n为数据量          p为误报率
        m = - (n * lnp) / (ln2)^2

        k = (m / n) * ln2
        """
        p = error_rate
        n = data_size
        m = - (n * (math.log(p, math.e)) / (math.log(2, math.e)) ** 2)
        k = m / n * math.log(2, math.e)
        return int(m), int(k)

    def __len__(self) -> int:
        """"
        返回现有数据容量
        """
        return self._data_count

    def __contains__(self, key) -> bool:
        return self._contains(key)
