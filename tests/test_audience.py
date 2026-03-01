"""Tests for Audience Segmentation & Targeting Engine."""

import os
import json
import pytest
import tempfile
from app.audience import (
    AudienceEngine,
    FollowerProfile,
    AudienceSegment,
    AudienceInsights,
    SegmentType,
    EngagementTier,
    LifecycleStage,
)
from datetime import datetime, timedelta


@pytest.fixture
def engine():
    """Create a test engine with temp database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = AudienceEngine(db_path=path)
    yield eng
    eng.close()
    os.unlink(path)


def _make_profile(
    user_id: str = "user1",
    username: str = "testuser",
    platform: str = "instagram",
    likes: int = 10,
    comments: int = 5,
    shares: int = 2,
    saves: int = 3,
    days_ago_active: int = 1,
    days_ago_followed: int = 30,
    country: str = "US",
    language: str = "en",
    active_hours: list = None,
    preferred_content: list = None,
) -> FollowerProfile:
    now = datetime.now()
    return FollowerProfile(
        user_id=user_id,
        username=username,
        platform=platform,
        followed_at=(now - timedelta(days=days_ago_followed)).isoformat(),
        last_active=(now - timedelta(days=days_ago_active)).isoformat(),
        total_interactions=likes + comments + shares + saves,
        likes_given=likes,
        comments_given=comments,
        shares_given=shares,
        saves_given=saves,
        active_hours=active_hours or [9, 12, 18, 21],
        preferred_content=preferred_content or ["image", "reel"],
        language=language,
        country=country,
        device="mobile",
    )


# ─── FollowerProfile ─────────────────────────────────────────────

class TestFollowerProfile:
    def test_engagement_score(self):
        p = _make_profile(likes=10, comments=5, shares=2, saves=3)
        score = p.engagement_score
        # 10*1 + 5*3 + 2*5 + 3*2 = 10+15+10+6 = 41
        assert score == 41.0

    def test_engagement_score_zero(self):
        p = _make_profile(likes=0, comments=0, shares=0, saves=0)
        assert p.engagement_score == 0.0

    def test_engagement_score_capped(self):
        p = _make_profile(likes=100, comments=50, shares=30, saves=20)
        assert p.engagement_score <= 100.0

    def test_days_since_active(self):
        p = _make_profile(days_ago_active=5)
        assert p.days_since_active == 5

    def test_days_since_active_no_data(self):
        p = FollowerProfile(user_id="x", last_active="")
        assert p.days_since_active == 999


# ─── Add Follower ────────────────────────────────────────────────

class TestAddFollower:
    def test_add_single(self, engine):
        p = _make_profile()
        result = engine.add_follower(p)
        assert "✅" in result
        assert "testuser" in result

    def test_add_updates_existing(self, engine):
        p1 = _make_profile(likes=5)
        engine.add_follower(p1)
        p2 = _make_profile(likes=50)
        engine.add_follower(p2)

        row = engine.db.execute(
            "SELECT likes_given FROM followers WHERE user_id='user1'"
        ).fetchone()
        assert row["likes_given"] == 50

    def test_bulk_add(self, engine):
        profiles = [
            _make_profile(user_id=f"u{i}", username=f"user{i}")
            for i in range(20)
        ]
        result = engine.bulk_add_followers(profiles)
        assert "20" in result

        count = engine.db.execute(
            "SELECT COUNT(*) as cnt FROM followers"
        ).fetchone()
        assert count["cnt"] == 20


# ─── Tier Classification ────────────────────────────────────────

class TestTierClassification:
    def test_superfan(self, engine):
        p = _make_profile(likes=50, comments=30, shares=20, saves=10)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.SUPERFAN

    def test_active(self, engine):
        p = _make_profile(likes=10, comments=5, shares=2, saves=1)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.ACTIVE

    def test_casual(self, engine):
        p = _make_profile(likes=3, comments=1, shares=0, saves=0)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.CASUAL

    def test_passive(self, engine):
        p = _make_profile(likes=1, comments=0, shares=0, saves=0)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.PASSIVE

    def test_dormant(self, engine):
        p = _make_profile(likes=10, comments=5, days_ago_active=45)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.DORMANT

    def test_churned(self, engine):
        p = _make_profile(likes=10, comments=5, days_ago_active=100)
        tier = engine._classify_tier(p)
        assert tier == EngagementTier.CHURNED


# ─── Lifecycle Classification ────────────────────────────────────

class TestLifecycleClassification:
    def test_new_follower(self, engine):
        p = _make_profile(days_ago_followed=3)
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.NEW_FOLLOWER

    def test_onboarding(self, engine):
        p = _make_profile(days_ago_followed=15)
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.ONBOARDING

    def test_established(self, engine):
        p = _make_profile(days_ago_followed=60)
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.ESTABLISHED

    def test_loyal(self, engine):
        p = _make_profile(days_ago_followed=200, days_ago_active=1)
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.LOYAL

    def test_at_risk(self, engine):
        p = _make_profile(days_ago_followed=200, days_ago_active=20)
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.AT_RISK

    def test_no_follow_date(self, engine):
        p = FollowerProfile(user_id="x", followed_at="")
        stage = engine._classify_lifecycle(p)
        assert stage == LifecycleStage.ESTABLISHED


# ─── Insights ────────────────────────────────────────────────────

class TestInsights:
    def _populate(self, engine, n=50):
        profiles = []
        for i in range(n):
            likes = (i % 10) * 5
            comments = (i % 5) * 3
            country = ["US", "CN", "UK", "DE", "JP"][i % 5]
            lang = ["en", "zh", "en", "de", "ja"][i % 5]
            profiles.append(_make_profile(
                user_id=f"u{i}",
                username=f"user{i}",
                likes=likes,
                comments=comments,
                shares=i % 3,
                saves=i % 4,
                country=country,
                language=lang,
                days_ago_active=i % 40,
                active_hours=[9 + (i % 12), 18 + (i % 6)],
            ))
        engine.bulk_add_followers(profiles)

    def test_insights_with_data(self, engine):
        self._populate(engine)
        insights = engine.get_insights("instagram")
        assert insights.total_followers == 50
        assert len(insights.segments) > 0
        assert len(insights.engagement_distribution) > 0

    def test_insights_empty(self, engine):
        insights = engine.get_insights("instagram")
        assert insights.total_followers == 0
        assert "导入粉丝数据" in insights.growth_opportunities[0]

    def test_insights_summary(self, engine):
        self._populate(engine)
        insights = engine.get_insights("instagram")
        summary = insights.summary()
        assert "受众洞察" in summary
        assert "INSTAGRAM" in summary
        assert "50" in summary

    def test_insights_has_countries(self, engine):
        self._populate(engine)
        insights = engine.get_insights("instagram")
        assert len(insights.top_countries) > 0

    def test_insights_has_languages(self, engine):
        self._populate(engine)
        insights = engine.get_insights("instagram")
        assert len(insights.top_languages) > 0

    def test_insights_saves_snapshot(self, engine):
        self._populate(engine)
        engine.get_insights("instagram")
        snapshots = engine.db.execute(
            "SELECT COUNT(*) as cnt FROM audience_snapshots"
        ).fetchone()
        assert snapshots["cnt"] >= 1


# ─── Growth Trend ────────────────────────────────────────────────

class TestGrowthTrend:
    def test_insufficient_data(self, engine):
        result = engine.get_growth_trend("instagram")
        assert "数据不足" in result

    def test_with_snapshots(self, engine):
        # Insert manual snapshots
        engine.db.execute(
            "INSERT INTO audience_snapshots "
            "(platform, total_followers, segment_counts_json, captured_at) "
            "VALUES (?, ?, ?, ?)",
            ("instagram", 100, '{"superfan": 5, "active": 20}',
             (datetime.now() - timedelta(days=10)).isoformat())
        )
        engine.db.execute(
            "INSERT INTO audience_snapshots "
            "(platform, total_followers, segment_counts_json, captured_at) "
            "VALUES (?, ?, ?, ?)",
            ("instagram", 150, '{"superfan": 8, "active": 30}',
             datetime.now().isoformat())
        )
        engine.db.commit()

        result = engine.get_growth_trend("instagram", days=30)
        assert "增长趋势" in result
        assert "150" in result


# ─── Lookalikes ──────────────────────────────────────────────────

class TestLookalikes:
    def test_find_lookalikes(self, engine):
        # Add some followers in different tiers
        for i in range(10):
            engine.add_follower(_make_profile(
                user_id=f"super{i}", username=f"super{i}",
                likes=50, comments=30, shares=20, saves=10,
            ))
        for i in range(20):
            engine.add_follower(_make_profile(
                user_id=f"casual{i}", username=f"casual{i}",
                likes=3, comments=1, shares=0, saves=0,
            ))

        results = engine.find_lookalikes("superfan", "instagram", limit=10)
        assert isinstance(results, list)

    def test_no_target_segment(self, engine):
        results = engine.find_lookalikes("superfan", "instagram")
        assert results == []


# ─── Content Recommendations ────────────────────────────────────

class TestContentRecs:
    def test_superfan_recs(self, engine):
        result = engine.get_segment_content_recs("instagram", "superfan")
        assert "超级粉丝" in result
        assert "UGC" in result

    def test_active_recs(self, engine):
        result = engine.get_segment_content_recs("instagram", "active")
        assert "活跃粉丝" in result

    def test_casual_recs(self, engine):
        result = engine.get_segment_content_recs("instagram", "casual")
        assert "普通粉丝" in result

    def test_passive_recs(self, engine):
        result = engine.get_segment_content_recs("instagram", "passive")
        assert "潜水粉丝" in result

    def test_dormant_recs(self, engine):
        result = engine.get_segment_content_recs("instagram", "dormant")
        assert "沉睡粉丝" in result

    def test_unknown_tier(self, engine):
        result = engine.get_segment_content_recs("instagram", "unknown")
        assert "未知" in result


# ─── AudienceSegment ─────────────────────────────────────────────

class TestAudienceSegment:
    def test_summary(self):
        seg = AudienceSegment(
            id="test",
            name="Super Fans",
            segment_type=SegmentType.ENGAGEMENT,
            size=100,
            percentage=5.0,
            avg_engagement_rate=8.5,
            top_active_hours=[9, 12, 18],
            content_recommendations=["Post more reels"],
            growth_trend="growing",
        )
        summary = seg.summary()
        assert "Super Fans" in summary
        assert "100" in summary
        assert "5.0%" in summary
        assert "growing" in summary

    def test_summary_no_hours(self):
        seg = AudienceSegment(
            id="t", name="Test", segment_type=SegmentType.ENGAGEMENT,
            size=10, percentage=1.0, avg_engagement_rate=2.0,
        )
        summary = seg.summary()
        assert "Test" in summary
        assert "活跃时段" not in summary
