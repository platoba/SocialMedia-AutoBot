"""Tests for app.config module."""

import os
import pytest
from unittest.mock import patch


class TestTelegramConfig:
    def test_valid_token(self):
        with patch.dict(os.environ, {"BOT_TOKEN": "123:ABC"}):
            from app.config import TelegramConfig
            cfg = TelegramConfig()
            assert cfg.token == "123:ABC"
            assert "123:ABC" in cfg.api_url

    def test_missing_token_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "BOT_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            from app.config import TelegramConfig
            with pytest.raises(ValueError, match="BOT_TOKEN"):
                TelegramConfig()


class TestInstagramConfig:
    def test_configured(self):
        with patch.dict(os.environ, {
            "IG_ACCESS_TOKEN": "tok", "IG_BUSINESS_ID": "123",
            "BOT_TOKEN": "t"
        }):
            from app.config import InstagramConfig
            cfg = InstagramConfig()
            assert cfg.configured is True

    def test_not_configured(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID")}
        env["BOT_TOKEN"] = "t"
        with patch.dict(os.environ, env, clear=True):
            from app.config import InstagramConfig
            cfg = InstagramConfig()
            assert cfg.configured is False


class TestTwitterConfig:
    def test_configured(self):
        with patch.dict(os.environ, {
            "TW_BEARER_TOKEN": "bearer", "BOT_TOKEN": "t"
        }):
            from app.config import TwitterConfig
            cfg = TwitterConfig()
            assert cfg.configured is True

    def test_not_configured(self):
        env = {"BOT_TOKEN": "t"}
        with patch.dict(os.environ, env, clear=True):
            from app.config import TwitterConfig
            cfg = TwitterConfig()
            assert cfg.configured is False


class TestTikTokConfig:
    def test_configured(self):
        with patch.dict(os.environ, {
            "TT_ACCESS_TOKEN": "tok", "BOT_TOKEN": "t"
        }):
            from app.config import TikTokConfig
            cfg = TikTokConfig()
            assert cfg.configured is True


class TestSchedulerConfig:
    def test_defaults(self):
        with patch.dict(os.environ, {"BOT_TOKEN": "t"}):
            from app.config import SchedulerConfig
            cfg = SchedulerConfig()
            assert cfg.max_posts_per_day == 10
            assert "scheduler.db" in cfg.db_path

    def test_custom_values(self):
        with patch.dict(os.environ, {
            "BOT_TOKEN": "t",
            "SCHEDULER_DB": "/tmp/test.db",
            "MAX_POSTS_PER_DAY": "20",
            "TZ": "Asia/Shanghai"
        }):
            from app.config import SchedulerConfig
            cfg = SchedulerConfig()
            assert cfg.max_posts_per_day == 20
            assert cfg.timezone == "Asia/Shanghai"


class TestAppConfig:
    def test_active_platforms_none(self):
        env = {"BOT_TOKEN": "t"}
        with patch.dict(os.environ, env, clear=True):
            from app.config import AppConfig
            cfg = AppConfig()
            assert cfg.active_platforms == []

    def test_active_platforms_with_ig(self):
        with patch.dict(os.environ, {
            "BOT_TOKEN": "t",
            "IG_ACCESS_TOKEN": "tok",
            "IG_BUSINESS_ID": "123"
        }):
            from app.config import AppConfig
            cfg = AppConfig()
            assert "Instagram" in cfg.active_platforms
