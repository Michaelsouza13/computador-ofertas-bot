import json
import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.logging_config import RUN_DIR, RUN_ID
from src.models.offer import Offer, ScoreCategory
from src.scrapers.mercado_livre import MercadoLivreScraper
from src.scrapers.shopee import ShopeeScraper
from src.scrapers.kabum import KabumScraper
from src.scrapers.pichau import PichauScraper
from src.scrapers.terabyte import TerabyteScraper
from src.scrapers.amazon_br import AmazonBRScraper
from src.scrapers.magalu import MagaluScraper
from src.scrapers.zoom import ZoomScraper
from src.scrapers.buscape import BuscapeScraper
from src.scrapers.amazon_us import AmazonUSScraper
from src.scrapers.aliexpress import AliExpressScraper
from src.scrapers.newegg import NeweggScraper
from src.score.engine import ScoreEngine
from src.senders.telegram import TelegramSender
from src.senders.whatsapp import WhatsAppSender
from src.storage.cache import Cache
from src.storage.price_history import PriceHistory
from src.utils.affiliate import make_affiliate_url
from src.utils.decorators import retry_with_backoff

logger = logging.getLogger("bot")


def _load_config() -> dict:
    config = {"platforms": {}, "scraping": {}, "sending": {}}
    config_path = Path("config/platforms.toml")
    if config_path.exists():
        try:
            import tomllib
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
        except Exception:
            pass
    return config


def _get_platforms(config: dict):
    enabled = config.get("platforms", {})
    scrapers = []
    if enabled.get("mercadolivre", True):
        scrapers.append(MercadoLivreScraper())
    if enabled.get("shopee", True):
        scrapers.append(ShopeeScraper(
            app_id=os.environ.get("SHOPEE_APP_ID", ""),
            app_secret=os.environ.get("SHOPEE_APP_SECRET", ""),
        ))
    if enabled.get("kabum", True):
        scrapers.append(KabumScraper())
    if enabled.get("pichau", True):
        scrapers.append(PichauScraper())
    if enabled.get("terabyte", True):
        scrapers.append(TerabyteScraper())
    if enabled.get("amazon_br", True):
        scrapers.append(AmazonBRScraper())
    if enabled.get("magalu", True):
        scrapers.append(MagaluScraper())
    if enabled.get("zoom", True):
        scrapers.append(ZoomScraper())
    if enabled.get("buscape", True):
        scrapers.append(BuscapeScraper())
    if enabled.get("amazon_us", False):
        scrapers.append(AmazonUSScraper())
    if enabled.get("aliexpress", False):
        scrapers.append(AliExpressScraper())
    if enabled.get("newegg", False):
        scrapers.append(NeweggScraper())
    return scrapers


def _interleave_offers(offers: list) -> list:
    groups = defaultdict(list)
    for o in offers:
        prefix = o.product_id[:2] if len(o.product_id) >= 2 else "ZZ"
        groups[prefix].append(o)
    result = []
    prefixes = sorted(groups.keys())
    while any(groups.values()):
        for p in prefixes:
            if groups[p]:
                result.append(groups[p].pop(0))
    return result


def _balance_offers(all_offers: list, max_offers: int) -> list:
    if not all_offers or max_offers <= 0:
        return []
    quotas = defaultdict(int)
    for o in all_offers:
        prefix = o.product_id[:2]
        quotas[prefix] += 1

    quota = max(max_offers // max(len(quotas), 1), 1)
    groups = defaultdict(list)
    for o in all_offers:
        groups[o.product_id[:2]].append(o)

    result = []
    prefixes = sorted(groups.keys())
    for i in range(quota):
        for p in prefixes:
            if i < len(groups[p]) and len(result) < max_offers:
                result.append(groups[p][i])

    remaining = _interleave_offers([
        o for p in prefixes for o in groups[p][quota:]
    ])
    for o in remaining:
        if len(result) >= max_offers:
            break
        result.append(o)

    logger.info("balance_result", extra={
        "total": len(result),
        "distribution": {p: sum(1 for o in result if o.product_id[:2] == p)
                         for p in prefixes},
    })
    return result


@retry_with_backoff(max_retries=2, base_delay=5)
def _scrape_platform(scraper, max_offers: int) -> list[Offer]:
    return scraper.scrape_targets(max_offers=max_offers)


def _build_summary(run_id: str, scrapers, scored, sent_tg, sent_wp, total_time_s, cache_size):
    summary = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "scrapers": {s.platform_name: s.health() for s in scrapers},
        "score_distribution": {},
        "sends": {"telegram": sent_tg, "whatsapp": sent_wp},
        "total_duration_s": round(total_time_s, 1),
        "cache_size": cache_size,
    }
    if scored:
        dist = defaultdict(int)
        for s in scored:
            dist[s.score.category.value] += 1
        summary["score_distribution"] = dict(dist)
    return summary


def main():
    t0 = time.time()
    logger.info("bot_start", extra={
        "run_id": RUN_ID,
        "config_summary": {"platforms": 12, "max_offers": 15},
    })

    config = _load_config()
    scraping_cfg = config.get("scraping", {})
    max_offers = int(os.environ.get("MAX_OFFERS_PER_RUN",
                                     str(scraping_cfg.get("max_offers_per_run", 15))))
    send_delay = int(os.environ.get("SEND_DELAY_SECONDS",
                                     str(scraping_cfg.get("send_delay_seconds", 30))))

    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    wp_url = os.environ.get("ZAP_API_URL", "")
    wp_key = os.environ.get("ZAP_API_KEY", "")
    wp_phone = os.environ.get("WHATSAPP_PHONE", "")

    if not tg_token and not wp_url:
        logger.error("no_sender_configured")
        sys.exit(1)

    scrapers = _get_platforms(config)
    if not scrapers:
        logger.error("no_scrapers_enabled")
        sys.exit(1)

    cache = Cache()
    price_history = PriceHistory()
    score_engine = ScoreEngine(price_history.data)

    sender_tg = TelegramSender(tg_token) if tg_token else None
    sender_wp = WhatsAppSender(wp_url, wp_key) if wp_url else None

    all_offers = []
    logger.info("scraping_start", extra={"platforms": len(scrapers)})

    with ThreadPoolExecutor(max_workers=min(len(scrapers), 6)) as executor:
        per_platform = max(1, max_offers // len(scrapers)) if max_offers > 0 else 5
        futures = {
            executor.submit(_scrape_platform, s, per_platform): s
            for s in scrapers
        }
        for future in as_completed(futures):
            scraper = futures[future]
            try:
                result = future.result()
                for o in result:
                    if not cache.contains(o.id):
                        cache.add(o.id)
                        all_offers.append(o)
                logger.info("platform_done", extra={
                    "platform": scraper.platform_name,
                    "offers": len(result),
                })
            except Exception as e:
                logger.error("platform_failed", extra={
                    "platform": scraper.platform_name, "error": str(e),
                })

    elapsed_scraping = time.time() - t0
    logger.info("scraping_complete", extra={
        "total_offers": len(all_offers), "elapsed_s": round(elapsed_scraping, 1),
    })

    if not all_offers:
        logger.info("no_offers_found")
        return

    offers = _balance_offers(all_offers, max_offers)

    for o in offers:
        price_history.record_offer(o)

    scored_offers = []
    for o in offers:
        o.score = score_engine.evaluate(o)
        if o.score.decision in ("send_immediate", "send", "send_if_needed"):
            scored_offers.append(o)

    scored_offers.sort(key=lambda o: o.score.final, reverse=True)

    logger.info("offers_to_send", extra={"count": len(scored_offers)})

    affiliate_config = {
        "ML": os.environ.get("AFFILIATE_TAG_ML", ""),
        "AZ": os.environ.get("AFFILIATE_TAG_AMAZON", ""),
    }

    sent_tg = 0
    sent_wp = 0

    for i, offer in enumerate(scored_offers):
        if i > 0 and send_delay > 0:
            logger.debug("send_delay", extra={"seconds": send_delay})
            time.sleep(send_delay)

        offer.product_url = make_affiliate_url(
            offer.clean_url, offer.product_id[:2], affiliate_config
        )

        if sender_tg:
            try:
                if sender_tg.send_offer(tg_chat, offer):
                    sent_tg += 1
            except Exception as e:
                logger.error("telegram_send_failed", extra={
                    "offer_id": offer.product_id, "error": str(e),
                })

        if sender_wp and wp_phone:
            try:
                if sender_wp.send_offer(wp_phone, offer):
                    sent_wp += 1
            except Exception as e:
                logger.error("whatsapp_send_failed", extra={
                    "offer_id": offer.product_id, "error": str(e),
                })

        logger.info("offer_sent", extra={
            "offer_id": offer.product_id,
            "title": offer.title[:50],
            "price": offer.current_price,
            "platform": offer.platform,
            "score": round(offer.score.final, 1) if offer.score else 0,
            "telegram": bool(sender_tg),
            "whatsapp": bool(sender_wp and wp_phone),
        })

    cache.save()
    price_history.save()

    total_time = time.time() - t0
    summary = _build_summary(
        RUN_ID, scrapers, scored_offers, sent_tg, sent_wp, total_time, len(cache.data)
    )
    summary_path = RUN_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("bot_complete", extra={
        "offers_found": len(all_offers),
        "offers_scored": len(scored_offers),
        "sent_telegram": sent_tg,
        "sent_whatsapp": sent_wp,
        "total_time_s": round(total_time, 1),
    })
