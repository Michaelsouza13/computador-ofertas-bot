import logging
import re
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.amazon_br")

SEARCH_URL = "https://www.amazon.com.br/s?k={termo}&s=price-asc-rank"


class AmazonBRScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="amazon_br")

    @property
    def platform_name(self) -> str:
        return "amazon_br"

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
        results = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
        for item in results:
            if len(offers) >= max_offers:
                break
            asin = item.get("data-asin", "")
            if not asin:
                continue
            pid = f"AZ{asin}"
            title_el = item.find("h2")
            title = title_el.get_text(strip=True) if title_el else ""
            price_whole = item.find("span", class_="a-price-whole")
            price_fraction = item.find("span", class_="a-price-fraction")
            current = 0.0
            if price_whole:
                whole = price_whole.get_text(strip=True).replace(".", "").replace(",", "")
                frac = price_fraction.get_text(strip=True) if price_fraction else "00"
                try:
                    current = float(f"{whole}.{frac}")
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            img_el = item.find("img", class_="s-image")
            img_url = img_el.get("src", "") if img_el else ""
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                image_url=img_url, platform="amazon_br",
                product_url=f"https://www.amazon.com.br/dp/{asin}",
            ))
        return offers
