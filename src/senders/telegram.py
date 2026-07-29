import logging
import random

import requests

from src.utils.price import format_price

logger = logging.getLogger("senders.telegram")

CTA_PHRASES = [
    "Aproveite antes que acabe!",
    "Corre que é oportunidade!",
    "Oferta por tempo limitado!",
    "Garanta a sua agora!",
    "Não perca essa chance!",
    "Preço imperdível!",
    "O melhor preço do mercado!",
]


class TelegramSender:
    API_BASE = "https://api.telegram.org"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"{self.API_BASE}/bot{bot_token}"

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        try:
            resp = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )
            if not resp.ok:
                logger.error("send_failed", extra={
                    "status": resp.status_code, "text": resp.text[:200],
                })
                return False
            logger.info("message_sent", extra={"chat_id": chat_id[:10]})
            return True
        except Exception as e:
            logger.error("send_exception", extra={"error": str(e)})
            return False

    def send_photo(self, chat_id: str, photo_url: str, caption: str) -> bool:
        try:
            resp = requests.post(
                f"{self.api_url}/sendPhoto",
                json={
                    "chat_id": chat_id,
                    "photo": photo_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            return resp.ok
        except Exception as e:
            logger.warning("photo_failed", extra={"error": str(e)})
            return False

    def send_offer(self, chat_id: str, offer) -> bool:
        message = self._format_message(offer)
        if offer.image_url:
            try:
                if self.send_photo(chat_id, offer.image_url, message):
                    return True
            except Exception:
                pass
        return self.send_message(chat_id, message)

    def send_alert(self, chat_id: str, text: str) -> bool:
        return self.send_message(chat_id, f"\u26A0\uFE0F <b>Bot</b>\n\n{text}")

    def _format_message(self, offer) -> str:
        current = format_price(offer.current_price)
        old = format_price(offer.original_price) if offer.original_price else ""
        discount = offer.discount_label.strip() if offer.discount_label else ""
        url = offer.clean_url

        score_tag = ""
        if offer.score:
            cat = offer.score.category.value
            if cat == "excellent":
                score_tag = "\u2B50 "
            elif cat == "good":
                score_tag = "\u2705 "
            elif cat == "medium":
                score_tag = "\u2796 "

        lines = [
            f"{score_tag}<b>\U0001F525 PROMO\u00C7\u00C3O {offer.platform_label.upper()}</b>",
            "",
            f"\U0001F4CC <b>{offer.title[:100]}</b>",
        ]
        if old:
            lines.append(f"\U0001F4B0 De: <s>{old}</s>")
        lines.append(f"\U0001F525 Por: <b>{current}</b>")
        if discount:
            lines.append(f"\U0001F3AF {discount}")
        if offer.installments_qty > 1 and offer.installment_value > 0:
            iv = format_price(offer.installment_value)
            lines.append(f"\U0001F4B3 {offer.installments_qty}x de {iv}")
        if offer.promo_code:
            lines.append(f"\U0001F39F <b>Cupom:</b> {offer.promo_code}")
        elif offer.coupon_label:
            lines.append(f"\U0001F39F {offer.coupon_label}")
        if offer.has_full_shipping:
            lines.append("\U0001F69A <b>Frete Gr\u00E1tis FULL</b>")
        elif offer.has_free_shipping:
            lines.append("\U0001F69A Frete Gr\u00E1tis")
        if url:
            lines.extend(["", f"\U0001F6D2 <a href='{url}'>Ver Oferta</a>"])
        lines.extend(["", f"\U0001F4E2 {random.choice(CTA_PHRASES)}"])

        return "\n".join(lines)
