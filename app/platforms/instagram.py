"""Instagram Graph API client."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class InstagramClient:
    """Instagram Business API via Facebook Graph API."""

    def __init__(self, access_token: str, business_id: str,
                 base_url: str = "https://graph.facebook.com/v19.0"):
        self.access_token = access_token
        self.business_id = business_id
        self.base_url = base_url
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        p = {"access_token": self.access_token}
        if params:
            p.update(params)
        try:
            r = self.session.get(f"{self.base_url}/{endpoint}", params=p, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("IG API error: %s", e)
            return None

    def _post(self, endpoint: str, data: Optional[dict] = None) -> Optional[dict]:
        d = {"access_token": self.access_token}
        if data:
            d.update(data)
        try:
            r = self.session.post(f"{self.base_url}/{endpoint}", data=d, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("IG API error: %s", e)
            return None

    def get_profile(self) -> str:
        data = self._get(self.business_id, {
            "fields": "username,followers_count,follows_count,media_count,biography"
        })
        if not data:
            return "❌ 无法获取Instagram资料"
        return (
            f"📸 @{data.get('username')}\n"
            f"👥 粉丝: {data.get('followers_count', 0):,}\n"
            f"👤 关注: {data.get('follows_count', 0):,}\n"
            f"📝 帖子: {data.get('media_count', 0)}\n"
            f"📋 简介: {data.get('biography', '')[:100]}"
        )

    def get_insights(self, period: str = "day") -> str:
        data = self._get(f"{self.business_id}/insights", {
            "metric": "impressions,reach,profile_views",
            "period": period,
        })
        if not data:
            return "❌ 无法获取Instagram数据"
        metrics = data.get("data", [])
        lines = ["📊 Instagram 今日数据\n"]
        for m in metrics:
            val = m.get("values", [{}])[-1].get("value", 0)
            lines.append(f"  {m.get('title', m.get('name'))}: {val:,}")
        return "\n".join(lines)

    def get_recent_media(self, limit: int = 5) -> str:
        data = self._get(f"{self.business_id}/media", {
            "fields": "id,caption,like_count,comments_count,timestamp,permalink,media_type",
            "limit": limit,
        })
        if not data:
            return "❌ 无法获取帖子"
        posts = data.get("data", [])
        if not posts:
            return "📸 暂无帖子"
        lines = [f"📸 最近{len(posts)}条帖子\n"]
        for p in posts:
            cap = (p.get("caption") or "")[:40]
            media_type = p.get("media_type", "IMAGE")
            emoji = {"IMAGE": "🖼️", "VIDEO": "🎬", "CAROUSEL_ALBUM": "📑"}.get(media_type, "📸")
            lines.append(
                f"{emoji} ❤️{p.get('like_count', 0)} "
                f"💬{p.get('comments_count', 0)} | {cap}"
            )
        return "\n".join(lines)

    def get_stories(self) -> str:
        data = self._get(f"{self.business_id}/stories", {
            "fields": "id,media_type,timestamp",
        })
        if not data:
            return "❌ 无法获取Stories"
        stories = data.get("data", [])
        if not stories:
            return "📱 暂无活跃Stories"
        return f"📱 当前活跃Stories: {len(stories)}条"

    def publish_photo(self, image_url: str, caption: str) -> str:
        # Step 1: Create media container
        container = self._post(f"{self.business_id}/media", {
            "image_url": image_url,
            "caption": caption,
        })
        if not container or "id" not in container:
            return "❌ 创建媒体容器失败"

        # Step 2: Publish
        result = self._post(f"{self.business_id}/media_publish", {
            "creation_id": container["id"],
        })
        if result and "id" in result:
            return f"✅ 发布成功! ID: {result['id']}"
        return "❌ 发布失败"

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        """Publish a carousel (multi-image) post."""
        if len(image_urls) < 2:
            return "❌ 轮播至少需要2张图片"

        # Create child containers
        children = []
        for url in image_urls[:10]:  # Max 10 images
            child = self._post(f"{self.business_id}/media", {
                "image_url": url,
                "is_carousel_item": True,
            })
            if child and "id" in child:
                children.append(child["id"])

        if len(children) < 2:
            return "❌ 创建轮播子项失败"

        # Create carousel container
        container = self._post(f"{self.business_id}/media", {
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(children),
        })
        if not container or "id" not in container:
            return "❌ 创建轮播容器失败"

        # Publish
        result = self._post(f"{self.business_id}/media_publish", {
            "creation_id": container["id"],
        })
        if result and "id" in result:
            return f"✅ 轮播发布成功! {len(children)}张图片, ID: {result['id']}"
        return "❌ 轮播发布失败"

    def get_hashtag_search(self, hashtag: str) -> str:
        """Search for a hashtag and get top media count."""
        data = self._get("ig_hashtag_search", {
            "q": hashtag.lstrip("#"),
            "user_id": self.business_id,
        })
        if not data:
            return f"❌ 无法搜索 #{hashtag}"
        hashtags = data.get("data", [])
        if not hashtags:
            return f"🔍 未找到 #{hashtag}"
        return f"#{hashtag} ID: {hashtags[0].get('id')}"
