import json
import logging
import re
import time

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.promobit")

BASE_URL = "https://www.promobit.com.br"

CATEGORY_URLS = {
    "cpu": "/promocoes/processador/s/",
    "gpu": "/promocoes/informatica/",
    "ram": "/promocoes/informatica/",
    "ssd": "/promocoes/hd-ssd/s/",
    "motherboard": "/promocoes/placa-mae/s/",
    "psu": "/promocoes/informatica/",
    "case": "/promocoes/informatica/",
    "cooler": "/promocoes/cooler/s/",
}


class PromobitScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="promobit")
        self._offers_cache: list[Offer] | None = None
        self._max_price_map: dict[str, float] = {}

    @property
    def platform_name(self) -> str:
        return "promobit"

    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        return []

    def scrape_targets(self, max_offers: int = 15) -> list[Offer]:
        from src.utils.keywords import TARGETS, get_max_price_for_product

        self.errors_this_run = 0
        self.offers_found = 0
        all_offers = []
        seen = set()

        if self._is_http_blocked():
            self.logger.warning("platform_blocked_skip_all")
            return all_offers

        for target in TARGETS:
            if self._is_http_blocked():
                self.logger.warning("platform_blocked_mid_run")
                break

            name = target.get("name", "")
            max_price = target.get("max_price", 0)
            terms = target.get("search_terms", [])
            cat_url = CATEGORY_URLS.get(name)
            if not cat_url:
                continue

            self.logger.info("searching_target", extra={
                "target": name, "max_price": max_price, "category": cat_url,
            })

            offers = self._fetch_category(cat_url)
            for o in offers:
                if len(all_offers) >= max_offers:
                    break
                if o.id in seen:
                    continue
                seen.add(o.id)
                if max_price > 0 and o.current_price > max_price:
                    self.logger.info("price_ceiling_blocked", extra={
                        "offer_id": o.id, "title": o.title[:50],
                        "price": o.current_price, "max": max_price,
                        "target": name,
                    })
                    continue
                if not self._title_matches_target(o.title, terms):
                    continue
                all_offers.append(o)
            time.sleep(0.5)

        self.offers_found = len(all_offers)
        self.logger.info("scrape_complete", extra={
            "offers": self.offers_found, "errors": self.errors_this_run,
        })
        return all_offers

    def _fetch_category(self, path: str) -> list[Offer]:
        url = f"{BASE_URL}{path}"
        html = self.http.get(url)
        if not html:
            return []

        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        offers_data = (
            data.get("props", {})
            .get("pageProps", {})
            .get("serverOffers", {})
            .get("offers", [])
        )
        return self._parse_offers(offers_data)

    def _parse_offers(self, raw: list[dict]) -> list[Offer]:
        results = []
        seen = set()
        for item in raw:
            offer_id = item.get("offerId")
            if not offer_id:
                continue
            pid = f"PB{offer_id}"
            if pid in seen:
                continue
            seen.add(pid)

            title = (item.get("offerTitle") or "").strip()
            price = float(item.get("offerPrice", 0) or 0)
            if not title or price <= 0:
                continue

            old_price = float(item.get("offerOldPrice", 0) or 0) or None
            pct = float(item.get("offerDiscontPercentage", 0) or 0)
            label = f"{int(pct)}% OFF" if pct > 0 else ""
            coupon = item.get("offerCoupon") or ""

            photo = item.get("offerPhoto", "") or ""
            if photo and not photo.startswith("http"):
                photo = f"{BASE_URL}{photo}"

            slug = item.get("offerSlug", "") or ""
            url = f"{BASE_URL}/oferta/{slug}/" if slug else ""

            store = item.get("storeName", "") or ""

            results.append(Offer(
                title=title[:150], product_id=pid,
                current_price=price, original_price=old_price,
                discount_label=label, image_url=photo,
                product_url=url, platform="promobit",
                promo_code=coupon, seller_name=store,
            ))

        return results
