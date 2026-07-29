import logging
import re
import time

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.pichau")

CATEGORY_URLS = {
    "placa-video": "https://www.pichau.com.br/hardware/placa-de-video",
    "processador": "https://www.pichau.com.br/hardware/processadores",
    "memoria": "https://www.pichau.com.br/hardware/memoria",
    "ssd": "https://www.pichau.com.br/hardware/armazenamento",
    "fonte": "https://www.pichau.com.br/hardware/fonte",
    "gabinete": "https://www.pichau.com.br/hardware/gabinete",
    "placa-mae": "https://www.pichau.com.br/hardware/placa-mae",
    "cooler": "https://www.pichau.com.br/hardware/cooler",
}


class PichauScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="pichau")

    @property
    def platform_name(self) -> str:
        return "pichau"

    def scrape(self, max_offers: int = 10) -> list[Offer]:
        self.errors_this_run = 0
        self.offers_found = 0
        t0 = time.time()
        offers = []
        seen = set()
        for cat, url in CATEGORY_URLS.items():
            if len(offers) >= max_offers:
                break
            html = self.http.get(url)
            if not html:
                self.errors_this_run += 1
                continue
            page_offers = self._parse_listing(html)
            for o in page_offers:
                if o.id in seen:
                    continue
                seen.add(o.id)
                offers.append(o)
                if len(offers) >= max_offers:
                    break
            time.sleep(1.5)
        self.offers_found = len(offers)
        self.elapsed_s = time.time() - t0
        self.logger.info("scraper_complete", extra={
            "offers": self.offers_found, "elapsed_s": round(self.elapsed_s, 1),
        })
        return offers

    def _parse_listing(self, html: str) -> list[Offer]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers = []
        products = soup.find_all("div", class_=re.compile(r"product-item|card"))
        for prod in products:
            link = prod.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            pid_base = str(hash(href))[:10]
            pid = f"PC{pid_base}"
            title = link.get("title", "") or link.get_text(strip=True)
            price_el = prod.find(["span", "div", "strong"], class_=re.compile(r"price|boleto|por"))
            current = 0.0
            if price_el:
                try:
                    current = float(
                        price_el.get_text(strip=True)
                        .replace("R$", "").replace(".", "").replace(",", ".").strip()
                    )
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            full_url = href if href.startswith("http") else f"https://www.pichau.com.br{href}"
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                product_url=full_url, platform="pichau",
            ))
        return offers
