"""Unit tests for per-brand error isolation in report_generation.py (BRI-1274).

Verifies that when one brand's LLM call raises ReportGenerationError, the
remaining brands are still processed and the failed brand appears in
digest_lines with an ``error`` field.
"""
from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Stub out optional deps that may not be installed in the dev/test environment
for _mod in ("schedule", "markdown"):
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)


REFERENCE_DATE = datetime(2026, 4, 19, 10, 0, 0)


def _make_fake_report(brand_key: str, brand_name: str) -> dict:
    return {
        "brand": brand_key,
        "brand_name": brand_name,
        "content": (
            f"# {brand_name} — Trend Antenna Report\n\n"
            "## Top signal here\n\nBody text."
        ),
        "timestamp": REFERENCE_DATE,
        "report_id": f"trend-antenna_{brand_key}_20260419_100000",
        "post_count": 5,
        "post_ids": [],
        "subreddits": [],
    }


def _run_generate(brand_side_effects: dict) -> tuple[dict, list]:
    """Patch report_processor.generate_brand_report per brand_side_effects, then
    call generate_report() with save_to_db=False, save_to_file=False.

    Returns (report_paths, digest_lines_captured).
    """
    from services.llm_processing.clients.base_client import ReportGenerationError
    from config import BRANDS

    def fake_generate_brand_report(brand_key, **kwargs):
        effect = brand_side_effects.get(brand_key)
        if isinstance(effect, Exception):
            raise effect
        brand_name = BRANDS[brand_key]["name"]
        return _make_fake_report(brand_key, brand_name)

    captured_digest: list = []

    def fake_post_digest(digest_lines, run_date):
        captured_digest.extend(digest_lines)
        return True

    with (
        patch("report_generation.RedditDataCollector") as MockCollector,
        patch("report_generation.ReportProcessor") as MockProcessor,
        patch("report_generation.MongoDBClient") as MockMongo,
        patch("report_generation.post_report_to_kb"),
        patch("report_generation.post_digest_to_telegram", side_effect=fake_post_digest),
    ):
        mock_collector = MockCollector.return_value
        mock_collector.get_detailed_subreddit_posts.return_value = []
        mock_collector.get_weekly_popular_posts.return_value = []
        mock_collector.get_monthly_popular_posts.return_value = []

        mock_processor = MockProcessor.return_value
        mock_processor.generate_brand_report.side_effect = fake_generate_brand_report
        mock_processor.save_report_to_file.return_value = "/fake/path.md"

        mock_mongo = MockMongo.return_value
        mock_mongo.get_latest_report.return_value = None
        mock_mongo.insert_or_update_posts.return_value = {"inserted": 0, "updated": 0}

        from report_generation import generate_report
        report_paths = generate_report(
            skip_mongodb=True,
            reference_date=REFERENCE_DATE,
            save_to_db=False,
            save_to_file=True,  # needed so post_digest_to_telegram is called
        )

    return report_paths, captured_digest


class TestPerBrandErrorIsolation(unittest.TestCase):
    """generate_report() must isolate ReportGenerationError per brand."""

    def test_one_brand_fails_others_still_in_digest(self):
        from services.llm_processing.clients.base_client import ReportGenerationError

        _, digest = _run_generate({
            "ztm": ReportGenerationError("LLM failed after retries: timeout"),
        })

        keys = [e["brand_key"] for e in digest]
        self.assertIn("ztm", keys, "failed brand must appear in digest")
        self.assertIn("tch", keys)
        self.assertIn("gbq_cm", keys)
        self.assertIn("fps", keys)

    def test_failed_brand_has_error_field_and_null_top_signal(self):
        from services.llm_processing.clients.base_client import ReportGenerationError

        err_msg = "LLM failed after retries: connection refused"
        _, digest = _run_generate({
            "tch": ReportGenerationError(err_msg),
        })

        tch_entry = next(e for e in digest if e["brand_key"] == "tch")
        self.assertIn("error", tch_entry)
        self.assertEqual(tch_entry["error"], err_msg)
        self.assertIsNone(tch_entry["top_signal"])

    def test_failed_brand_excluded_from_report_paths(self):
        from services.llm_processing.clients.base_client import ReportGenerationError

        report_paths, _ = _run_generate({
            "ztm": ReportGenerationError("LLM failed"),
        })

        self.assertNotIn("ztm", report_paths)
        self.assertIn("tch", report_paths)

    def test_successful_brand_has_no_error_field(self):
        _, digest = _run_generate({})

        for entry in digest:
            self.assertNotIn("error", entry, f"{entry['brand_key']} should have no error field")

    def test_all_brands_fail_returns_empty_report_paths(self):
        from services.llm_processing.clients.base_client import ReportGenerationError

        err = ReportGenerationError("all fail")
        report_paths, digest = _run_generate({
            "ztm": err,
            "tch": err,
            "gbq_cm": err,
            "fps": err,
        })

        self.assertEqual(report_paths, {})
        self.assertEqual(len(digest), 4)
        for entry in digest:
            self.assertIn("error", entry)


if __name__ == "__main__":
    unittest.main()
