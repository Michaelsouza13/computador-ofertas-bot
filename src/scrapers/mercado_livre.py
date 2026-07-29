import json
import logging
import re
import time
from typing import Optional

from src.models.offer import Offer
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import HttpClient
from src.utils.keywords import ALL_HARDWARE

logger = logging.getLogger("scrapers.mercado_livre")


class MercadoLivreScraper(BaseScraper):
    BASE_URL = "https://www.mercadolivre.com.br/ofertas"

    CATEGORIAS = {
        "informatica": "MLB1648",
        "esportes": "MLB1276",
        "eletronicos": "MLB1000",
    }

    def __init__(self, category: str = "informatica", pages: int = 3, promotion_type: str = ""):
        super().__init__()
        self.category = CATEGORIAS.get(category.lower(), category) if category else ""
        self.pages = pages
        self.promotion_type = promotion_type
        self.http = HttpClient(platform="mercadolivre")

    @property
    def platform_name(self) -> str:
        return "mercadolivre"

    def _make_url(self, page: int) -> str:
        url = self.BASE_URL
        params = {}
        if self.category:
            params["category"] = self.category
        if self.promotion_type:
            params["promotion_type"] = self.promotion_type
        if page > 1:
            params["page"] = str(page)
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return url

    def scrape(self, max_offers: int = 10) -> list[Offer]:
        self.offers_found = 0
        self.errors_this_run = 0
        seen = set()
        offers = []
        t0 = time.time()

        for page in range(1, self.pages + 1):
            if len(offers) >= max_offers:
                break
            if page > 1:
                time.sleep(1.5)

            url = self._make_url(page)
            html = self.http.get(url)
            if not html:
                self.errors_this_run += 1
                continue

            page_offers = self._extract_from_json(html)
            if not page_offers:
                page_offers = self._extract_from_html(html)

            for o in page_offers:
                if o.id in seen:
                    continue
                seen.add(o.id)
                if not self._match_keywords(o.title):
                    continue
                offers.append(o)
                if len(offers) >= max_offers:
                    break

            self.logger.info("page_done", extra={
                "page": page, "found": len(page_offers), "total": len(offers),
            })

        self.offers_found = len(offers)
        self.elapsed_s = time.time() - t0
        self.logger.info("scraper_complete", extra={
            "offers": self.offers_found, "elapsed_s": round(self.elapsed_s, 1),
        })
        return offers

    def _match_keywords(self, title: str) -> bool:
        t = title.lower()
        return any(kw in t for kw in ALL_HARDWARE)

    def _extract_from_json(self, html: str) -> list[Offer]:
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
                if not shipping_tags:
                    shipping_tags = components.get("shipping_v2", {}).get("shipping", {}).get("tags", [])
                coupon_label = ""
                promos = components.get("promotions", {}).get("promotions", [])
                for p in promos:
                    if p.get("type") == "coupon":
                        coupon_label = p.get("text", "")
                pics = card.get("pictures", {}).get("pictures", [])
                img = f"https://http2.mlstatic.com/D_{pics[0]['id']}-O.jpg" if pics else ""
                offers.append(Offer(
                    title=title, product_id=pid,
                    current_price=float(current),
                    original_price=float(previous) if previous else None,
                    discount_label=discount,
                    installments_qty=inst_qty, installment_value=inst_val,
                    image_url=img, product_url=meta.get("url", ""),
                    shipping_tags=shipping_tags, coupon_label=coupon_label,
                    platform="mercadolivre",
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
