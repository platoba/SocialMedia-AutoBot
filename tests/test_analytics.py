"""Tests for app.analytics module."""

import os
import tempfile
import pytest
from app.analytics import Analytics


@pytest.fixture
def analytics():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    a = Analytics(db_path=db_path)
    yield a
    a.close()
    os.unlink(db_path)


class TestTrack:
    def test_track_account(self, analytics):
        result = analytics.track("ig", "testuser")
        assert "已追踪" in result
        assert "testuser" in result

    def test_track_with_notes(self, analytics):
        result = analytics.track("tw", "user2", notes="竞品")
        assert "已追踪" in result

    def test_track_duplicate(self, analytics):
        analytics.track("ig", "testuser")
        result = analytics.track("ig", "testuser")
        assert "已追踪" in result  # INSERT OR IGNORE

    def test_track_case_insensitive(self, analytics):
        analytics.track("IG", "TestUser")
        listed = analytics.list_tracked()
        assert "ig" in listed
        assert "testuser" in listed


class TestUntrack:
    def test_untrack_existing(self, analytics):
        analytics.track("ig", "testuser")
        result = analytics.untrack("ig", "testuser")
        assert "已取消追踪" in result

    def test_untrack_nonexistent(self, analytics):
        result = analytics.untrack("ig", "nobody")
        assert "未找到" in result


class TestListTracked:
    def test_empty_list(self, analytics):
        result = analytics.list_tracked()
        assert "暂无追踪" in result

    def test_list_with_accounts(self, analytics):
        analytics.track("ig", "user1")
        analytics.track("tw", "user2")
        analytics.track("tt", "user3")
        result = analytics.list_tracked()
        assert "3个" in result
        assert "user1" in result
        assert "user2" in result
        assert "user3" in result

    def test_list_emojis(self, analytics):
        analytics.track("ig", "a")
        analytics.track("tw", "b")
        analytics.track("tt", "c")
        result = analytics.list_tracked()
        assert "📸" in result
        assert "🐦" in result
        assert "🎵" in result


class TestSnapshots:
    def test_save_snapshot(self, analytics):
        analytics.save_snapshot("ig", "testuser", followers=1000, posts=50)
        rows = analytics.db.execute(
            "SELECT * FROM snapshots WHERE username='testuser'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["followers"] == 1000

    def test_save_with_extra(self, analytics):
        analytics.save_snapshot("ig", "user", extra={"bio": "test"})
        rows = analytics.db.execute("SELECT extra_json FROM snapshots").fetchall()
        assert "bio" in rows[0]["extra_json"]


class TestGrowth:
    def test_insufficient_data(self, analytics):
        result = analytics.get_growth("ig", "testuser")
        assert "数据不足" in result

    def test_growth_with_data(self, analytics):
        analytics.save_snapshot("ig", "user1", followers=1000, posts=10)
        analytics.save_snapshot("ig", "user1", followers=1200, posts=12)
        result = analytics.get_growth("ig", "user1")
        assert "+200" in result
        assert "2个" in result

    def test_growth_custom_days(self, analytics):
        analytics.save_snapshot("ig", "user1", followers=500)
        analytics.save_snapshot("ig", "user1", followers=600)
        result = analytics.get_growth("ig", "user1", days=30)
        assert "30天增长" in result


class TestClose:
    def test_close(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        a = Analytics(db_path=db_path)
        a.close()
        os.unlink(db_path)
