"""Telegram digest notification — weekly push after cron run completes.

Sends a one-shot summary to a Telegram chat when all per-brand reports are
written and POSTed to the KB store.

Env vars (read at call time to keep tests easy):
  TELEGRAM_BOT_TOKEN       Bot token from @BotFather
  TELEGRAM_CHAT_ID         Target chat or channel ID
  TELEGRAM_NOTIFY_ENABLED  Set to 'true' to enable (default: not set → dry-run)
"""

import os
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 30  # seconds
_TELEGRAM_API_BASE = "https://api.telegram.org"


def post_digest_to_telegram(digest_lines: list[dict], run_date: datetime) -> bool:
    """POST a weekly digest summary to Telegram.

    Failure handling: any non-2xx response or network exception is logged and
    returns False — callers must NOT raise on False; the overall run continues.

    Args:
        digest_lines: List of dicts with keys ``brand_key``, ``brand_name``,
            and ``top_signal`` (str or None). Caller is responsible for
            extracting the signal text from the report content.
        run_date: Run reference date used in the message header.

    Returns:
        True if Telegram accepted the message (2xx), False otherwise.
    """
    notify_enabled = os.getenv("TELEGRAM_NOTIFY_ENABLED", "").strip().lower() == "true"
    if not notify_enabled:
        logger.info("TELEGRAM_NOTIFY_ENABLED not 'true' — skipping Telegram digest")
        return False

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram digest")
        return False

    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping Telegram digest")
        return False

    date_str = run_date.strftime("%Y-%m-%d")
    message_parts = [f"📡 *Trend Antenna — {date_str}*", ""]

    for entry in digest_lines:
        brand_name = entry.get("brand_name", "")
        top_signal = entry.get("top_signal")
        signal_text = top_signal if top_signal else "no strong signals"
        message_parts.append(f"*{brand_name}:* {signal_text}")

    message_parts.append("")
    message_parts.append("_Review: /pre-flight in Claude Code or query KB_")

    message = "\n".join(message_parts)

    url = f"{_TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
        if 200 <= response.status_code < 300:
            logger.info("Telegram digest sent (HTTP %d)", response.status_code)
            return True
        else:
            logger.error(
                "Telegram: non-2xx response: HTTP %d — %s",
                response.status_code,
                response.text[:300],
            )
            return False
    except requests.exceptions.Timeout:
        logger.error("Telegram: request timed out after %ds", _REQUEST_TIMEOUT)
        return False
    except requests.exceptions.RequestException as exc:
        logger.error("Telegram: request failed: %s", exc)
        return False
