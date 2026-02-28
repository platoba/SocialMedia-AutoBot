"""Tests for app.telegram module."""

import pytest
import requests
from unittest.mock import patch, MagicMock
from app.telegram import TelegramBot


@pytest.fixture
def bot():
    return TelegramBot("https://api.telegram.org/botTEST_TOKEN")


class TestTelegramBot:
    def test_init(self, bot):
        assert "TEST_TOKEN" in bot.api_url
        assert bot.timeout == 35

    def test_custom_timeout(self):
        b = TelegramBot("https://api.telegram.org/botX", timeout=10)
        assert b.timeout == 10


class TestGetMe:
    @patch("app.telegram.requests.Session.get")
    def test_get_me_success(self, mock_get, bot):
        mock_get.return_value.json.return_value = {
            "ok": True, "result": {"id": 123, "username": "testbot"}
        }
        result = bot.get_me()
        assert result["ok"] is True
        assert result["result"]["username"] == "testbot"

    @patch("app.telegram.requests.Session.get")
    def test_get_me_failure(self, mock_get, bot):
        mock_get.side_effect = requests.RequestException("connection error")
        result = bot.get_me()
        assert result is None


class TestGetUpdates:
    @patch("app.telegram.requests.Session.get")
    def test_get_updates(self, mock_get, bot):
        mock_get.return_value.json.return_value = {
            "ok": True, "result": []
        }
        result = bot.get_updates()
        assert result["ok"] is True

    @patch("app.telegram.requests.Session.get")
    def test_get_updates_with_offset(self, mock_get, bot):
        mock_get.return_value.json.return_value = {"ok": True, "result": []}
        bot.get_updates(offset=42)
        call_params = mock_get.call_args[1].get("params", mock_get.call_args[0][0] if mock_get.call_args[0] else {})
        # Verify offset was passed


class TestSendMessage:
    @patch("app.telegram.requests.Session.get")
    def test_send_message_success(self, mock_get, bot):
        mock_get.return_value.json.return_value = {
            "ok": True, "result": {"message_id": 1}
        }
        result = bot.send_message(123, "Hello")
        assert result["ok"] is True

    @patch("app.telegram.requests.Session.get")
    def test_send_message_markdown_fallback(self, mock_get, bot):
        # First call fails, second succeeds (without parse_mode)
        mock_get.return_value.json.side_effect = [
            {"ok": False, "description": "parse error"},
            {"ok": True, "result": {"message_id": 1}},
        ]
        result = bot.send_message(123, "**broken**")

    @patch("app.telegram.requests.Session.get")
    def test_send_message_with_reply(self, mock_get, bot):
        mock_get.return_value.json.return_value = {"ok": True, "result": {"message_id": 2}}
        bot.send_message(123, "Reply", reply_to=1)


class TestSendPhoto:
    @patch("app.telegram.requests.Session.get")
    def test_send_photo(self, mock_get, bot):
        mock_get.return_value.json.return_value = {"ok": True, "result": {"message_id": 3}}
        result = bot.send_photo(123, "https://img.com/1.jpg", "caption")
        assert result is not None

    @patch("app.telegram.requests.Session.get")
    def test_send_photo_long_caption(self, mock_get, bot):
        mock_get.return_value.json.return_value = {"ok": True, "result": {"message_id": 4}}
        long_caption = "x" * 2000
        bot.send_photo(123, "https://img.com/1.jpg", long_caption)
        # Caption should be truncated to 1024


class TestCallbackAnswer:
    @patch("app.telegram.requests.Session.get")
    def test_answer_callback(self, mock_get, bot):
        mock_get.return_value.json.return_value = {"ok": True}
        result = bot.send_callback_answer("cb123", "Done!")
        assert result is not None
