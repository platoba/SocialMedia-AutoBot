"""Analytics and competitor tracking with SQLite persistence."""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Analytics:
    """Track competitors and store engagement metrics."""

    def __init__(self, db_path: str = "data/analytics.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tracked_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT DEFAULT '',
                UNIQUE(platform, username)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                followers INTEGER DEFAULT 0,
                posts INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                extra_json TEXT DEFAULT '{}',
                captured_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS post_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                captured_at TEXT NOT NULL,
                UNIQUE(platform, post_id, captured_at)
            );
        """)
        self.db.commit()

    def track(self, platform: str, username: str, notes: str = "") -> str:
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO tracked_accounts (platform, username, added_at, notes) "
                "VALUES (?, ?, ?, ?)",
                (platform.lower(), username.lower(), datetime.now().isoformat(), notes)
            )
            self.db.commit()
            return f"✅ 已追踪 {platform} @{username}"
        except Exception as e:
            logger.error("Track error: %s", e)
            return f"❌ 追踪失败: {e}"

    def untrack(self, platform: str, username: str) -> str:
        cur = self.db.execute(
            "DELETE FROM tracked_accounts WHERE platform=? AND username=?",
            (platform.lower(), username.lower())
        )
        self.db.commit()
        if cur.rowcount:
            return f"✅ 已取消追踪 {platform} @{username}"
        return f"⚠️ 未找到 {platform} @{username}"

    def list_tracked(self) -> str:
        rows = self.db.execute(
            "SELECT platform, username, added_at, notes FROM tracked_accounts ORDER BY platform, username"
        ).fetchall()
        if not rows:
            return "📋 暂无追踪账号\n\n使用 /track <ig|tw|tt> <用户名> 添加"
        lines = [f"📋 追踪列表 ({len(rows)}个)\n"]
        platform_emoji = {"ig": "📸", "tw": "🐦", "tt": "🎵"}
        for r in rows:
            emoji = platform_emoji.get(r["platform"], "📊")
            note = f" — {r['notes']}" if r["notes"] else ""
            lines.append(f"  {emoji} {r['platform']} @{r['username']}{note}")
        return "\n".join(lines)

    def save_snapshot(self, platform: str, username: str,
                      followers: int = 0, posts: int = 0,
                      engagement_rate: float = 0, extra: Optional[dict] = None):
        self.db.execute(
            "INSERT INTO snapshots (platform, username, followers, posts, "
            "engagement_rate, extra_json, captured_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (platform, username, followers, posts, engagement_rate,
             json.dumps(extra or {}), datetime.now().isoformat())
        )
        self.db.commit()

    def get_growth(self, platform: str, username: str, days: int = 7) -> str:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self.db.execute(
            "SELECT followers, posts, captured_at FROM snapshots "
            "WHERE platform=? AND username=? AND captured_at>=? ORDER BY captured_at",
            (platform, username, since)
        ).fetchall()
        if len(rows) < 2:
            return f"📊 @{username} 数据不足 (需要至少2次快照)"
        first, last = rows[0], rows[-1]
        f_diff = last["followers"] - first["followers"]
        p_diff = last["posts"] - first["posts"]
        sign = "+" if f_diff >= 0 else ""
        return (
            f"📊 @{username} {days}天增长\n\n"
            f"👥 粉丝: {last['followers']:,} ({sign}{f_diff:,})\n"
            f"📝 帖子: {last['posts']:,} (+{p_diff})\n"
            f"📅 数据点: {len(rows)}个"
        )

    def close(self):
        self.db.close()
