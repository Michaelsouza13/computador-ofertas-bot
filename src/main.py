import sys
import os

os.environ.setdefault("CACHE_DIR", "cache")

from src.logging_config import setup_logging
from src.bot import main

run_id = setup_logging()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import logging
        logger = logging.getLogger("bot")
        logger.critical("bot_crashed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
        })
        raise
