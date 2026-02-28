"""Content scheduler with SQLite persistence."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Schedule and manage social media posts."""

    def __init__(self, db_path: str = "data/scheduler.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                content_type TEXT DEFAULT 'image',
                caption TEXT DEFAULT '',
                media_url TEXT DEFAULT '',
                scheduled_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                published_at TEXT,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_scheduled_status
                ON scheduled_posts(status, scheduled_at);
        """)
        self.db.commit()

    def add_post(self, platform: str, caption: str, media_url: str,
                 scheduled_at: str, content_type: str = "image") -> str:
        try:
            # Validate datetime
            dt = datetime.fromisoformat(scheduled_at)
            self.db.execute(
                "INSERT INTO scheduled_posts "
                "(platform, content_type, caption, media_url, scheduled_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (platform, content_type, caption, media_url,
                 dt.isoformat(), datetime.now().isoformat())
            )
            self.db.commit()
            return f"✅ 已排期: {platform} {dt.strftime('%m/%d %H:%M')}\n📝 {caption[:50]}"
        except ValueError:
            return "❌ 时间格式错误，请使用 YYYY-MM-DDTHH:MM"
        except Exception as e:
            return f"❌ 排期失败: {e}"

    def list_pending(self) -> str:
        rows = self.db.execute(
            "SELECT id, platform, caption, scheduled_at FROM scheduled_posts "
            "WHERE status='pending' ORDER BY scheduled_at LIMIT 20"
        ).fetchall()
        if not rows:
            return "📅 暂无排期内容\n\n使用 /schedule <平台> <时间> <文案> 添加"
        lines = [f"📅 待发布 ({len(rows)}条)\n"]
        for r in rows:
            dt = datetime.fromisoformat(r["scheduled_at"])
            lines.append(
                f"  #{r['id']} {r['platform']} "
                f"{dt.strftime('%m/%d %H:%M')} | "
                f"{r['caption'][:30]}"
            )
        return "\n".join(lines)

    def get_due_posts(self) -> list[dict]:
        """Get posts that are due for publishing."""
        now = datetime.now().isoformat()
        rows = self.db.execute(
            "SELECT * FROM scheduled_posts WHERE status='pending' AND scheduled_at<=?",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_published(self, post_id: int):
        self.db.execute(
            "UPDATE scheduled_posts SET status='published', published_at=? WHERE id=?",
            (datetime.now().isoformat(), post_id)
        )
        self.db.commit()

    def mark_failed(self, post_id: int, error: str):
        self.db.execute(
            "UPDATE scheduled_posts SET status='failed', error=? WHERE id=?",
            (error[:500], post_id)
        )
        self.db.commit()

    def cancel_post(self, post_id: int) -> str:
        cur = self.db.execute(
            "UPDATE scheduled_posts SET status='cancelled' "
            "WHERE id=? AND status='pending'",
            (post_id,)
        )
        self.db.commit()
        if cur.rowcount:
            return f"✅ 已取消排期 #{post_id}"
        return f"⚠️ 未找到待发布的排期 #{post_id}"

    def get_stats(self) -> str:
        rows = self.db.execute(
            "SELECT status, COUNT(*) as cnt FROM scheduled_posts GROUP BY status"
        ).fetchall()
        stats = {r["status"]: r["cnt"] for r in rows}
        return (
            f"📊 排期统计\n\n"
            f"⏳ 待发布: {stats.get('pending', 0)}\n"
            f"✅ 已发布: {stats.get('published', 0)}\n"
            f"❌ 失败: {stats.get('failed', 0)}\n"
            f"🚫 已取消: {stats.get('cancelled', 0)}"
        )

    def close(self):
        self.db.close()
