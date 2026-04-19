"""KB Store integration — dual-write reports to Supabase Knowledge Brain.

After each per-brand markdown report is written to disk, POST it to the
Supabase KB store webhook so M4 pre-flight can query via search_knowledge.

Env vars (read at call time to keep tests easy):
  KB_STORE_URL       Full webhook URL (e.g. https://<project>.supabase.co/functions/v1/store-document)
  SUPABASE_ANON_KEY  Bearer token for the Supabase Edge Function
  KB_STORE_ENABLED   Set to 'false' to skip all KB posts (default: 'true')
"""

import os
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 30  # seconds


def post_report_to_kb(
    content: str,
    brand_key: str,
    brand_name: str,
    report_id: str,
    reference_date: datetime,
) -> bool:
    """POST a report to the Supabase KB store webhook.

    Idempotency: `source_key` is set to the deterministic `report_id`
    (e.g. ``trend-antenna_ztm_20260418_060000``). If the webhook dedupes
    on this field, re-running the same report will not create a duplicate.
    See PR description for the dedupe story.

    Failure handling: any non-2xx response or network exception is logged
    and returns False — callers must NOT raise on False; the overall run
    continues with remaining brands.

    Args:
        content: Full markdown report body.
        brand_key: Brand slug — one of ``ztm``, ``tch``, ``gbq_cm``, ``fps``.
        brand_name: Human-readable brand name for the KB entry title.
        report_id: Deterministic report ID used as ``source_key``.
        reference_date: Report reference date used in the KB entry title.

    Returns:
        True if the KB store accepted the payload (2xx), False otherwise.
    """
    kb_store_enabled = os.getenv("KB_STORE_ENABLED", "true").lower() == "true"
    if not kb_store_enabled:
        logger.info("KB_STORE_ENABLED=false — skipping KB post for brand '%s'", brand_key)
        return False

    kb_store_url = os.getenv("KB_STORE_URL", "").strip()
    if not kb_store_url:
        logger.warning(
            "KB_STORE_URL not set — skipping KB post for brand '%s'. "
            "Add KB_STORE_URL to your .env to enable dual-write.",
            brand_key,
        )
        return False

    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not supabase_anon_key:
        logger.warning(
            "SUPABASE_ANON_KEY not set — skipping KB post for brand '%s'.",
            brand_key,
        )
        return False

    date_str = reference_date.strftime("%Y-%m-%d")
    payload = {
        "doc_type": "note",
        "title": f"Trend Antenna — {brand_name} — {date_str}",
        "content": content,
        "tags": ["trend-antenna", brand_key],
        "source_key": report_id,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {supabase_anon_key}",
    }

    try:
        response = requests.post(
            kb_store_url,
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
        if 200 <= response.status_code < 300:
            logger.info(
                "KB store: posted '%s' for brand '%s' (HTTP %d)",
                report_id,
                brand_key,
                response.status_code,
            )
            return True
        else:
            logger.error(
                "KB store: non-2xx response for brand '%s': HTTP %d — %s",
                brand_key,
                response.status_code,
                response.text[:300],
            )
            return False
    except requests.exceptions.Timeout:
        logger.error(
            "KB store: request timed out after %ds for brand '%s'",
            _REQUEST_TIMEOUT,
            brand_key,
        )
        return False
    except requests.exceptions.RequestException as exc:
        logger.error(
            "KB store: request failed for brand '%s': %s",
            brand_key,
            exc,
        )
        return False
