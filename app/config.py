"""Configuration management with validation."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TelegramConfig:
    token: str = ""
    api_url: str = ""

    def __post_init__(self):
        self.token = os.environ.get("BOT_TOKEN", "")
        if not self.token:
            raise ValueError("BOT_TOKEN environment variable is required")
        self.api_url = f"https://api.telegram.org/bot{self.token}"


@dataclass
class InstagramConfig:
    access_token: str = ""
    business_id: str = ""
    api_version: str = "v19.0"
    base_url: str = ""

    def __post_init__(self):
        self.access_token = os.environ.get("IG_ACCESS_TOKEN", "")
        self.business_id = os.environ.get("IG_BUSINESS_ID", "")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    @property
    def configured(self) -> bool:
        return bool(self.access_token and self.business_id)


@dataclass
class TwitterConfig:
    bearer_token: str = ""
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    access_secret: str = ""

    def __post_init__(self):
        self.bearer_token = os.environ.get("TW_BEARER_TOKEN", "")
        self.api_key = os.environ.get("TW_API_KEY", "")
        self.api_secret = os.environ.get("TW_API_SECRET", "")
        self.access_token = os.environ.get("TW_ACCESS_TOKEN", "")
        self.access_secret = os.environ.get("TW_ACCESS_SECRET", "")

    @property
    def configured(self) -> bool:
        return bool(self.bearer_token)


@dataclass
class TikTokConfig:
    access_token: str = ""
    open_id: str = ""

    def __post_init__(self):
        self.access_token = os.environ.get("TT_ACCESS_TOKEN", "")
        self.open_id = os.environ.get("TT_OPEN_ID", "")

    @property
    def configured(self) -> bool:
        return bool(self.access_token)


@dataclass
class SchedulerConfig:
    db_path: str = ""
    max_posts_per_day: int = 10
    timezone: str = "UTC"

    def __post_init__(self):
        self.db_path = os.environ.get("SCHEDULER_DB", "data/scheduler.db")
        self.max_posts_per_day = int(os.environ.get("MAX_POSTS_PER_DAY", "10"))
        self.timezone = os.environ.get("TZ", "UTC")


@dataclass
class AppConfig:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    tiktok: TikTokConfig = field(default_factory=TikTokConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    log_level: str = "INFO"
    data_dir: str = "data"

    def __post_init__(self):
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.data_dir = os.environ.get("DATA_DIR", "data")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def active_platforms(self) -> list[str]:
        platforms = []
        if self.instagram.configured:
            platforms.append("Instagram")
        if self.twitter.configured:
            platforms.append("Twitter")
        if self.tiktok.configured:
            platforms.append("TikTok")
        return platforms
