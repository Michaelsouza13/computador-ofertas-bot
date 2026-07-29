import logging
from statistics import mean
from typing import Optional

logger = logging.getLogger("score.historical")


class HistoricalAnalyzer:
    def __init__(self, price_history: dict):
        self.price_history = price_history

    def analyze(self, product_id: str, current_price: float, listed_original: Optional[float] = None) -> dict:
        history = self.price_history.get(product_id, {}).get("prices", [])
        if not history:
            return {
                "score": 50.0,
                "avg_30d": None,
                "min_30d": None,
                "fake_discount": False,
                "real_discount_pct": 0.0,
            }

        prices = [h["price"] for h in history if h.get("price", 0) > 0]
        if not prices:
            return {
                "score": 50.0,
                "avg_30d": None,
                "min_30d": None,
                "fake_discount": False,
                "real_discount_pct": 0.0,
            }

        avg = mean(prices)
        mn = min(prices)

        fake_discount = False
        if listed_original and listed_original > avg * 1.3:
            fake_discount = True
            logger.warning("fake_discount_detected", extra={
                "product_id": product_id,
                "listed_original": listed_original,
                "historical_avg": round(avg, 2),
                "inflation_ratio": round(listed_original / avg, 2),
            })

        real_discount = 0.0
        if avg > 0:
            real_discount = (1 - current_price / avg) * 100

        score = 50.0
        if real_discount >= 15:
            score = 90.0
        elif real_discount >= 10:
            score = 75.0
        elif real_discount >= 5:
            score = 60.0
        elif real_discount > 0:
            score = 45.0
        else:
            score = 20.0

        if fake_discount:
            score *= 0.3

        return {
            "score": score,
            "avg_30d": round(avg, 2),
            "min_30d": round(mn, 2),
            "fake_discount": fake_discount,
            "real_discount_pct": round(real_discount, 1),
        }
