import functools
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger("utils.decorators")


def log_performance(log: Optional[logging.Logger] = None):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _log = log or logging.getLogger(func.__module__)
            t0 = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.monotonic() - t0) * 1000
                _log.debug("perf_ok", extra={
                    "func": func.__name__,
                    "duration_ms": round(elapsed, 1),
                    "module": func.__module__,
                })
                return result
            except Exception as e:
                elapsed = (time.monotonic() - t0) * 1000
                _log.error("perf_fail", extra={
                    "func": func.__name__,
                    "duration_ms": round(elapsed, 1),
                    "error": str(e),
                    "module": func.__module__,
                })
                raise
        return wrapper
    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 5.0,
    backoff_factor: float = 2.0,
    log: Optional[logging.Logger] = None,
):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _log = log or logging.getLogger(func.__module__)
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt == max_retries - 1:
                        _log.error("retry_exhausted", extra={
                            "func": func.__name__,
                            "attempts": max_retries,
                            "error": str(e),
                        })
                        raise
                    delay = base_delay * (backoff_factor ** attempt)
                    _log.warning("retry_attempt", extra={
                        "func": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay_s": delay,
                        "error": str(e),
                    })
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
