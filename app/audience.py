"""Audience Segmentation & Targeting Engine.

Analyze follower demographics, behavior, and engagement patterns
to create actionable audience segments for targeted content.

Features:
- Follower behavior clustering (active hours, content preferences)
- Engagement-based segmentation (superfans, casual, dormant)
- Demographic profiling (geo, language, device)
- Lookalike audience generation
- Segment-specific content recommendations
- Growth opportunity detection
- SQLite persistence for segment tracking
"""

import json
import math
import sqlite3
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SegmentType(str, Enum):
    ENGAGEMENT = "engagement"       # By engagement level
    BEHAVIOR = "behavior"           # By behavior pattern
    DEMOGRAPHIC = "demographic"     # By demographics
    INTEREST = "interest"           # By content interest
    LIFECYCLE = "lifecycle"         # By follower lifecycle stage
    CUSTOM = "custom"              # User-defined


class EngagementTier(str, Enum):
    SUPERFAN = "superfan"           # Top 5% — likes, comments, shares everything
    ACTIVE = "active"               # Regular engagement (top 20%)
    CASUAL = "casual"               # Occasional interaction (middle 50%)
    PASSIVE = "passive"             # Mostly lurks (bottom 25%)
    DORMANT = "dormant"             # No interaction in 30+ days
    CHURNED = "churned"             # Unfollowed or inactive 90+ days


class LifecycleStage(str, Enum):
    NEW_FOLLOWER = "new_follower"       # < 7 days
    ONBOARDING = "onboarding"           # 7-30 days
    ESTABLISHED = "established"         # 30-180 days
    LOYAL = "loyal"                     # 180+ days
    AT_RISK = "at_risk"                 # Declining engagement
    REACTIVATED = "reactivated"         # Returned after dormancy


TIER_THRESHOLDS = {
    EngagementTier.SUPERFAN: 0.95,    # Top 5%
    EngagementTier.ACTIVE: 0.80,      # 80-95th percentile
    EngagementTier.CASUAL: 0.30,      # 30-80th percentile
    EngagementTier.PASSIVE: 0.05,     # 5-30th percentile
    EngagementTier.DORMANT: 0.0,      # Below 5th or inactive 30 days
}


@dataclass
class FollowerProfile:
    """Profile of a single follower."""
    user_id: str
    username: str = ""
    platform: str = ""
    followed_at: str = ""
    last_active: str = ""
    total_interactions: int = 0
    likes_given: int = 0
    comments_given: int = 0
    shares_given: int = 0
    saves_given: int = 0
    active_hours: list[int] = field(default_factory=list)
    preferred_content: list[str] = field(default_factory=list)
    language: str = ""
    country: str = ""
    device: str = ""  # mobile/desktop

    @property
    def engagement_score(self) -> float:
        """Calculate normalized engagement score (0-100)."""
        # Weighted: comments > shares > saves > likes
        score = (
            self.likes_given * 1.0 +
            self.comments_given * 3.0 +
            self.shares_given * 5.0 +
            self.saves_given * 2.0
        )
        return min(100.0, score)

    @property
    def days_since_active(self) -> int:
        if not self.last_active:
            return 999
        try:
            last = datetime.fromisoformat(self.last_active.replace("Z", "+00:00"))
            return (datetime.now() - last.replace(tzinfo=None)).days
        except (ValueError, AttributeError):
            return 999


@dataclass
class AudienceSegment:
    """A segment of the audience."""
    id: str
    name: str
    segment_type: SegmentType
    description: str = ""
    size: int = 0
    percentage: float = 0.0  # % of total audience
    avg_engagement_rate: float = 0.0
    characteristics: dict = field(default_factory=dict)
    content_recommendations: list[str] = field(default_factory=list)
    top_active_hours: list[int] = field(default_factory=list)
    growth_trend: str = "stable"  # growing / stable / declining

    def summary(self) -> str:
        lines = [
            f"👥 {self.name} ({self.size:,} | {self.percentage:.1f}%)",
            f"   📊 平均互动率: {self.avg_engagement_rate:.2f}%",
            f"   📈 趋势: {self.growth_trend}",
        ]
        if self.top_active_hours:
            hours = ", ".join(f"{h}:00" for h in self.top_active_hours[:3])
            lines.append(f"   ⏰ 活跃时段: {hours}")
        if self.content_recommendations:
            lines.append(f"   💡 推荐: {self.content_recommendations[0]}")
        return "\n".join(lines)


@dataclass
class AudienceInsights:
    """Comprehensive audience analysis."""
    platform: str
    total_followers: int
    segments: list[AudienceSegment]
    engagement_distribution: dict[str, int]  # tier → count
    top_active_hours: list[tuple[int, float]]  # (hour, engagement_rate)
    top_countries: list[tuple[str, int]]
    top_languages: list[tuple[str, int]]
    content_preferences: list[tuple[str, float]]
    growth_opportunities: list[str]

    def summary(self) -> str:
        lines = [
            f"📊 受众洞察 — {self.platform.upper()}",
            f"👥 总粉丝: {self.total_followers:,}",
            "",
            "📈 互动分层:",
        ]

        tier_emoji = {
            "superfan": "🌟", "active": "🔥", "casual": "👤",
            "passive": "😶", "dormant": "💤", "churned": "💀",
        }
        for tier, count in self.engagement_distribution.items():
            pct = (count / max(self.total_followers, 1)) * 100
            emoji = tier_emoji.get(tier, "▪️")
            lines.append(f"  {emoji} {tier}: {count:,} ({pct:.1f}%)")

        if self.segments:
            lines.append("")
            lines.append("🎯 关键细分:")
            for seg in self.segments[:5]:
                lines.append(seg.summary())

        if self.top_active_hours:
            lines.append("")
            hours = ", ".join(
                f"{h}:00 ({r:.1f}%)"
                for h, r in self.top_active_hours[:5]
            )
            lines.append(f"⏰ 最佳发帖时间: {hours}")

        if self.top_countries:
            lines.append("")
            countries = ", ".join(f"{c} ({n:,})" for c, n in self.top_countries[:5])
            lines.append(f"🌍 主要地区: {countries}")

        if self.growth_opportunities:
            lines.append("")
            lines.append("🚀 增长机会:")
            for opp in self.growth_opportunities[:5]:
                lines.append(f"  • {opp}")

        return "\n".join(lines)


class AudienceEngine:
    """Audience analysis engine with SQLite persistence."""

    def __init__(self, db_path: str = "data/audience.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS followers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT DEFAULT '',
                platform TEXT NOT NULL,
                followed_at TEXT DEFAULT '',
                last_active TEXT DEFAULT '',
                total_interactions INTEGER DEFAULT 0,
                likes_given INTEGER DEFAULT 0,
                comments_given INTEGER DEFAULT 0,
                shares_given INTEGER DEFAULT 0,
                saves_given INTEGER DEFAULT 0,
                active_hours_json TEXT DEFAULT '[]',
                preferred_content_json TEXT DEFAULT '[]',
                language TEXT DEFAULT '',
                country TEXT DEFAULT '',
                device TEXT DEFAULT '',
                engagement_tier TEXT DEFAULT 'casual',
                lifecycle_stage TEXT DEFAULT 'new_follower',
                updated_at TEXT NOT NULL,
                UNIQUE(platform, user_id)
            );

            CREATE TABLE IF NOT EXISTS segments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                segment_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                criteria_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS segment_members (
                segment_id TEXT NOT NULL,
                follower_id TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (segment_id, follower_id),
                FOREIGN KEY (segment_id) REFERENCES segments(id),
                FOREIGN KEY (follower_id) REFERENCES followers(id)
            );

            CREATE TABLE IF NOT EXISTS audience_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                total_followers INTEGER NOT NULL,
                segment_counts_json TEXT DEFAULT '{}',
                insights_json TEXT DEFAULT '{}',
                captured_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_followers_platform
                ON followers(platform);
            CREATE INDEX IF NOT EXISTS idx_followers_tier
                ON followers(engagement_tier);
        """)
        self.db.commit()

    def add_follower(self, profile: FollowerProfile) -> str:
        """Add or update a follower profile."""
        tier = self._classify_tier(profile)
        stage = self._classify_lifecycle(profile)

        self.db.execute(
            "INSERT OR REPLACE INTO followers "
            "(id, user_id, username, platform, followed_at, last_active, "
            "total_interactions, likes_given, comments_given, shares_given, saves_given, "
            "active_hours_json, preferred_content_json, language, country, device, "
            "engagement_tier, lifecycle_stage, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"{profile.platform}_{profile.user_id}",
                profile.user_id, profile.username, profile.platform,
                profile.followed_at, profile.last_active,
                profile.total_interactions, profile.likes_given,
                profile.comments_given, profile.shares_given, profile.saves_given,
                json.dumps(profile.active_hours),
                json.dumps(profile.preferred_content),
                profile.language, profile.country, profile.device,
                tier.value, stage.value,
                datetime.now().isoformat(),
            )
        )
        self.db.commit()
        return f"✅ {profile.platform} @{profile.username} → {tier.value}"

    def bulk_add_followers(self, profiles: list[FollowerProfile]) -> str:
        """Batch add/update followers."""
        added = 0
        for p in profiles:
            self.add_follower(p)
            added += 1
        return f"✅ 批量导入 {added} 粉丝"

    def _classify_tier(self, profile: FollowerProfile) -> EngagementTier:
        """Classify follower into engagement tier."""
        score = profile.engagement_score

        if profile.days_since_active > 90:
            return EngagementTier.CHURNED
        if profile.days_since_active > 30:
            return EngagementTier.DORMANT

        if score >= 50:
            return EngagementTier.SUPERFAN
        if score >= 20:
            return EngagementTier.ACTIVE
        if score >= 5:
            return EngagementTier.CASUAL
        return EngagementTier.PASSIVE

    def _classify_lifecycle(self, profile: FollowerProfile) -> LifecycleStage:
        """Classify follower lifecycle stage."""
        if not profile.followed_at:
            return LifecycleStage.ESTABLISHED

        try:
            followed = datetime.fromisoformat(
                profile.followed_at.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            days = (datetime.now() - followed).days
        except (ValueError, AttributeError):
            return LifecycleStage.ESTABLISHED

        if days < 7:
            return LifecycleStage.NEW_FOLLOWER
        if days < 30:
            return LifecycleStage.ONBOARDING
        if days < 180:
            return LifecycleStage.ESTABLISHED

        # Check if at risk (loyal but declining)
        if profile.days_since_active > 14:
            return LifecycleStage.AT_RISK

        return LifecycleStage.LOYAL

    def get_insights(self, platform: str) -> AudienceInsights:
        """Generate comprehensive audience insights."""
        followers = self.db.execute(
            "SELECT * FROM followers WHERE platform=?", (platform,)
        ).fetchall()

        total = len(followers)
        if total == 0:
            return AudienceInsights(
                platform=platform,
                total_followers=0,
                segments=[],
                engagement_distribution={},
                top_active_hours=[],
                top_countries=[],
                top_languages=[],
                content_preferences=[],
                growth_opportunities=["开始导入粉丝数据以获取洞察"],
            )

        # Engagement distribution
        tier_counts: dict[str, int] = Counter()
        hourly_engagement: dict[int, list[float]] = defaultdict(list)
        country_counts: Counter = Counter()
        language_counts: Counter = Counter()
        content_scores: dict[str, list[float]] = defaultdict(list)

        for f in followers:
            tier_counts[f["engagement_tier"]] += 1

            if f["country"]:
                country_counts[f["country"]] += 1
            if f["language"]:
                language_counts[f["language"]] += 1

            try:
                hours = json.loads(f["active_hours_json"] or "[]")
                score = f["total_interactions"] or 0
                for h in hours:
                    hourly_engagement[h].append(float(score))
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                prefs = json.loads(f["preferred_content_json"] or "[]")
                score = f["total_interactions"] or 0
                for ct in prefs:
                    content_scores[ct].append(float(score))
            except (json.JSONDecodeError, TypeError):
                pass

        # Top active hours by average engagement
        top_hours = sorted(
            [
                (h, sum(scores) / len(scores))
                for h, scores in hourly_engagement.items()
                if scores
            ],
            key=lambda x: -x[1],
        )

        # Content preferences
        content_prefs = sorted(
            [
                (ct, sum(scores) / len(scores))
                for ct, scores in content_scores.items()
                if scores
            ],
            key=lambda x: -x[1],
        )

        # Build segments
        segments = self._build_segments(followers, platform)

        # Growth opportunities
        opportunities = self._detect_opportunities(
            tier_counts, total, top_hours, country_counts
        )

        # Save snapshot
        self._save_snapshot(platform, total, tier_counts)

        return AudienceInsights(
            platform=platform,
            total_followers=total,
            segments=segments,
            engagement_distribution=dict(tier_counts),
            top_active_hours=top_hours[:10],
            top_countries=country_counts.most_common(10),
            top_languages=language_counts.most_common(10),
            content_preferences=content_prefs[:10],
            growth_opportunities=opportunities,
        )

    def _build_segments(self, followers: list, platform: str) -> list[AudienceSegment]:
        """Build audience segments from follower data."""
        total = len(followers)
        segments = []

        # Segment by engagement tier
        tier_groups: dict[str, list] = defaultdict(list)
        for f in followers:
            tier_groups[f["engagement_tier"]].append(f)

        tier_descriptions = {
            "superfan": "核心粉丝 — 几乎每条内容都互动",
            "active": "活跃粉丝 — 定期互动",
            "casual": "普通粉丝 — 偶尔互动",
            "passive": "潜水粉丝 — 很少互动",
            "dormant": "沉睡粉丝 — 30+天未互动",
            "churned": "流失粉丝 — 90+天未互动",
        }

        tier_recommendations = {
            "superfan": ["给VIP专属内容", "邀请UGC共创", "作为品牌大使培养"],
            "active": ["保持互动频率", "引导分享裂变", "推送高价值内容"],
            "casual": ["增加互动型内容(投票/问答)", "优化发帖时间触达", "用Story保持可见度"],
            "passive": ["用hook型标题吸引注意", "尝试不同内容格式", "考虑付费推广触达"],
            "dormant": ["发送唤醒内容", "推出限时活动", "检查内容质量是否下滑"],
            "churned": ["分析流失原因", "考虑再营销广告", "清理无效粉丝提升互动率"],
        }

        for tier, group in tier_groups.items():
            if not group:
                continue

            avg_interactions = (
                sum(f["total_interactions"] or 0 for f in group) / len(group)
            )

            hours: list[int] = []
            for f in group:
                try:
                    h = json.loads(f["active_hours_json"] or "[]")
                    hours.extend(h)
                except (json.JSONDecodeError, TypeError):
                    pass

            top_hours = [h for h, _ in Counter(hours).most_common(3)]

            import hashlib
            seg_id = hashlib.md5(f"{platform}_{tier}".encode()).hexdigest()[:10]

            segments.append(AudienceSegment(
                id=seg_id,
                name=tier.replace("_", " ").title(),
                segment_type=SegmentType.ENGAGEMENT,
                description=tier_descriptions.get(tier, ""),
                size=len(group),
                percentage=(len(group) / total) * 100,
                avg_engagement_rate=avg_interactions,
                content_recommendations=tier_recommendations.get(tier, []),
                top_active_hours=top_hours,
            ))

        segments.sort(key=lambda s: -s.avg_engagement_rate)
        return segments

    def _detect_opportunities(
        self,
        tier_counts: Counter,
        total: int,
        top_hours: list[tuple[int, float]],
        country_counts: Counter,
    ) -> list[str]:
        """Detect growth opportunities from audience data."""
        opportunities = []

        if total == 0:
            return ["导入粉丝数据开始分析"]

        # Check engagement health
        dormant = tier_counts.get("dormant", 0) + tier_counts.get("churned", 0)
        dormant_pct = (dormant / total) * 100
        if dormant_pct > 40:
            opportunities.append(
                f"⚠️ {dormant_pct:.0f}%粉丝沉睡/流失 — 急需唤醒策略"
            )
        elif dormant_pct > 20:
            opportunities.append(
                f"📉 {dormant_pct:.0f}%粉丝沉睡 — 建议推出互动活动"
            )

        # Superfan leverage
        superfan = tier_counts.get("superfan", 0)
        if superfan > 0:
            opportunities.append(
                f"🌟 {superfan}个超级粉丝 — 可发展为品牌大使/UGC来源"
            )

        # Passive conversion
        passive = tier_counts.get("passive", 0)
        if passive > total * 0.3:
            opportunities.append(
                f"👤 {passive}个被动粉丝 — 优化内容hook可转化为活跃粉"
            )

        # Geographic focus
        if country_counts:
            top_country, top_count = country_counts.most_common(1)[0]
            pct = (top_count / total) * 100
            if pct > 50:
                opportunities.append(
                    f"🌍 {pct:.0f}%粉丝来自{top_country} — 可做本地化内容深耕"
                )

        # Posting time optimization
        if top_hours:
            best_hour = top_hours[0][0]
            opportunities.append(
                f"⏰ 最佳发帖时间: {best_hour}:00 — 确保此时段有内容"
            )

        return opportunities

    def _save_snapshot(self, platform: str, total: int, tier_counts: Counter):
        """Save audience snapshot for trend tracking."""
        self.db.execute(
            "INSERT INTO audience_snapshots "
            "(platform, total_followers, segment_counts_json, captured_at) "
            "VALUES (?, ?, ?, ?)",
            (platform, total, json.dumps(dict(tier_counts)),
             datetime.now().isoformat())
        )
        self.db.commit()

    def get_growth_trend(self, platform: str, days: int = 30) -> str:
        """Get audience growth trend over time."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self.db.execute(
            "SELECT total_followers, segment_counts_json, captured_at "
            "FROM audience_snapshots "
            "WHERE platform=? AND captured_at>=? ORDER BY captured_at",
            (platform, since)
        ).fetchall()

        if len(rows) < 2:
            return f"📈 数据不足 — 需要至少2次快照 (当前: {len(rows)})"

        first = rows[0]
        last = rows[-1]
        growth = last["total_followers"] - first["total_followers"]
        sign = "+" if growth >= 0 else ""

        lines = [
            f"📈 {platform.upper()} {days}天增长趋势",
            f"👥 粉丝: {last['total_followers']:,} ({sign}{growth:,})",
            f"📅 数据点: {len(rows)}个",
        ]

        # Segment trend
        try:
            first_segs = json.loads(first["segment_counts_json"])
            last_segs = json.loads(last["segment_counts_json"])

            for tier in ["superfan", "active", "dormant"]:
                f_cnt = first_segs.get(tier, 0)
                l_cnt = last_segs.get(tier, 0)
                diff = l_cnt - f_cnt
                if diff != 0:
                    sign = "+" if diff > 0 else ""
                    lines.append(f"  {tier}: {l_cnt} ({sign}{diff})")
        except (json.JSONDecodeError, TypeError):
            pass

        return "\n".join(lines)

    def find_lookalikes(
        self, target_segment: str, platform: str, limit: int = 50
    ) -> list[dict]:
        """Find followers similar to a target segment.

        Useful for expanding successful segments.
        """
        # Get target segment characteristics
        target_followers = self.db.execute(
            "SELECT * FROM followers "
            "WHERE platform=? AND engagement_tier=?",
            (platform, target_segment)
        ).fetchall()

        if not target_followers:
            return []

        # Calculate average profile of target segment
        avg_interactions = sum(f["total_interactions"] or 0 for f in target_followers) / len(target_followers)

        # Find non-target followers with similar characteristics
        candidates = self.db.execute(
            "SELECT * FROM followers "
            "WHERE platform=? AND engagement_tier!=? "
            "ORDER BY ABS(total_interactions - ?) LIMIT ?",
            (platform, target_segment, avg_interactions, limit)
        ).fetchall()

        return [dict(c) for c in candidates]

    def get_segment_content_recs(self, platform: str, tier: str) -> str:
        """Get content recommendations for a specific segment."""
        count = self.db.execute(
            "SELECT COUNT(*) as cnt FROM followers "
            "WHERE platform=? AND engagement_tier=?",
            (platform, tier)
        ).fetchone()

        n = count["cnt"] if count else 0

        recs_map = {
            "superfan": (
                f"🌟 超级粉丝策略 ({n}人)\n\n"
                "1. 📌 专属内容 — 提前预览、幕后花絮\n"
                "2. 🎤 UGC共创 — 邀请参与内容创作\n"
                "3. 🏆 认可奖励 — 点名感谢、专属称号\n"
                "4. 💬 深度互动 — 回复每条评论\n"
                "5. 🎁 专属福利 — 限量商品、提前购"
            ),
            "active": (
                f"🔥 活跃粉丝策略 ({n}人)\n\n"
                "1. 📊 投票互动 — Story投票、问答\n"
                "2. 🔄 分享激励 — 分享有奖\n"
                "3. 📚 系列内容 — 连载型内容保持粘性\n"
                "4. 🤝 社群感 — 打造归属感\n"
                "5. 📈 进阶引导 — 向superfan转化"
            ),
            "casual": (
                f"👤 普通粉丝策略 ({n}人)\n\n"
                "1. 🎣 强Hook — 前3秒/前2行抓住注意力\n"
                "2. 📱 短内容 — 易消化的快速内容\n"
                "3. ❓ 提问式 — 降低互动门槛\n"
                "4. 🎵 趋势跟风 — 追热点、用热门BGM\n"
                "5. ⏰ 精准时间 — 在其活跃时段发布"
            ),
            "passive": (
                f"😶 潜水粉丝策略 ({n}人)\n\n"
                "1. 💥 争议观点 — 引发讨论欲望\n"
                "2. 🎬 视频优先 — 视频比图文更易触达\n"
                "3. 🏷️ 标签互动 — @提及唤醒\n"
                "4. 🎯 精准推送 — 根据兴趣定向\n"
                "5. 📣 付费触达 — 适当广告投放"
            ),
            "dormant": (
                f"💤 沉睡粉丝策略 ({n}人)\n\n"
                "1. 🔔 唤醒活动 — '好久不见'专题\n"
                "2. 🎁 限时福利 — 优惠码/抽奖激活\n"
                "3. 📊 调研问卷 — 了解沉睡原因\n"
                "4. ✂️ 清理考虑 — 严重影响互动率时清理\n"
                "5. 🔄 内容转型 — 可能是内容不再匹配"
            ),
        }

        return recs_map.get(tier, f"❓ 未知分层: {tier}")

    def close(self):
        self.db.close()
