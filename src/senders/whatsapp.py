import logging

import requests

from src.utils.price import format_price

logger = logging.getLogger("senders.whatsapp")


class WhatsAppSender:
    def __init__(self, api_url: str = "", api_key: str = ""):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def send_offer(self, phone: str, offer) -> bool:
        message = self._format_message(offer)
        return self._send(phone, message)

    def send_alert(self, phone: str, text: str) -> bool:
        return self._send(phone, f"\u26A0\uFE0F *Bot*\n\n{text}")

    def _send(self, phone: str, message: str) -> bool:
        if not self.api_url:
            logger.warning("whatsapp_not_configured")
            return False
        try:
            payload = {
                "number": phone,
                "text": message,
            }
            resp = requests.post(
                f"{self.api_url}/send",
                json=payload,
                headers=self.headers,
                timeout=15,
            )
            if resp.ok:
                logger.info("message_sent", extra={"phone": phone[:6]})
                return True
            logger.error("send_failed", extra={
                "status": resp.status_code, "text": resp.text[:200],
            })
            return False
        except Exception as e:
            logger.error("send_exception", extra={"error": str(e)})
            return False

    def _format_message(self, offer) -> str:
        current = format_price(offer.current_price)
        old = format_price(offer.original_price) if offer.original_price else ""
        discount = offer.discount_label.strip() if offer.discount_label else ""

        lines = [
            f"\U0001F525 *PROMO\u00C7\u00C3O {offer.platform_label.upper()}*",
            "",
            f"*{offer.title[:100]}*",
        ]
        if old:
            lines.append(f"De: ~{old}~")
        lines.append(f"Por: *{current}*")
        if discount:
            lines.append(f"{discount}")
        if offer.promo_code:
            lines.append(f"Cupom: {offer.promo_code}")
        if offer.has_free_shipping:
            lines.append("Frete Gr\u00E1tis")
        if offer.clean_url:
            lines.append("")
            lines.append(f"Link: {offer.clean_url}")

        return "\n".join(lines)
