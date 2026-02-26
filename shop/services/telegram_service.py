import urllib.parse
import urllib.request

from django.conf import settings

import logging

logger = logging.getLogger(__name__)


def telegram_send_message(text: str) -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "") or ""
    logger.info("Telegram: token present=%s, chat_id=%s", bool(token), chat_id)
    if not token or not chat_id:
        logger.warning("Telegram: missing token or chat_id")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ok = getattr(resp, "status", 200) == 200
            if not ok:
                logger.error(
                    "Telegram sendMessage failed: status=%s body=%s",
                    getattr(resp, "status", "?"),
                    body[:500],
                )
            else:
                logger.info("Telegram message sent successfully")
            return ok
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:500]
        logger.error("Telegram HTTPError: status=%s body=%s", e.code, error_body)
        return False
    except Exception:
        logger.exception("Telegram sendMessage exception")
        return False


def telegram_format_order_message(order, items, total, lang: str) -> str:
    def esc(s):
        if s is None:
            return ""
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    lines = [
        f"🧾 <b>Новый заказ #{esc(order.id)}</b>"
        if lang == "ru"
        else f"🧾 <b>Нове замовлення #{esc(order.id)}</b>",
        f"<b>Клиент:</b> {esc(order.full_name)}"
        if lang == "ru"
        else f"<b>Клієнт:</b> {esc(order.full_name)}",
        f"<b>Телефон:</b> {esc(order.phone)}",
        f"<b>Email:</b> {esc(order.email)}",
        f"<b>Город:</b> {esc(order.city)}"
        if lang == "ru"
        else f"<b>Місто:</b> {esc(order.city)}",
        f"<b>Отделение:</b> {esc(order.warehouse)}"
        if lang == "ru"
        else f"<b>Відділення:</b> {esc(order.warehouse)}",
    ]

    if getattr(order, "payment_method", ""):
        pm = str(order.payment_method)
        if lang == "ru":
            pm_label = {
                "card": "Оплата картой",
                "cod": "Оплата наложенным платежом",
            }.get(pm, pm)
        else:
            pm_label = {
                "card": "Оплата карткою",
                "cod": "Оплата накладеним платежем",
            }.get(pm, pm)
        lines.append(f"<b>Оплата:</b> {esc(pm_label)}")

    lines.append("")
    lines.append("<b>Товары:</b>" if lang == "ru" else "<b>Товари:</b>")
    for it in items:
        candle = it.get("candle")
        qty = it.get("qty")
        subtotal = it.get("subtotal")
        options_display = it.get("options_display", {})
        try:
            name = (
                candle.display_name
                if not callable(getattr(candle, "display_name", None))
                else candle.display_name()
            )
        except Exception:
            name = str(candle)

        lines.append(f"• {esc(name)} × {esc(qty)} — {esc(subtotal)}")

        if options_display:
            opts_str = ", ".join([f"{k}: {v}" for k, v in options_display.items()])
            lines.append(f"  └ {esc(opts_str)}")

    lines.append("")
    lines.append(
        (f"<b>Итого:</b> {esc(total)}" if lang == "ru" else f"<b>Разом:</b> {esc(total)}")
    )

    if getattr(order, "notes", None):
        lines.append("")
        lines.append(
            f"<b>Примечания:</b> {esc(order.notes)}"
            if lang == "ru"
            else f"<b>Нотатки:</b> {esc(order.notes)}"
        )

    return "\n".join(lines)
