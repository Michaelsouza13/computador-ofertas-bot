import logging
import re
import time

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient
from src.utils.keywords import ALL_HARDWARE

logger = logging.getLogger("scrapers.kabum")

CATEGORY_URLS = {
    "placa-video": "https://www.kabum.com.br/hardware/placa-de-video",
    "processador": "https://www.kabum.com.br/hardware/processador",
    "memoria": "https://www.kabum.com.br/hardware/memoria",
    "ssd": "https://www.kabum.com.br/hardware/ssd",
    "fonte": "https://www.kabum.com.br/hardware/fonte",
    "gabinete": "https://www.kabum.com.br/hardware/gabinete",
    "placa-mae": "https://www.kabum.com.br/hardware/placa-mãe",
    "cooler": "https://www.kabum.com.br/hardware/cooler",
}


class KabumScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="kabum")

    @property
    def platform_name(self) -> str:
        return "kabum"

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
            page_offers = self._parse_listing(html, cat)
            for o in page_offers:
                if o.id in seen:
                    continue
                seen.add(o.id)
                offers.append(o)
                if len(offers) >= max_offers:
                    break
            time.sleep(2)
        self.offers_found = len(offers)
        self.elapsed_s = time.time() - t0
        self.logger.info("scraper_complete", extra={
            "offers": self.offers_found, "elapsed_s": round(self.elapsed_s, 1),
        })
        return offers

    def _parse_listing(self, html: str, category: str) -> list[Offer]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers = []
        products = soup.find_all("article", class_=re.compile(r"productCard"))
        if not products:
            products = soup.find_all("div", class_=re.compile(r"product"))
        for prod in products:
            link = prod.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            pid_match = re.search(r"/produto/(\d+)", href)
            if not pid_match:
                pid_match = re.search(r"MLB(\d+)", href)
            pid_base = pid_match.group(1) if pid_match else str(hash(href))[:10]
            pid = f"KB{pid_base}"
            title_el = prod.find(["h2", "h3", "span"], class_=re.compile(r"(title|name|desc)"))
            title = title_el.get_text(strip=True) if title_el else link.get("title", "") or ""
            price_el = prod.find("span", class_=re.compile(r"price"))
            if not price_el:
                price_el = prod.find("strong", class_=re.compile(r"price"))
            current = 0.0
            if price_el:
                try:
                    current = float(
                        price_el.get_text(strip=True)
                        .replace("R$", "").replace(".", "").replace(",", ".").strip()
                    )
                except ValueError:
                    pass
            old_price = None
            old_el = prod.find("span", class_=re.compile(r"old|before|de:"))
            if old_el:
                try:
                    old_price = float(
                        old_el.get_text(strip=True)
                        .replace("R$", "").replace(".", "").replace(",", ".").strip()
                    )
                except ValueError:
                    pass
            if not title or current <= 0:
                continue
            full_url = href if href.startswith("http") else f"https://www.kabum.com.br{href}"
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                original_price=old_price, product_url=full_url,
                platform="kabum",
            ))
        return offers
