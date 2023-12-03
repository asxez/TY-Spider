from time import perf_counter
from typing import Callable, Any

from loguru import logger

_lang_model = None


def cost_time(func: Callable) -> Callable:
    def fun(*args, **kwargs):
        t = perf_counter()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} 耗时：{perf_counter() - t:.8f}s")
        return result

    return fun


def check_lang(s: str) -> tuple[Any, Any]:
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
    return lang, like
