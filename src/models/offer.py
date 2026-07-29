import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ScoreCategory(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MEDIUM = "medium"
    WEAK = "weak"
    UNCERTAIN = "uncertain"


@dataclass
class ScoreResult:
    final: float = 0.0
    category: ScoreCategory = ScoreCategory.UNCERTAIN
    historical_score: float = 0.0
    context_score: float = 0.0
    quality_score: float = 0.0
    fake_discount_flag: bool = False
    historical_avg_30d: Optional[float] = None
    historical_min_30d: Optional[float] = None
    real_discount_pct: float = 0.0
    declared_discount_pct: float = 0.0
    decision: str = "skipped"

    def to_dict(self) -> dict:
        return {
            "final": round(self.final, 1),
            "category": self.category.value,
            "historical_score": round(self.historical_score, 1),
            "context_score": round(self.context_score, 1),
            "quality_score": round(self.quality_score, 1),
            "fake_discount_flag": self.fake_discount_flag,
            "historical_avg_30d": self.historical_avg_30d,
            "historical_min_30d": self.historical_min_30d,
            "real_discount_pct": round(self.real_discount_pct, 1),
            "declared_discount_pct": round(self.declared_discount_pct, 1),
            "decision": self.decision,
        }


@dataclass
class Offer:
    title: str
    product_id: str
    current_price: float
    original_price: Optional[float] = None
    discount_label: str = ""
    image_url: str = ""
    product_url: str = ""
    platform: str = ""
    shipping_tags: list = field(default_factory=list)
    promo_code: str = ""
    promo_value: str = ""
    coupon_label: str = ""
    installments_qty: int = 0
    installment_value: float = 0.0
    seller_name: str = ""
    seller_rating: Optional[float] = None
    score: Optional[ScoreResult] = None

    @property
    def id(self) -> str:
        return self.product_id

    @property
    def clean_url(self) -> str:
        if self.product_url:
            if self.product_url.startswith("http"):
                return self.product_url
            return f"https://{self.product_url}"
        if self.product_id.startswith("MLB"):
            return f"https://www.mercadolivre.com.br/p/{self.product_id}"
        if self.product_id.startswith("SH"):
            return f"https://shopee.com.br/product/{self.product_id[2:]}"
        return self.product_url or ""

    @property
    def discount_percent(self) -> int:
        m = re.search(r"(\d+)%", self.discount_label)
        if m:
            return int(m.group(1))
        if self.original_price and self.original_price > 0 and self.current_price > 0:
            return int((1 - self.current_price / self.original_price) * 100)
        return 0

    @property
    def has_free_shipping(self) -> bool:
        return "free_shipping" in self.shipping_tags or self.has_full_shipping

    @property
    def has_full_shipping(self) -> bool:
        return "fulfillment" in self.shipping_tags

    @property
    def platform_label(self) -> str:
        labels = {
            "ML": "Mercado Livre",
            "SH": "Shopee",
            "KB": "Kabum",
            "PC": "Pichau",
            "TB": "Terabyte",
            "AZ": "Amazon",
            "MG": "Magalu",
            "AE": "AliExpress",
            "ZM": "Zoom",
            "BC": "Buscapé",
            "NW": "Newegg",
        }
        prefix = self.product_id[:2].upper() if len(self.product_id) >= 2 else ""
        return labels.get(prefix, self.platform or "Oferta")

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "title": self.title,
            "current_price": self.current_price,
            "original_price": self.original_price,
            "discount_label": self.discount_label,
            "discount_percent": self.discount_percent,
            "platform": self.platform_label,
            "image_url": self.image_url,
            "has_free_shipping": self.has_free_shipping,
            "has_full_shipping": self.has_full_shipping,
            "installments_qty": self.installments_qty,
            "installment_value": self.installment_value,
            "promo_code": self.promo_code,
            "coupon_label": self.coupon_label,
            "seller_name": self.seller_name,
            "url": self.clean_url,
        }
