import logging
from typing import Optional

from src.models.offer import Offer, ScoreResult, ScoreCategory
from src.score.historical import HistoricalAnalyzer
from src.score.rules import QualityRules

logger = logging.getLogger("score.engine")

SCORE_THRESHOLDS = {
    ScoreCategory.EXCELLENT: 80,
    ScoreCategory.GOOD: 60,
    ScoreCategory.MEDIUM: 40,
    ScoreCategory.WEAK: 0,
}


class ScoreEngine:
    def __init__(self, price_history: dict):
        self.historical = HistoricalAnalyzer(price_history)
        self.rules = QualityRules()

    def evaluate(self, offer: Offer) -> ScoreResult:
        result = ScoreResult()

        hist = self.historical.analyze(
            offer.product_id, offer.current_price, offer.original_price
        )
        quality = self.rules.check(offer, hist)

        declared = offer.discount_percent

        result.historical_score = hist["score"]
        result.context_score = min(100, declared * 1.5)
        result.quality_score = quality["score"]
        result.historical_avg_30d = hist["avg_30d"]
        result.historical_min_30d = hist["min_30d"]
        result.fake_discount_flag = hist["fake_discount"]
        result.real_discount_pct = hist["real_discount_pct"]
        result.declared_discount_pct = float(declared)

        result.final = (
            result.historical_score * 0.40 +
            result.context_score * 0.30 +
            result.quality_score * 0.30
        )

        for cat, threshold in sorted(
            SCORE_THRESHOLDS.items(), key=lambda x: -x[1]
        ):
            if result.final >= threshold:
                result.category = cat
                break

        if result.final >= ScoreThresholds.EXCELLENT:
            result.decision = "send_immediate"
        elif result.final >= ScoreThresholds.GOOD:
            result.decision = "send"
        elif result.final >= ScoreThresholds.MEDIUM:
            result.decision = "send_if_needed"
        else:
            result.decision = "skip"

        logger.info("offer_scored", extra={
            "offer_id": offer.product_id,
            "title": offer.title[:50],
            "platform": offer.platform,
            "current_price": offer.current_price,
            "listed_original": offer.original_price,
            "declared_discount": declared,
            **result.to_dict(),
        })

        return result


class ScoreThresholds:
    EXCELLENT = 80.0
    GOOD = 60.0
    MEDIUM = 40.0
    WEAK = 0.0
