"""Twitter/X API v2 client."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TwitterClient:
    """Twitter API v2 client with Bearer token auth."""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {bearer_token}"

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        try:
            r = self.session.get(
                f"{self.BASE_URL}/{endpoint}", params=params, timeout=15
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("Twitter API error: %s", e)
            return None

    def search_recent(self, query: str, max_results: int = 10) -> str:
        data = self._get("tweets/search/recent", {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "public_metrics,created_at,author_id",
        })
        if not data:
            return "❌ 搜索失败"
        tweets = data.get("data", [])
        if not tweets:
            return f"🔍 未找到关于 '{query}' 的推文"
        lines = [f"🐦 搜索: {query} ({len(tweets)}条)\n"]
        for t in tweets[:10]:
            m = t.get("public_metrics", {})
            lines.append(
                f"❤️{m.get('like_count', 0)} "
                f"🔄{m.get('retweet_count', 0)} "
                f"💬{m.get('reply_count', 0)} | "
                f"{t['text'][:60]}"
            )
        return "\n".join(lines)

    def get_user(self, username: str) -> str:
        data = self._get(f"users/by/username/{username}", {
            "user.fields": "public_metrics,description,created_at,verified",
        })
        if not data or "data" not in data:
            return f"❌ 未找到用户 @{username}"
        d = data["data"]
        m = d.get("public_metrics", {})
        verified = "✅" if d.get("verified") else ""
        return (
            f"🐦 @{d.get('username')} {verified}\n"
            f"👥 粉丝: {m.get('followers_count', 0):,}\n"
            f"👤 关注: {m.get('following_count', 0):,}\n"
            f"📝 推文: {m.get('tweet_count', 0):,}\n"
            f"📋 {d.get('description', '')[:100]}"
        )

    def get_user_tweets(self, username: str, max_results: int = 5) -> str:
        """Get recent tweets from a user."""
        user_data = self._get(f"users/by/username/{username}")
        if not user_data or "data" not in user_data:
            return f"❌ 未找到用户 @{username}"

        user_id = user_data["data"]["id"]
        data = self._get(f"users/{user_id}/tweets", {
            "max_results": min(max_results, 100),
            "tweet.fields": "public_metrics,created_at",
        })
        if not data:
            return "❌ 获取推文失败"
        tweets = data.get("data", [])
        if not tweets:
            return f"📝 @{username} 暂无推文"
        lines = [f"📝 @{username} 最近推文\n"]
        for t in tweets:
            m = t.get("public_metrics", {})
            lines.append(
                f"❤️{m.get('like_count', 0)} "
                f"🔄{m.get('retweet_count', 0)} | "
                f"{t['text'][:60]}"
            )
        return "\n".join(lines)

    def get_trending(self, woeid: int = 1) -> str:
        """Get trending topics (v1.1 endpoint, requires elevated access)."""
        try:
            r = self.session.get(
                f"https://api.twitter.com/1.1/trends/place.json",
                params={"id": woeid}, timeout=15
            )
            if not r.ok:
                return "❌ 趋势获取失败 (需要Elevated权限)"
            trends = r.json()[0].get("trends", [])[:10]
            lines = ["🔥 Twitter热门趋势\n"]
            for i, t in enumerate(trends, 1):
                vol = t.get("tweet_volume")
                vol_str = f" ({vol:,})" if vol else ""
                lines.append(f"{i}. {t['name']}{vol_str}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("Trending error: %s", e)
            return "❌ 趋势获取失败"
