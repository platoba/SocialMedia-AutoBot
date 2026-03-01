"""Engagement Intelligence Engine.

Analyze engagement patterns, optimal posting times, and audience behavior
to maximize social media reach and conversions.

Features:
- Engagement rate calculator (by platform norms)
- Optimal posting time predictor
- Audience activity heatmap
- Content performance classifier
- Viral potential scorer
- Engagement decay analysis
- Competitor benchmarking
"""
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime, timedelta


class ContentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    TEXT = "text"
    LINK = "link"
    POLL = "poll"


class PerformanceLevel(str, Enum):
    VIRAL = "viral"
    HIGH = "high"
    AVERAGE = "average"
    LOW = "low"
    UNDERPERFORMING = "underperforming"


# Platform engagement benchmarks (average engagement rates %)
PLATFORM_BENCHMARKS = {
    "instagram": {"avg_rate": 1.6, "good_rate": 3.5, "viral_rate": 10.0},
    "tiktok": {"avg_rate": 4.25, "good_rate": 8.0, "viral_rate": 20.0},
    "twitter": {"avg_rate": 0.05, "good_rate": 0.5, "viral_rate": 2.0},
    "linkedin": {"avg_rate": 2.0, "good_rate": 5.0, "viral_rate": 10.0},
    "facebook": {"avg_rate": 0.06, "good_rate": 1.0, "viral_rate": 5.0},
    "youtube": {"avg_rate": 1.7, "good_rate": 4.0, "viral_rate": 8.0},
}


@dataclass
class PostMetrics:
    """Metrics for a single post."""
    post_id: str = ""
    platform: str = "instagram"
    content_type: ContentType = ContentType.IMAGE
    posted_at: str = ""  # ISO format
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    impressions: int = 0
    reach: int = 0
    video_views: int = 0
    followers_at_time: int = 0
    hashtags: list[str] = field(default_factory=list)
    caption_length: int = 0

    @property
    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares + self.saves

    @property
    def engagement_rate(self) -> float:
        """Engagement rate as percentage of followers."""
        if self.followers_at_time <= 0:
            return 0.0
        return (self.total_engagement / self.followers_at_time) * 100

    @property
    def reach_rate(self) -> float:
        """Reach as percentage of followers."""
        if self.followers_at_time <= 0:
            return 0.0
        return (self.reach / self.followers_at_time) * 100

    @property
    def engagement_per_reach(self) -> float:
        """Engagement rate based on reach (more accurate)."""
        if self.reach <= 0:
            return 0.0
        return (self.total_engagement / self.reach) * 100


@dataclass
class EngagementReport:
    """Comprehensive engagement analysis report."""
    platform: str
    period_days: int
    total_posts: int
    avg_engagement_rate: float
    median_engagement_rate: float
    best_content_type: ContentType
    best_posting_hour: int
    best_posting_day: int  # 0=Monday, 6=Sunday
    performance_level: PerformanceLevel
    top_hashtags: list[tuple[str, float]] = field(default_factory=list)
    content_type_rates: dict = field(default_factory=dict)
    hourly_rates: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        lines = [
            f"📊 Engagement Report — {self.platform.upper()}",
            f"Period: {self.period_days} days, {self.total_posts} posts",
            f"Avg Engagement: {self.avg_engagement_rate:.2f}%",
            f"Performance: {self.performance_level.value.upper()}",
            f"Best content: {self.best_content_type.value}",
            f"Best time: {days[self.best_posting_day]} at {self.best_posting_hour}:00",
        ]
        if self.top_hashtags:
            lines.append("Top hashtags: " + ", ".join(
                f"#{h} ({r:.1f}%)" for h, r in self.top_hashtags[:5]
            ))
        if self.recommendations:
            lines.append("\n💡 Recommendations:")
            for r in self.recommendations:
                lines.append(f"  • {r}")
        return "\n".join(lines)


def classify_performance(rate: float, platform: str) -> PerformanceLevel:
    """Classify engagement rate against platform benchmarks."""
    benchmarks = PLATFORM_BENCHMARKS.get(platform, PLATFORM_BENCHMARKS["instagram"])
    if rate >= benchmarks["viral_rate"]:
        return PerformanceLevel.VIRAL
    if rate >= benchmarks["good_rate"]:
        return PerformanceLevel.HIGH
    if rate >= benchmarks["avg_rate"]:
        return PerformanceLevel.AVERAGE
    if rate >= benchmarks["avg_rate"] * 0.5:
        return PerformanceLevel.LOW
    return PerformanceLevel.UNDERPERFORMING


def viral_potential_score(metrics: PostMetrics) -> float:
    """Calculate viral potential score (0-100) based on early engagement signals."""
    score = 0.0

    # High engagement rate
    er = metrics.engagement_rate
    benchmarks = PLATFORM_BENCHMARKS.get(metrics.platform, PLATFORM_BENCHMARKS["instagram"])
    if er >= benchmarks["viral_rate"]:
        score += 40
    elif er >= benchmarks["good_rate"]:
        score += 25
    elif er >= benchmarks["avg_rate"]:
        score += 10

    # Share ratio (shares indicate viral spread)
    if metrics.total_engagement > 0:
        share_ratio = metrics.shares / metrics.total_engagement
        score += min(share_ratio * 100, 30)

    # Save ratio (saves indicate value)
    if metrics.total_engagement > 0:
        save_ratio = metrics.saves / metrics.total_engagement
        score += min(save_ratio * 50, 15)

    # Comment ratio (comments indicate discussion)
    if metrics.total_engagement > 0:
        comment_ratio = metrics.comments / metrics.total_engagement
        score += min(comment_ratio * 30, 15)

    return min(100.0, max(0.0, score))


def optimal_posting_times(posts: list[PostMetrics]) -> dict:
    """Analyze posting history to find optimal times.

    Returns dict with 'hourly' and 'daily' engagement averages.
    """
    hourly: dict[int, list[float]] = {h: [] for h in range(24)}
    daily: dict[int, list[float]] = {d: [] for d in range(7)}

    for post in posts:
        if not post.posted_at:
            continue
        try:
            dt = datetime.fromisoformat(post.posted_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        hourly[dt.hour].append(post.engagement_rate)
        daily[dt.weekday()].append(post.engagement_rate)

    hourly_avg = {
        h: (sum(rates) / len(rates)) if rates else 0.0
        for h, rates in hourly.items()
    }
    daily_avg = {
        d: (sum(rates) / len(rates)) if rates else 0.0
        for d, rates in daily.items()
    }

    return {"hourly": hourly_avg, "daily": daily_avg}


def hashtag_performance(posts: list[PostMetrics]) -> list[tuple[str, float]]:
    """Rank hashtags by average engagement rate when used."""
    tag_rates: dict[str, list[float]] = {}
    for post in posts:
        for tag in post.hashtags:
            tag_lower = tag.lower().lstrip("#")
            if tag_lower not in tag_rates:
                tag_rates[tag_lower] = []
            tag_rates[tag_lower].append(post.engagement_rate)

    # Average engagement per hashtag, sorted descending
    results = [
        (tag, sum(rates) / len(rates))
        for tag, rates in tag_rates.items()
        if len(rates) >= 2  # Minimum 2 uses for reliability
    ]
    results.sort(key=lambda x: -x[1])
    return results


def content_type_analysis(posts: list[PostMetrics]) -> dict[str, dict]:
    """Analyze performance by content type."""
    type_data: dict[str, list[float]] = {}
    for post in posts:
        ct = post.content_type.value
        if ct not in type_data:
            type_data[ct] = []
        type_data[ct].append(post.engagement_rate)

    return {
        ct: {
            "count": len(rates),
            "avg_rate": sum(rates) / len(rates),
            "median_rate": statistics.median(rates) if rates else 0,
            "max_rate": max(rates) if rates else 0,
        }
        for ct, rates in type_data.items()
    }


def engagement_decay_rate(metrics: PostMetrics, hours_data: dict[int, int]) -> float:
    """Calculate how quickly engagement drops after posting.

    hours_data: {hours_since_post: cumulative_engagement}
    Returns decay half-life in hours.
    """
    if not hours_data or len(hours_data) < 2:
        return 0.0

    total = max(hours_data.values())
    if total <= 0:
        return 0.0

    # Find when 50% of engagement was reached
    sorted_hours = sorted(hours_data.items())
    for hours, cumulative in sorted_hours:
        if cumulative >= total * 0.5:
            return float(hours)

    return float(sorted_hours[-1][0])


def analyze_engagement(posts: list[PostMetrics], platform: str = "instagram",
                       period_days: int = 30) -> EngagementReport:
    """Generate comprehensive engagement analysis."""
    if not posts:
        return EngagementReport(
            platform=platform,
            period_days=period_days,
            total_posts=0,
            avg_engagement_rate=0.0,
            median_engagement_rate=0.0,
            best_content_type=ContentType.IMAGE,
            best_posting_hour=12,
            best_posting_day=2,
            performance_level=PerformanceLevel.UNDERPERFORMING,
        )

    rates = [p.engagement_rate for p in posts]
    avg_rate = sum(rates) / len(rates)
    median_rate = statistics.median(rates)

    # Best content type
    ct_analysis = content_type_analysis(posts)
    best_ct = max(ct_analysis.items(), key=lambda x: x[1]["avg_rate"])[0] if ct_analysis else "image"

    # Best posting times
    timing = optimal_posting_times(posts)
    best_hour = max(timing["hourly"].items(), key=lambda x: x[1])[0] if timing["hourly"] else 12
    best_day = max(timing["daily"].items(), key=lambda x: x[1])[0] if timing["daily"] else 2

    # Top hashtags
    top_tags = hashtag_performance(posts)

    # Performance classification
    perf = classify_performance(avg_rate, platform)

    # Recommendations
    recs = []
    if perf in (PerformanceLevel.LOW, PerformanceLevel.UNDERPERFORMING):
        recs.append("Engagement below platform average — focus on content quality and timing")
    if best_ct in ("reel", "video"):
        recs.append(f"{best_ct.title()} content performs best — increase production")
    if top_tags:
        recs.append(f"Top hashtag #{top_tags[0][0]} boosts engagement — use consistently")

    benchmarks = PLATFORM_BENCHMARKS.get(platform, {})
    if avg_rate < benchmarks.get("avg_rate", 1):
        recs.append("Try posting at peak engagement hours to boost reach")
    if len(set(p.content_type for p in posts)) < 3:
        recs.append("Diversify content types — mix images, videos, and carousels")

    return EngagementReport(
        platform=platform,
        period_days=period_days,
        total_posts=len(posts),
        avg_engagement_rate=avg_rate,
        median_engagement_rate=median_rate,
        best_content_type=ContentType(best_ct),
        best_posting_hour=best_hour,
        best_posting_day=best_day,
        performance_level=perf,
        top_hashtags=top_tags[:10],
        content_type_rates=ct_analysis,
        hourly_rates=timing["hourly"],
        recommendations=recs,
    )
