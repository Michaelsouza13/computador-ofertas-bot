import logging
import re
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.terabyte")

SEARCH_URL = "https://www.terabyteshop.com.br/busca?str={termo}"


class TerabyteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="terabyte")

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
        seen = set()
        products = soup.find_all("div", class_=re.compile(r"produto|item|card"))
        for prod in products:
            if len(offers) >= max_offers:
                break
            link = prod.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            pid_base = str(hash(href))[:10]
            pid = f"TB{pid_base}"
            if pid in seen:
                continue
            seen.add(pid)
            title = link.get("title", "") or link.get_text(strip=True)
            price_el = prod.find(["span", "div"], class_=re.compile(r"price|preco|val-prod"))
            current = 0.0
            if price_el:
                try:
                    current = float(price_el.get_text(strip=True).replace("R$", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            full_url = href if href.startswith("http") else f"https://www.terabyteshop.com.br{href}"
            offers.append(Offer(
                title=title[:150], product_id=pid,
                current_price=current, product_url=full_url, platform="terabyte",
            ))
        return offers
