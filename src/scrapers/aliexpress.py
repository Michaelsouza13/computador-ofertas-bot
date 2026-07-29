import logging
import re
import time

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.aliexpress")

SEARCH_URL = "https://pt.aliexpress.com/wholesale?SearchText={keyword}&sort=price_asc"


class AliExpressScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="aliexpress")

    @property
    def platform_name(self) -> str:
        return "aliexpress"

    def scrape(self, max_offers: int = 5) -> list[Offer]:
        self.errors_this_run = 0
        self.offers_found = 0
        t0 = time.time()
        offers = []
        seen = set()
        keywords = ["graphics+card", "cpu+processor", "ddr5+ram", "nvme"]
        for kw in keywords:
            if len(offers) >= max_offers:
                break
            url = SEARCH_URL.format(keyword=kw)
            html = self.http.get(url)
            if not html:
                self.errors_this_run += 1
                continue
            page_offers = self._parse_search(html)
            for o in page_offers:
                if o.id in seen:
                    continue
                seen.add(o.id)
                offers.append(o)
                if len(offers) >= max_offers:
                    break
            time.sleep(3)
        self.offers_found = len(offers)
        self.elapsed_s = time.time() - t0
        self.logger.info("scraper_complete", extra={
            "offers": self.offers_found, "elapsed_s": round(self.elapsed_s, 1),
        })
        return offers

    def _parse_search(self, html: str) -> list[Offer]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers = []
        items = soup.find_all("a", class_=re.compile(r"item|product|card"))
        for item in items:
            href = item.get("href", "")
            if not href or "aliexpress" not in href:
                continue
            pid_base = str(hash(href))[:10]
            pid = f"AE{pid_base}"
            title = item.get("title", "") or item.get_text(strip=True)
            price_el = item.find(["span", "div"], class_=re.compile(r"price|usd"))
            current = 0.0
            if price_el:
                try:
                    txt = price_el.get_text(strip=True).replace("US", "").replace("$", "").strip()
                    current = float(txt.replace(",", ""))
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            full_url = href if href.startswith("http") else f"https:{href}"
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                product_url=full_url, platform="aliexpress",
            ))
        return offers
