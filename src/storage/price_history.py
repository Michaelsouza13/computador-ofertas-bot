import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("storage.price_history")

HISTORY_DIR = Path("cache")
HISTORY_FILE = HISTORY_DIR / "price_history.json"
MAX_PRODUCTS = 500
MAX_ENTRIES_PER_PRODUCT = 60


class PriceHistory:
    def __init__(self):
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if not HISTORY_FILE.exists():
            logger.info("no_history_found")
            return {}
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            logger.info("history_loaded", extra={
                "products": len(data),
                "total_entries": sum(len(v.get("prices", [])) for v in data.values()),
            })
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("history_load_failed", extra={"error": str(e)})
            return {}

    def save(self):
        trimmed = dict(list(self.data.items())[-MAX_PRODUCTS:])
        for pid in trimmed:
            trimmed[pid]["prices"] = trimmed[pid]["prices"][-MAX_ENTRIES_PER_PRODUCT:]
        HISTORY_FILE.write_text(
            json.dumps(trimmed, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        total = sum(len(v.get("prices", [])) for v in trimmed.values())
        logger.info("history_saved", extra={"products": len(trimmed), "entries": total})

    def record_price(self, product_id: str, price: float, platform: str = ""):
        import datetime
        if product_id not in self.data:
            self.data[product_id] = {"prices": [], "platforms": []}
        entry = {
            "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            "price": price,
        }
        self.data[product_id]["prices"].append(entry)
        if platform and platform not in self.data[product_id]["platforms"]:
            self.data[product_id]["platforms"].append(platform)

    def get_platforms_for(self, product_id: str) -> list:
        return self.data.get(product_id, {}).get("platforms", [])

    def record_offer(self, offer):
        self.record_price(offer.product_id, offer.current_price, offer.platform)
