import logging
import re
import time

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.amazon_us")

SEARCH_URL = "https://www.amazon.com/s?k={keyword}+computer+hardware&s=price-asc-rank"


class AmazonUSScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="amazon_us")

    @property
    def platform_name(self) -> str:
        return "amazon_us"

    def scrape(self, max_offers: int = 5) -> list[Offer]:
        self.errors_this_run = 0
        self.offers_found = 0
        t0 = time.time()
        offers = []
        seen = set()
        keywords = ["graphics+card", "processor+cpu", "ddr5+ram", "nvme+ssd", "power+supply"]
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
        results = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
        for item in results:
            asin = item.get("data-asin", "")
            if not asin:
                continue
            pid = f"AZ{asin}"
            title_el = item.find("h2")
            title = title_el.get_text(strip=True) if title_el else ""
            price_whole = item.find("span", class_="a-price-whole")
            current = 0.0
            if price_whole:
                try:
                    current = float(price_whole.get_text(strip=True).replace(".", "").replace(",", ""))
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            pid_type = "AZU"
            pid = f"{pid_type}{asin}"
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                platform="amazon_us",
                product_url=f"https://www.amazon.com/dp/{asin}",
            ))
        return offers
