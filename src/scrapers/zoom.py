import logging
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.zoom")

SEARCH_URL = "https://www.zoom.com.br/search?q={termo}&sort=price"


class ZoomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="zoom")

    @property
    def platform_name(self) -> str:
        return "zoom"

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
        cards = soup.select('article[data-testid="product-card"]')
        for card in cards:
            if len(offers) >= max_offers:
                break
            link_el = card.select_one('a[data-testid="product-card::card"]')
            if not link_el:
                continue
            href = link_el.get("href", "")
            pid_base = str(hash(href))[:10]
            pid = f"ZM{pid_base}"
            title_el = card.select_one('h2[data-testid="product-card::name"]')
            title = title_el.get_text(strip=True) if title_el else ""
            price_el = card.select_one('[data-testid="product-card::price"] strong')
            current = 0.0
            if price_el:
                try:
                    current = float(price_el.get_text(strip=True).replace("R$", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            full_url = href if href.startswith("http") else f"https://www.zoom.com.br{href}"
            offers.append(Offer(
                title=title[:150], product_id=pid,
                current_price=current, product_url=full_url, platform="zoom",
            ))
        return offers
