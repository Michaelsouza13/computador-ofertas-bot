import logging
import logging.config
import os
import sys
import uuid
from pathlib import Path

RUN_ID = uuid.uuid4().hex[:12]
RUN_DIR = Path(f"logs/run_{RUN_ID}")


class RunIDFilter(logging.Filter):
    def filter(self, record):
        record.run_id = RUN_ID
        return True


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "run_id": {
            "()": RunIDFilter,
        },
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(asctime)s %(name)s %(levelname)s "
                "%(message)s %(run_id)s"
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
        "console": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "console",
            "level": "INFO",
        },
        "json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(RUN_DIR / "bot.json"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 2,
            "formatter": "json",
            "level": "DEBUG",
            "encoding": "utf-8",
            "filters": ["run_id"],
        },
        "errors_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(RUN_DIR / "errors.json"),
            "maxBytes": 2 * 1024 * 1024,
            "backupCount": 2,
            "formatter": "json",
            "level": "WARNING",
            "encoding": "utf-8",
            "filters": ["run_id"],
        },
    },
    "loggers": {
        "bot": {"level": "DEBUG", "propagate": True},
        "scrapers": {"level": "DEBUG", "propagate": True},
        "senders": {"level": "DEBUG", "propagate": True},
        "storage": {"level": "DEBUG", "propagate": True},
        "score": {"level": "DEBUG", "propagate": True},
        "utils": {"level": "INFO", "propagate": True},
    },
    "root": {
        "handlers": ["console", "json_file", "errors_file"],
        "level": "INFO",
    },
}


def setup_logging():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "summary.json").write_text(
        '{"run_id":"' + RUN_ID + '","status":"running"}', encoding="utf-8"
    )
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger("bot").info("logging_ready")
    return RUN_ID
