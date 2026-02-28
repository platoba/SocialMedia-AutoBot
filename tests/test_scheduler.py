"""Tests for app.scheduler module."""

import os
import tempfile
from datetime import datetime, timedelta
import pytest
from app.scheduler import Scheduler


@pytest.fixture
def scheduler():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    s = Scheduler(db_path=db_path)
    yield s
    s.close()
    os.unlink(db_path)


class TestAddPost:
    def test_add_valid_post(self, scheduler):
        dt = (datetime.now() + timedelta(hours=1)).isoformat()
        result = scheduler.add_post("ig", "Test caption", "https://img.com/1.jpg", dt)
        assert "已排期" in result

    def test_add_invalid_datetime(self, scheduler):
        result = scheduler.add_post("ig", "Test", "url", "not-a-date")
        assert "格式错误" in result

    def test_add_with_content_type(self, scheduler):
        dt = (datetime.now() + timedelta(hours=1)).isoformat()
        result = scheduler.add_post("tt", "Video", "url", dt, content_type="video")
        assert "已排期" in result


class TestListPending:
    def test_empty_queue(self, scheduler):
        result = scheduler.list_pending()
        assert "暂无排期" in result

    def test_list_with_posts(self, scheduler):
        dt = (datetime.now() + timedelta(hours=1)).isoformat()
        scheduler.add_post("ig", "Post 1", "url1", dt)
        scheduler.add_post("tw", "Post 2", "url2", dt)
        result = scheduler.list_pending()
        assert "2条" in result
        assert "Post 1" in result
        assert "Post 2" in result


class TestDuePosts:
    def test_no_due_posts(self, scheduler):
        dt = (datetime.now() + timedelta(hours=1)).isoformat()
        scheduler.add_post("ig", "Future", "url", dt)
        due = scheduler.get_due_posts()
        assert len(due) == 0

    def test_due_posts(self, scheduler):
        dt = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "Past", "url", dt)
        due = scheduler.get_due_posts()
        assert len(due) == 1
        assert due[0]["caption"] == "Past"


class TestMarkPublished:
    def test_mark_published(self, scheduler):
        dt = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "Test", "url", dt)
        due = scheduler.get_due_posts()
        scheduler.mark_published(due[0]["id"])
        remaining = scheduler.get_due_posts()
        assert len(remaining) == 0

    def test_published_has_timestamp(self, scheduler):
        dt = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "Test", "url", dt)
        due = scheduler.get_due_posts()
        scheduler.mark_published(due[0]["id"])
        row = scheduler.db.execute(
            "SELECT published_at FROM scheduled_posts WHERE id=?", (due[0]["id"],)
        ).fetchone()
        assert row["published_at"] is not None


class TestMarkFailed:
    def test_mark_failed(self, scheduler):
        dt = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "Test", "url", dt)
        due = scheduler.get_due_posts()
        scheduler.mark_failed(due[0]["id"], "API error")
        remaining = scheduler.get_due_posts()
        assert len(remaining) == 0

    def test_error_message_stored(self, scheduler):
        dt = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "Test", "url", dt)
        due = scheduler.get_due_posts()
        scheduler.mark_failed(due[0]["id"], "rate limited")
        row = scheduler.db.execute(
            "SELECT error FROM scheduled_posts WHERE id=?", (due[0]["id"],)
        ).fetchone()
        assert "rate limited" in row["error"]


class TestCancelPost:
    def test_cancel_pending(self, scheduler):
        dt = (datetime.now() + timedelta(hours=1)).isoformat()
        scheduler.add_post("ig", "Cancel me", "url", dt)
        result = scheduler.cancel_post(1)
        assert "已取消" in result

    def test_cancel_nonexistent(self, scheduler):
        result = scheduler.cancel_post(999)
        assert "未找到" in result


class TestStats:
    def test_empty_stats(self, scheduler):
        result = scheduler.get_stats()
        assert "排期统计" in result
        assert "0" in result

    def test_stats_with_data(self, scheduler):
        dt_future = (datetime.now() + timedelta(hours=1)).isoformat()
        dt_past = (datetime.now() - timedelta(minutes=5)).isoformat()
        scheduler.add_post("ig", "P1", "url", dt_future)
        scheduler.add_post("ig", "P2", "url", dt_past)
        due = scheduler.get_due_posts()
        scheduler.mark_published(due[0]["id"])
        result = scheduler.get_stats()
        assert "待发布: 1" in result
        assert "已发布: 1" in result
