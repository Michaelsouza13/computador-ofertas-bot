import json
import logging
from pathlib import Path

logger = logging.getLogger("storage.cache")

CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "sent_offers.json"
MAX_CACHE_SIZE = 2000


class Cache:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if not CACHE_FILE.exists():
            logger.info("no_cache_found")
            return {}
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if len(data) > MAX_CACHE_SIZE:
                    data = dict(list(data.items())[-MAX_CACHE_SIZE:])
                logger.info("cache_loaded", extra={"size": len(data)})
                return data
            return {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("cache_load_failed", extra={"error": str(e)})
            return {}

    def save(self):
        trimmed = dict(list(self.data.items())[-MAX_CACHE_SIZE:])
        CACHE_FILE.write_text(
            json.dumps(trimmed, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("cache_saved", extra={"size": len(trimmed)})

    def contains(self, offer_id: str) -> bool:
        return offer_id in self.data

    def add(self, offer_id: str):
        import time
        self.data[offer_id] = time.time()
