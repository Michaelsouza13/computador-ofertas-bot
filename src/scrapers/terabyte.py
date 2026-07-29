import logging
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.terabyte")

SEARCH_URL = "https://www.terabyteshop.com.br/busca?str={termo}"


class TerabyteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="terabyte", use_curl_cffi=True, impersonate="chrome120")

    @property
    def platform_name(self) -> str:
        return "terabyte"

    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        url = SEARCH_URL.format(termo=quote(term))
        html = self.http.get(url)
        if not html:
            return []
        return self._parse_search(html, max_offers)

    def _parse_search(self, html: str, max_offers: int) -> list[Offer]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers = []
        cards = soup.select("div.product-item")
        for card in cards:
            if len(offers) >= max_offers:
                break
            price_str = card.get("data-tss-price", "")
            if not price_str:
                continue
            try:
                current = float(price_str)
            except ValueError:
                continue
            title_el = card.select_one("a.product-item__name h2")
            if not title_el:
                title_el = card.select_one("a.product-item__name")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link_el = card.select_one("a.product-item__name")
            if not link_el:
                link_el = card.select_one("a.product-item__image")
            if not link_el:
                continue
            href = link_el.get("href", "")
            pid_base = str(hash(href))[:10]
            pid = f"TB{pid_base}"
            full_url = href if href.startswith("http") else f"https://www.terabyteshop.com.br{href}"
            img_el = card.select_one("img.image-thumbnail")
            img_url = img_el.get("src", "") if img_el else ""
            offers.append(Offer(
                title=title[:150], product_id=pid,
                current_price=current, product_url=full_url,
                image_url=img_url, platform="terabyte",
            ))
        return offers
