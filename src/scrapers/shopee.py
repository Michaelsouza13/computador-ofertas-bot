import hashlib
import json
import logging
import time

import requests

from src.models.offer import Offer
from src.scrapers.base import BaseScraper

logger = logging.getLogger("scrapers.shopee")

API_URL = "https://open-api.affiliate.shopee.com.br/graphql"


class ShopeeScraper(BaseScraper):
    def __init__(self, app_id: str = "", app_secret: str = ""):
        super().__init__()
        self.app_id = app_id
        self.app_secret = app_secret

    @property
    def platform_name(self) -> str:
        return "shopee"

    def _sign(self, timestamp: str, payload: str) -> str:
        raw = self.app_id + timestamp + payload + self.app_secret
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _call(self, query: str, variables: dict):
        payload = json.dumps({"query": query, "variables": variables}, ensure_ascii=False, separators=(",", ":"))
        ts = str(int(time.time()))
        sig = self._sign(ts, payload)
        headers = {
            "Authorization": f"SHA256 Credential={self.app_id}, Timestamp={ts}, Signature={sig}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(API_URL, data=payload, headers=headers, timeout=30)
            if not resp.ok:
                self.logger.error("api_error", extra={"status": resp.status_code})
                return None
            j = resp.json()
            if "errors" in j:
                self.logger.error("graphql_error", extra={"errors": j["errors"]})
                return None
            return j
        except Exception as e:
            self.logger.error("api_exception", extra={"error": str(e)})
            return None

    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        if not self.app_id or not self.app_secret:
            return []
        query = """
        query($keyword: String!, $limit: Int) {
            productOfferV2(keyword: $keyword, limit: $limit) {
                nodes {
                    itemId productName productLink offerLink
                    imageUrl priceMin priceMax priceDiscountRate
                }
            }
        }
        """
        variables = {"keyword": term, "limit": max_offers * 2}
        data = self._call(query, variables)
        if not data:
            return []
        offers = []
        seen = set()
        try:
            nodes = data["data"]["productOfferV2"]["nodes"]
        except (KeyError, TypeError):
            return []
        for node in nodes:
            if len(offers) >= max_offers:
                break
            item_id = str(node.get("itemId", ""))
            if not item_id:
                continue
            full_id = f"SH{item_id}"
            if full_id in seen:
                continue
            seen.add(full_id)
            title = (node.get("productName", "") or "").strip()
            if not title:
                continue
            price_min = float(node.get("priceMin", 0) or 0)
            price_max = float(node.get("priceMax", 0) or 0)
            current = price_min if price_min > 0 else price_max
            if current <= 0:
                continue
            rate = float(node.get("priceDiscountRate", 0) or 0)
            old = current / (1 - rate / 100) if rate > 0 else current * 1.3
            label = f"{int(rate)}% OFF" if rate > 0 else ""
            img = node.get("imageUrl", "") or ""
            url = node.get("offerLink", "") or node.get("productLink", "") or ""
            if url and url.startswith("http"):
                url = url.split("://", 1)[1]
            offers.append(Offer(
                title=title, product_id=full_id,
                current_price=current, original_price=old,
                discount_label=label, image_url=img,
                product_url=url, platform="shopee",
            ))
        return offers
