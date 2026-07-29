import logging
import re
import time
from urllib.parse import quote

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient

logger = logging.getLogger("scrapers.mercado_livre")

SEARCH_URL = "https://lista.mercadolivre.com.br/{termo}"


class MercadoLivreScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.http = HttpClient(platform="mercadolivre")

    @property
    def platform_name(self) -> str:
        return "mercadolivre"

    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        url = SEARCH_URL.format(termo=quote(term))
        html = self.http.get(url)
        if not html:
            return []
        return self._parse_search(html, max_offers)

    def _parse_search(self, html: str, max_offers: int) -> list[Offer]:
        offers = []
        seen = set()

        page_offers = self._extract_from_json(html)
        if not page_offers:
            page_offers = self._extract_from_html(html)

        for o in page_offers:
            if o.id in seen:
                continue
            seen.add(o.id)
            offers.append(o)
            if len(offers) >= max_offers:
                break

        return offers

    def _extract_from_json(self, html: str) -> list[Offer]:
        import json
        match = re.search(r"_n\.ctx\.r\s*=\s*(\{.+?\});", html, re.DOTALL)
        if not match:
            return []
        try:
            ctx = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        items = (
            ctx.get("appProps", {})
            .get("pageProps", {})
            .get("data", {})
            .get("items", [])
        )
        offers = []
        for item in items:
            try:
                card = item.get("card", {})
                meta = card.get("metadata", {})
                pid = meta.get("id", "")
                if not pid or not pid.startswith("MLB"):
                    continue
                components = {c["type"]: c for c in card.get("components", [])}
                title = components.get("title", {}).get("title", {}).get("text", "")
                price_data = components.get("price", {}).get("price", {})
                current = price_data.get("current_price", {}).get("value", 0.0)
                previous = price_data.get("previous_price", {}).get("value")
                discount = price_data.get("discount_label", {}).get("text", "")
                inst = price_data.get("installments", {})
                inst_qty = int(inst.get("quantity", 0) or 0)
                inst_val = float(inst.get("amount", 0.0) or 0.0)
                shipping_tags = components.get("shipping", {}).get("shipping", {}).get("tags", [])
                pics = card.get("pictures", {}).get("pictures", [])
                img = f"https://http2.mlstatic.com/D_{pics[0]['id']}-O.jpg" if pics else ""
                offers.append(Offer(
                    title=title, product_id=pid,
                    current_price=float(current),
                    original_price=float(previous) if previous else None,
                    discount_label=discount,
                    installments_qty=inst_qty, installment_value=inst_val,
                    image_url=img, product_url=meta.get("url", ""),
                    shipping_tags=shipping_tags, platform="mercadolivre",
                ))
            except Exception:
                continue
        return offers

    def _extract_from_html(self, html: str) -> list[Offer]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        offers = []
        seen = set()
        cards = soup.find_all("li", class_=re.compile(r"ui-search-layout__item"))
        if not cards:
            cards = soup.find_all("div", class_=re.compile(r"poly-card"))
        for card in cards:
            link = card.find("a", href=re.compile(r"/p/MLB\d+"))
            if not link:
                continue
            href = link.get("href", "")
            m = re.search(r"/p/(MLB\d+)", href)
            if not m or m.group(1) in seen:
                continue
            pid = m.group(1)
            seen.add(pid)
            title = link.get("title", "") or link.get_text(strip=True)
            price_el = card.find("span", class_=re.compile(r"andes-money-amount__fraction"))
            current = 0.0
            if price_el:
                try:
                    current = float(price_el.get_text(strip=True).replace(".", "").replace(",", "."))
                except ValueError:
                    pass
            offers.append(Offer(
                title=title, product_id=pid, current_price=current,
                product_url=href, platform="mercadolivre",
            ))
        return offers
