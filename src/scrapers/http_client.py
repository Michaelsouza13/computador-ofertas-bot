import logging
import random
import time
from typing import Optional

import requests

logger = logging.getLogger("scrapers.http_client")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class AdaptiveRateLimiter:
    def __init__(self, min_delay: float = 1.5, max_delay: float = 30.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = min_delay
        self._last_request = 0.0

    def wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.current_delay:
            sleep = self.current_delay - elapsed
            time.sleep(sleep)
        self._last_request = time.time()

    def on_success(self):
        self.current_delay = max(self.min_delay, self.current_delay * 0.9)

    def on_block(self):
        self.current_delay = min(self.max_delay, self.current_delay * 2.0)


class HttpClient:
    def __init__(self, platform: str = ""):
        self.platform = platform
        self.session = requests.Session()
        self.limiter = AdaptiveRateLimiter(min_delay=2.0, max_delay=30.0)
        self._rotate_ua()

    def _rotate_ua(self):
        self.session.headers.update(BASE_HEADERS)
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

    def get(self, url: str, timeout: int = 30, **kwargs) -> Optional[str]:
        self.limiter.wait()
        self._rotate_ua()
        logger.debug("http_get", extra={
            "url": url[:120], "platform": self.platform,
            "delay": round(self.limiter.current_delay, 1),
        })
        try:
            resp = self.session.get(url, timeout=timeout, **kwargs)
            if resp.status_code == 429 or resp.status_code == 403:
                self.limiter.on_block()
                logger.warning("http_blocked", extra={
                    "url": url[:80], "status": resp.status_code,
                    "platform": self.platform,
                    "new_delay": round(self.limiter.current_delay, 1),
                })
                return None
            resp.raise_for_status()
            resp.encoding = "utf-8"
            self.limiter.on_success()
            logger.debug("http_ok", extra={
                "url": url[:80], "status": resp.status_code,
                "size_kb": round(len(resp.text) / 1024, 1),
            })
            return resp.text
        except requests.RequestException as e:
            logger.error("http_error", extra={
                "url": url[:80], "error": str(e), "platform": self.platform,
            })
            return None

    def get_json(self, url: str, timeout: int = 30, **kwargs) -> Optional[dict]:
        text = self.get(url, timeout=timeout, **kwargs)
        if text:
            import json
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        return None
