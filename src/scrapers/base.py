import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.models.offer import Offer

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
    def scrape(self, max_offers: int = 10) -> list[Offer]:
        ...

    def health(self) -> dict:
        return {
            "platform": self.platform_name,
            "errors": self.errors_this_run,
            "offers_found": self.offers_found,
            "elapsed_s": round(self.elapsed_s, 1),
            "status": "fail" if self.errors_this_run > 5 else "ok",
        }
