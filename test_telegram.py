"""Unit tests for Telegram digest notification (BRI-1266).

All tests mock requests.post so no real network calls are made.
"""

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

from services.telegram import post_digest_to_telegram


REFERENCE_DATE = datetime(2026, 4, 18, 6, 0, 0)

_BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "test-bot-token",
    "TELEGRAM_CHAT_ID": "123456789",
    "TELEGRAM_NOTIFY_ENABLED": "true",
}

SAMPLE_DIGEST_LINES = [
    {"brand_key": "ztm", "brand_name": "Zero to Made", "top_signal": "No-code AI builders dominate"},
    {"brand_key": "tch", "brand_name": "The Creator Handbook", "top_signal": "Podcasting growth surge"},
    {"brand_key": "gbq_cm", "brand_name": "Great British Quizzes / Charlie Mercer", "top_signal": None},
    {"brand_key": "fps", "brand_name": "First Person Science", "top_signal": "Mental health memoir demand"},
]


def _make_mock_response(status_code: int = 200, text: str = "ok") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestPostDigestToTelegramContract(unittest.TestCase):
    """Assert the message format and API call match the Telegram contract."""

    @patch("services.telegram.requests.post")
    def test_message_contains_date_header(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertTrue(result)
        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("📡 *Trend Antenna — 2026-04-18*", text)

    @patch("services.telegram.requests.post")
    def test_message_contains_review_footer(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("_Review: /pre-flight in Claude Code or query KB_", text)

    @patch("services.telegram.requests.post")
    def test_message_uses_markdown_parse_mode(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["parse_mode"], "Markdown")

    @patch("services.telegram.requests.post")
    def test_message_disables_web_page_preview(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        self.assertTrue(kwargs["json"]["disable_web_page_preview"])

    @patch("services.telegram.requests.post")
    def test_correct_url_called(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://api.telegram.org/bottest-bot-token/sendMessage")

    @patch("services.telegram.requests.post")
    def test_chat_id_in_payload(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["chat_id"], "123456789")


class TestPostDigestToTelegramAllBrands(unittest.TestCase):
    """Assert all four brands render correctly in the message."""

    @patch("services.telegram.requests.post")
    def test_four_brands_all_present(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertTrue(result)
        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("*Zero to Made:*", text)
        self.assertIn("*The Creator Handbook:*", text)
        self.assertIn("*Great British Quizzes / Charlie Mercer:*", text)
        self.assertIn("*First Person Science:*", text)

    @patch("services.telegram.requests.post")
    def test_none_top_signal_renders_as_no_strong_signals(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        digest = [{"brand_key": "gbq_cm", "brand_name": "GBQ/CM", "top_signal": None}]

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(digest, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("*GBQ/CM:* no strong signals", text)

    @patch("services.telegram.requests.post")
    def test_top_signal_text_appears_in_message(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        digest = [{"brand_key": "ztm", "brand_name": "Zero to Made", "top_signal": "AI builders dominate"}]

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(digest, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("*Zero to Made:* AI builders dominate", text)

    @patch("services.telegram.requests.post")
    def test_error_entry_renders_with_warning_emoji(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        digest = [
            {"brand_key": "ztm", "brand_name": "Zero to Made", "top_signal": None, "error": "LLM failed after retries: timeout"},
        ]

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(digest, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("⚠️ generation failed", text)
        self.assertIn("*Zero to Made:*", text)
        self.assertNotIn("no strong signals", text)

    @patch("services.telegram.requests.post")
    def test_error_entry_does_not_suppress_other_brands(self, mock_post):
        mock_post.return_value = _make_mock_response(200)

        digest = [
            {"brand_key": "ztm", "brand_name": "Zero to Made", "top_signal": None, "error": "LLM timed out"},
            {"brand_key": "tch", "brand_name": "The Creator Handbook", "top_signal": "Podcasting surge"},
        ]

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            post_digest_to_telegram(digest, REFERENCE_DATE)

        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        self.assertIn("*Zero to Made:* ⚠️ generation failed", text)
        self.assertIn("*The Creator Handbook:* Podcasting surge", text)


class TestPostDigestToTelegramDryRun(unittest.TestCase):
    """TELEGRAM_NOTIFY_ENABLED not 'true' must suppress all network calls."""

    @patch("services.telegram.requests.post")
    def test_missing_enabled_skips_post(self, mock_post):
        env = {k: v for k, v in _BASE_ENV.items() if k != "TELEGRAM_NOTIFY_ENABLED"}

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_NOTIFY_ENABLED", None)
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch("services.telegram.requests.post")
    def test_enabled_false_skips_post(self, mock_post):
        env = {**_BASE_ENV, "TELEGRAM_NOTIFY_ENABLED": "false"}

        with patch.dict(os.environ, env, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch("services.telegram.requests.post")
    def test_enabled_false_case_insensitive(self, mock_post):
        """TELEGRAM_NOTIFY_ENABLED=False (capital F) should also disable."""
        env = {**_BASE_ENV, "TELEGRAM_NOTIFY_ENABLED": "False"}

        with patch.dict(os.environ, env, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)
        mock_post.assert_not_called()


class TestPostDigestToTelegramMissingConfig(unittest.TestCase):
    """Missing token or chat_id must skip silently and return False."""

    @patch("services.telegram.requests.post")
    def test_missing_bot_token_returns_false(self, mock_post):
        env = {k: v for k, v in _BASE_ENV.items() if k != "TELEGRAM_BOT_TOKEN"}

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)
        mock_post.assert_not_called()

    @patch("services.telegram.requests.post")
    def test_missing_chat_id_returns_false(self, mock_post):
        env = {k: v for k, v in _BASE_ENV.items() if k != "TELEGRAM_CHAT_ID"}

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_CHAT_ID", None)
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)
        mock_post.assert_not_called()


class TestPostDigestToTelegramFailureHandling(unittest.TestCase):
    """Non-2xx and network errors must return False without raising."""

    @patch("services.telegram.requests.post")
    def test_non_2xx_returns_false(self, mock_post):
        mock_post.return_value = _make_mock_response(500, "Internal Server Error")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)

    @patch("services.telegram.requests.post")
    def test_4xx_returns_false(self, mock_post):
        mock_post.return_value = _make_mock_response(401, "Unauthorized")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)

    @patch("services.telegram.requests.post")
    def test_timeout_returns_false(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout()

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)

    @patch("services.telegram.requests.post")
    def test_connection_error_returns_false(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("unreachable")

        with patch.dict(os.environ, _BASE_ENV, clear=False):
            result = post_digest_to_telegram(SAMPLE_DIGEST_LINES, REFERENCE_DATE)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
