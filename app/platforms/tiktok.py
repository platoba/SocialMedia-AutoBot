"""TikTok API client for business accounts."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TikTokClient:
    """TikTok Content Posting API + Research API client."""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self, access_token: str, open_id: str = ""):
        self.access_token = access_token
        self.open_id = open_id
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {access_token}"
        self.session.headers["Content-Type"] = "application/json"

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        try:
            r = self.session.get(
                f"{self.BASE_URL}/{endpoint}", params=params, timeout=15
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("TikTok API error: %s", e)
            return None

    def _post(self, endpoint: str, json_data: Optional[dict] = None) -> Optional[dict]:
        try:
            r = self.session.post(
                f"{self.BASE_URL}/{endpoint}", json=json_data, timeout=30
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("TikTok API error: %s", e)
            return None

    def get_user_info(self) -> str:
        """Get authenticated user's profile info."""
        data = self._get("user/info/", {
            "fields": "open_id,display_name,avatar_url,follower_count,"
                      "following_count,likes_count,video_count",
        })
        if not data or "data" not in data:
            return "❌ 无法获取TikTok资料"
        user = data["data"].get("user", {})
        return (
            f"🎵 {user.get('display_name', 'Unknown')}\n"
            f"👥 粉丝: {user.get('follower_count', 0):,}\n"
            f"👤 关注: {user.get('following_count', 0):,}\n"
            f"❤️ 获赞: {user.get('likes_count', 0):,}\n"
            f"🎬 视频: {user.get('video_count', 0)}"
        )

    def get_videos(self, max_count: int = 5) -> str:
        """Get user's recent videos."""
        data = self._post("video/list/", {
            "max_count": min(max_count, 20),
            "fields": "id,title,like_count,comment_count,share_count,"
                      "view_count,create_time,duration",
        })
        if not data or "data" not in data:
            return "❌ 无法获取视频列表"
        videos = data["data"].get("videos", [])
        if not videos:
            return "🎬 暂无视频"
        lines = [f"🎬 最近{len(videos)}个视频\n"]
        for v in videos:
            title = (v.get("title") or "无标题")[:40]
            lines.append(
                f"👁️{v.get('view_count', 0):,} "
                f"❤️{v.get('like_count', 0):,} "
                f"💬{v.get('comment_count', 0)} | {title}"
            )
        return "\n".join(lines)

    def search_videos(self, query: str, max_count: int = 10) -> str:
        """Search public videos via Research API."""
        data = self._post("research/video/query/", {
            "query": {"and": [{"operation": "IN", "field_name": "keyword",
                               "field_values": [query]}]},
            "max_count": min(max_count, 100),
            "fields": "id,like_count,comment_count,share_count,view_count,"
                      "voice_to_text,video_description",
        })
        if not data or "data" not in data:
            return "❌ 搜索失败 (需要Research API权限)"
        videos = data["data"].get("videos", [])
        if not videos:
            return f"🔍 未找到关于 '{query}' 的视频"
        lines = [f"🎵 TikTok搜索: {query} ({len(videos)}条)\n"]
        for v in videos[:10]:
            desc = (v.get("video_description") or "")[:40]
            lines.append(
                f"👁️{v.get('view_count', 0):,} "
                f"❤️{v.get('like_count', 0):,} | {desc}"
            )
        return "\n".join(lines)

    def init_video_upload(self, video_size: int, chunk_size: int = 10_000_000,
                          title: str = "", privacy: str = "SELF_ONLY") -> Optional[str]:
        """Initialize video upload and return publish_id."""
        data = self._post("post/publish/video/init/", {
            "post_info": {
                "title": title[:150],
                "privacy_level": privacy,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": -(-video_size // chunk_size),
            },
        })
        if data and "data" in data:
            return data["data"].get("publish_id")
        return None
