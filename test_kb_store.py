"""Unit tests for KB store dual-write integration (BRI-1252).

All tests mock requests.post so no real network calls are made.
"""

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import requests

from services.kb_store import post_report_to_kb


REFERENCE_DATE = datetime(2026, 4, 18, 6, 0, 0)
SAMPLE_CONTENT = "# Trend Antenna — Zero to Made — 2026-04-18\n\nSome signals here."
SAMPLE_BRAND_KEY = "ztm"
SAMPLE_BRAND_NAME = "Zero to Made"
SAMPLE_REPORT_ID = "trend-antenna_ztm_20260418_060000"

_BASE_ENV = {
    "KB_STORE_URL": "https://ufpmcvawhbflmvauwdez.supabase.co/functions/v1/webhook/knowledge/store",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "KB_STORE_ENABLED": "true",
}


def _make_mock_response(status_code: int = 201, text: str = "created") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestPostReportToKbContract(unittest.TestCase):
    """Assert the POST body matches the KB store contract."""

    @patch("services.kb_store.requests.post")
    def test_post_body_matches_contract(self, mock_post):
        mock_post.return_value = _make_mock_response(201)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertTrue(result)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]

        self.assertEqual(payload["doc_type"], "note")
        self.assertEqual(payload["title"], "Trend Antenna — Zero to Made — 2026-04-18")
        self.assertEqual(payload["content"], SAMPLE_CONTENT)
        self.assertIn("trend-antenna", payload["tags"])
        self.assertIn("ztm", payload["tags"])
        self.assertEqual(payload["source_key"], SAMPLE_REPORT_ID)

    @patch("services.kb_store.requests.post")
    def test_authorization_header_uses_anon_key(self, mock_post):
        mock_post.return_value = _make_mock_response(201)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-anon-key")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("services.kb_store.requests.post")
    def test_correct_url_called(self, mock_post):
        mock_post.return_value = _make_mock_response(201)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, _BASE_ENV["KB_STORE_URL"])


class TestPostReportToKbAllBrands(unittest.TestCase):
    """Assert correct tags are emitted for all four brand slugs."""

    @patch("services.kb_store.requests.post")
    def test_all_brand_slugs(self, mock_post):
        mock_post.return_value = _make_mock_response(201)

        brands = [
            ("ztm", "Zero to Made"),
            ("tch", "The Creator Handbook"),
            ("gbq_cm", "Great British Quizzes / Charlie Mercer"),
            ("fps", "First Person Science"),
        ]

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            for brand_key, brand_name in brands:
                mock_post.reset_mock()
                result = post_report_to_kb(
                    content=SAMPLE_CONTENT,
                    brand_key=brand_key,
                    brand_name=brand_name,
                    report_id=f"trend-antenna_{brand_key}_20260418_060000",
                    reference_date=REFERENCE_DATE,
                )
                self.assertTrue(result, f"Expected True for brand '{brand_key}'")
                _, kwargs = mock_post.call_args
                payload = kwargs["json"]
                self.assertIn("trend-antenna", payload["tags"])
                self.assertIn(brand_key, payload["tags"])


class TestPostReportToKbDryRun(unittest.TestCase):
    """KB_STORE_ENABLED=false must suppress all network calls."""

    @patch("services.kb_store.requests.post")
    def test_dry_run_skips_post(self, mock_post):
        env = {**_BASE_ENV, "KB_STORE_ENABLED": "false"}

        with patch.dict(os.environ, env, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch("services.kb_store.requests.post")
    def test_dry_run_case_insensitive(self, mock_post):
        """KB_STORE_ENABLED=False (capital F) should also disable."""
        env = {**_BASE_ENV, "KB_STORE_ENABLED": "False"}

        with patch.dict(os.environ, env, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)
        mock_post.assert_not_called()


class TestPostReportToKbMissingConfig(unittest.TestCase):
    """Missing env vars must skip silently and return False."""

    @patch("services.kb_store.requests.post")
    def test_missing_kb_store_url_returns_false(self, mock_post):
        env = {k: v for k, v in _BASE_ENV.items() if k != "KB_STORE_URL"}

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("KB_STORE_URL", None)
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch("services.kb_store.requests.post")
    def test_missing_anon_key_returns_false(self, mock_post):
        env = {k: v for k, v in _BASE_ENV.items() if k != "SUPABASE_ANON_KEY"}

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SUPABASE_ANON_KEY", None)
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)
        mock_post.assert_not_called()


class TestPostReportToKbFailureHandling(unittest.TestCase):
    """Non-2xx and network errors must return False without raising."""

    @patch("services.kb_store.requests.post")
    def test_non_2xx_returns_false(self, mock_post):
        mock_post.return_value = _make_mock_response(500, "Internal Server Error")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)

    @patch("services.kb_store.requests.post")
    def test_4xx_returns_false(self, mock_post):
        mock_post.return_value = _make_mock_response(401, "Unauthorized")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)

    @patch("services.kb_store.requests.post")
    def test_timeout_returns_false(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout()

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)

    @patch("services.kb_store.requests.post")
    def test_connection_error_returns_false(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("unreachable")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_report_to_kb(
                content=SAMPLE_CONTENT,
                brand_key=SAMPLE_BRAND_KEY,
                brand_name=SAMPLE_BRAND_NAME,
                report_id=SAMPLE_REPORT_ID,
                reference_date=REFERENCE_DATE,
            )

        self.assertFalse(result)

    @patch("services.kb_store.requests.post")
    def test_one_brand_failure_does_not_affect_others(self, mock_post):
        """Simulate report loop: first brand fails, second succeeds."""
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("down"),
            _make_mock_response(201),
        ]

        brands = [("ztm", "Zero to Made"), ("tch", "The Creator Handbook")]
        results = []

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            for brand_key, brand_name in brands:
                results.append(
                    post_report_to_kb(
                        content=SAMPLE_CONTENT,
                        brand_key=brand_key,
                        brand_name=brand_name,
                        report_id=f"trend-antenna_{brand_key}_20260418_060000",
                        reference_date=REFERENCE_DATE,
                    )
                )

        self.assertFalse(results[0])
        self.assertTrue(results[1])


if __name__ == "__main__":
    unittest.main()
