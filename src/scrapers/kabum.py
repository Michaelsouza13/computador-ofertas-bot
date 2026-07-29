import json
import logging
import re
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.kabum")

SEARCH_URL = "https://www.kabum.com.br/busca/{termo}"


class KabumScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="kabum", use_curl_cffi=True, impersonate="chrome120")

    @property
    def platform_name(self) -> str:
        return "kabum"

    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        url = SEARCH_URL.format(termo=quote(term))
        html = self.http.get(url)
        if not html:
            return []
        return self._parse_search(html, max_offers)

    def _parse_search(self, html: str, max_offers: int) -> list[Offer]:
        offers = []
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        products = self._extract_products(data)
        seen = set()
        for prod in products:
            if len(offers) >= max_offers:
                break
            code = prod.get("code")
            if not code:
                continue
            pid = f"KB{code}"
            if pid in seen:
                continue
            seen.add(pid)
            title = prod.get("name", "")
            price = prod.get("priceWithDiscount", 0) or prod.get("price", 0)
            if not title or not price:
                continue
            slug = prod.get("friendlyName", "")
            url = f"https://www.kabum.com.br/{slug}" if slug else ""
            offers.append(Offer(
                title=title[:150], product_id=pid,
                current_price=float(price), product_url=url,
                platform="kabum",
            ))
        return offers

    def _extract_products(self, data: dict) -> list[dict]:
        try:
            pp = data.get("props", {}).get("pageProps", {})
            catalog = pp.get("data", {}).get("catalogServer", {})
            products = catalog.get("data", [])
            if isinstance(products, list) and products:
                return products
        except Exception:
            pass
        return []
