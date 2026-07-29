import logging
from typing import Optional

logger = logging.getLogger("score.rules")

PLATFORM_RELIABILITY = {
    "kabum": 0.95, "pichau": 0.90, "terabyte": 0.90,
    "mercadolivre": 0.80, "shopee": 0.70, "amazon_br": 0.85,
    "amazon_us": 0.85, "magalu": 0.75, "aliexpress": 0.50,
    "zoom": 0.70, "buscape": 0.70, "newegg": 0.80,
}


class QualityRules:
    @staticmethod
    def check(offer, historical: dict) -> dict:
        flags = []
        deductions = 0.0

        # Regra 1: desconto suspeito > 80%
        if offer.discount_percent > 80:
            flags.append("discount_too_high")
            deductions += 20

        # Regra 2: preço original inflado
        if historical.get("fake_discount"):
            flags.append("fake_discount")
            deductions += 30

        # Regra 3: sem histórico = incerto
        if historical.get("avg_30d") is None:
            flags.append("no_history")
            deductions += 15

        # Regra 4: frete
        if not offer.has_free_shipping:
            deductions += 5
        if offer.has_full_shipping:
            deductions -= 10

        # Regra 5: cupom
        if offer.promo_code or offer.coupon_label:
            deductions -= 10

        # Regra 6: parcelamento
        if offer.installments_qty >= 10:
            deductions -= 5

        # Regra 7: confiabilidade da plataforma
        reliability = PLATFORM_RELIABILITY.get(offer.platform, 0.6)
        deductions += (1 - reliability) * 30

        score = max(0, 100 - deductions)
        return {"score": score, "flags": flags}
