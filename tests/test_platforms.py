"""Tests for app.platforms module."""

import pytest
import requests
from unittest.mock import patch, MagicMock
from app.platforms.instagram import InstagramClient
from app.platforms.twitter import TwitterClient
from app.platforms.tiktok import TikTokClient


# ===== Instagram Tests =====

class TestInstagramClient:
    @pytest.fixture
    def ig(self):
        return InstagramClient("test_token", "12345")

    def test_init(self, ig):
        assert ig.access_token == "test_token"
        assert ig.business_id == "12345"

    @patch("app.platforms.instagram.requests.Session.get")
    def test_get_profile_success(self, mock_get, ig):
        mock_get.return_value.json.return_value = {
            "username": "testaccount",
            "followers_count": 5000,
            "follows_count": 300,
            "media_count": 120,
            "biography": "Test bio"
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = ig.get_profile()
        assert "testaccount" in result
        assert "5,000" in result

    @patch("app.platforms.instagram.requests.Session.get")
    def test_get_profile_failure(self, mock_get, ig):
        mock_get.side_effect = requests.RequestException("API down")
        result = ig.get_profile()
        assert "❌" in result

    @patch("app.platforms.instagram.requests.Session.get")
    def test_get_recent_media(self, mock_get, ig):
        mock_get.return_value.json.return_value = {
            "data": [
                {"id": "1", "caption": "Test post", "like_count": 100,
                 "comments_count": 10, "media_type": "IMAGE"},
                {"id": "2", "caption": "Video", "like_count": 200,
                 "comments_count": 20, "media_type": "VIDEO"},
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = ig.get_recent_media()
        assert "Test post" in result
        assert "🖼️" in result
        assert "🎬" in result

    @patch("app.platforms.instagram.requests.Session.get")
    def test_get_recent_media_empty(self, mock_get, ig):
        mock_get.return_value.json.return_value = {"data": []}
        mock_get.return_value.raise_for_status = MagicMock()
        result = ig.get_recent_media()
        assert "暂无帖子" in result

    @patch("app.platforms.instagram.requests.Session.get")
    def test_get_stories(self, mock_get, ig):
        mock_get.return_value.json.return_value = {
            "data": [{"id": "s1"}, {"id": "s2"}]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = ig.get_stories()
        assert "2条" in result

    @patch("app.platforms.instagram.requests.Session.post")
    def test_publish_photo(self, mock_post, ig):
        mock_post.return_value.json.side_effect = [
            {"id": "container1"},  # Create container
            {"id": "post1"},  # Publish
        ]
        mock_post.return_value.raise_for_status = MagicMock()
        result = ig.publish_photo("https://img.com/1.jpg", "Test")
        assert "发布成功" in result

    @patch("app.platforms.instagram.requests.Session.post")
    def test_publish_carousel(self, mock_post, ig):
        mock_post.return_value.json.side_effect = [
            {"id": "child1"}, {"id": "child2"},  # Children
            {"id": "carousel1"},  # Container
            {"id": "published1"},  # Publish
        ]
        mock_post.return_value.raise_for_status = MagicMock()
        result = ig.publish_carousel(
            ["https://img.com/1.jpg", "https://img.com/2.jpg"], "Multi"
        )
        assert "轮播发布成功" in result

    @patch("app.platforms.instagram.requests.Session.post")
    def test_publish_carousel_too_few(self, mock_post, ig):
        result = ig.publish_carousel(["single"], "Test")
        assert "至少需要2张" in result


# ===== Twitter Tests =====

class TestTwitterClient:
    @pytest.fixture
    def tw(self):
        return TwitterClient("test_bearer")

    def test_init(self, tw):
        assert "Bearer test_bearer" in tw.session.headers["Authorization"]

    @patch("app.platforms.twitter.requests.Session.get")
    def test_search_recent(self, mock_get, tw):
        mock_get.return_value.json.return_value = {
            "data": [
                {"text": "Hello world", "public_metrics": {
                    "like_count": 10, "retweet_count": 5, "reply_count": 2
                }},
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = tw.search_recent("test")
        assert "Hello world" in result

    @patch("app.platforms.twitter.requests.Session.get")
    def test_search_empty(self, mock_get, tw):
        mock_get.return_value.json.return_value = {"data": []}
        mock_get.return_value.raise_for_status = MagicMock()
        result = tw.search_recent("noresults")
        assert "未找到" in result

    @patch("app.platforms.twitter.requests.Session.get")
    def test_get_user(self, mock_get, tw):
        mock_get.return_value.json.return_value = {
            "data": {
                "username": "elonmusk",
                "verified": True,
                "description": "Mars",
                "public_metrics": {
                    "followers_count": 100000,
                    "following_count": 200,
                    "tweet_count": 50000,
                }
            }
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = tw.get_user("elonmusk")
        assert "elonmusk" in result
        assert "✅" in result
        assert "100,000" in result

    @patch("app.platforms.twitter.requests.Session.get")
    def test_get_user_not_found(self, mock_get, tw):
        mock_get.return_value.json.return_value = {"errors": [{"message": "not found"}]}
        mock_get.return_value.raise_for_status = MagicMock()
        result = tw.get_user("nobody")
        assert "未找到" in result

    @patch("app.platforms.twitter.requests.Session.get")
    def test_get_user_tweets(self, mock_get, tw):
        mock_get.return_value.json.side_effect = [
            {"data": {"id": "123", "username": "user"}},
            {"data": [{"text": "Tweet 1", "public_metrics": {
                "like_count": 5, "retweet_count": 1
            }}]},
        ]
        mock_get.return_value.raise_for_status = MagicMock()
        result = tw.get_user_tweets("user")
        assert "Tweet 1" in result


# ===== TikTok Tests =====

class TestTikTokClient:
    @pytest.fixture
    def tt(self):
        return TikTokClient("test_token", "open123")

    def test_init(self, tt):
        assert "Bearer test_token" in tt.session.headers["Authorization"]
        assert tt.open_id == "open123"

    @patch("app.platforms.tiktok.requests.Session.get")
    def test_get_user_info(self, mock_get, tt):
        mock_get.return_value.json.return_value = {
            "data": {"user": {
                "display_name": "TestUser",
                "follower_count": 10000,
                "following_count": 50,
                "likes_count": 500000,
                "video_count": 200,
            }}
        }
        mock_get.return_value.raise_for_status = MagicMock()
        result = tt.get_user_info()
        assert "TestUser" in result
        assert "10,000" in result

    @patch("app.platforms.tiktok.requests.Session.get")
    def test_get_user_info_failure(self, mock_get, tt):
        mock_get.side_effect = requests.RequestException("API down")
        result = tt.get_user_info()
        assert "❌" in result

    @patch("app.platforms.tiktok.requests.Session.post")
    def test_get_videos(self, mock_post, tt):
        mock_post.return_value.json.return_value = {
            "data": {"videos": [
                {"title": "Dance video", "view_count": 50000,
                 "like_count": 3000, "comment_count": 100},
            ]}
        }
        mock_post.return_value.raise_for_status = MagicMock()
        result = tt.get_videos()
        assert "Dance video" in result
        assert "50,000" in result

    @patch("app.platforms.tiktok.requests.Session.post")
    def test_get_videos_empty(self, mock_post, tt):
        mock_post.return_value.json.return_value = {"data": {"videos": []}}
        mock_post.return_value.raise_for_status = MagicMock()
        result = tt.get_videos()
        assert "暂无视频" in result

    @patch("app.platforms.tiktok.requests.Session.post")
    def test_search_videos(self, mock_post, tt):
        mock_post.return_value.json.return_value = {
            "data": {"videos": [
                {"video_description": "trending", "view_count": 1000000,
                 "like_count": 50000},
            ]}
        }
        mock_post.return_value.raise_for_status = MagicMock()
        result = tt.search_videos("dance")
        assert "trending" in result

    @patch("app.platforms.tiktok.requests.Session.post")
    def test_init_video_upload(self, mock_post, tt):
        mock_post.return_value.json.return_value = {
            "data": {"publish_id": "pub123"}
        }
        mock_post.return_value.raise_for_status = MagicMock()
        result = tt.init_video_upload(50_000_000, title="Test")
        assert result == "pub123"

    @patch("app.platforms.tiktok.requests.Session.post")
    def test_init_video_upload_failure(self, mock_post, tt):
        mock_post.side_effect = requests.RequestException("upload failed")
        result = tt.init_video_upload(50_000_000)
        assert result is None
