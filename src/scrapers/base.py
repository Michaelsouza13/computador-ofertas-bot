import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.models.offer import Offer
from src.utils.keywords import TARGETS, get_max_price_for_product

logger = logging.getLogger("scrapers.base")


class BaseScraper(ABC):
    def __init__(self):
        self.logger = logging.getLogger(f"scrapers.{self.platform_name}")
        self.errors_this_run = 0
        self.offers_found = 0
        self.elapsed_s = 0.0

    @property
    @abstractmethod
    def platform_name(self) -> str:
        ...

    @abstractmethod
    def search(self, term: str, max_offers: int = 5) -> list[Offer]:
        ...

    def _is_http_blocked(self) -> bool:
        http = getattr(self, "http", None)
        return http is not None and http.is_blocked()

    def scrape_targets(self, max_offers: int = 15) -> list[Offer]:
        import time
        self.errors_this_run = 0
        self.offers_found = 0
        all_offers = []
        seen = set()

        if self._is_http_blocked():
            self.logger.warning("platform_blocked_skip_all")
            return all_offers

        for target in TARGETS:
            if self._is_http_blocked():
                self.logger.warning("platform_blocked_mid_run")
                break
            terms = target.get("search_terms", [])
            max_price = target.get("max_price", 0)
            name = target.get("name", "")
            self.logger.info("searching_target", extra={
                "target": name, "max_price": max_price, "terms": len(terms),
            })

            for term in terms:
                if len(all_offers) >= max_offers:
                    break
                if self._is_http_blocked():
                    break
                try:
                    results = self.search(term, max_offers=5)
                except Exception as e:
                    self.logger.error("search_failed", extra={
                        "term": term, "error": str(e),
                    })
                    self.errors_this_run += 1
                    continue

                for o in results:
                    if o.id in seen:
                        continue
                    seen.add(o.id)
                    if max_price > 0 and o.current_price > max_price:
                        self.logger.info("price_ceiling_blocked", extra={
                            "offer_id": o.id, "title": o.title[:50],
                            "price": o.current_price, "max": max_price,
                            "target": name,
                        })
                        continue
                    if not self._title_matches_target(o.title, terms):
                        continue
                    all_offers.append(o)
                    if len(all_offers) >= max_offers:
                        break
                time.sleep(1.0)

        self.offers_found = len(all_offers)
        self.logger.info("scrape_complete", extra={
            "offers": self.offers_found, "errors": self.errors_this_run,
        })
        return all_offers

    def _title_matches_target(self, title: str, terms: list[str]) -> bool:
        t = title.lower()
        return any(term.lower() in t for term in terms)

    def health(self) -> dict:
        return {
            "platform": self.platform_name,
            "errors": self.errors_this_run,
            "offers_found": self.offers_found,
            "elapsed_s": round(self.elapsed_s, 1),
            "status": "fail" if self.errors_this_run > 5 else "ok",
        }
