import logging, time, functools
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("orchestrator")


@contextmanager
def trace_span(name: str):
    start = time.perf_counter()
    logger.info("[START] %s", name)
    try:
        yield
    except Exception as e:
        logger.error("[ERROR] %s | %s", name, e)
        raise
    finally:
        elapsed = time.perf_counter() - start
        logger.info("[END] %s | %.3fs", name, elapsed)


def timed(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.info("[TIMED] %s | %.3fs", func.__name__, elapsed)
    return wrapper
