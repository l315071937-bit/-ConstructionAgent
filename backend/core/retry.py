import time
from functools import wraps

from core.logger import get_logger

logger = get_logger("retry")


def retry(max_attempts: int = 3, base_delay: float = 1.0, exceptions=(Exception,)):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning("retry %s/%s for %s: %s", attempt, max_attempts, fn.__name__, e)
                    time.sleep(delay)
        return wrapper
    return deco
