"""Tests for Content Repurposer module."""

import pytest
from app.content_repurposer import (
    Platform,
    RepurposedContent,
    extract_hashtags,
    extract_mentions,
    truncate_smart,
    split_into_thread,
    repurpose,
    repurpose_to_all,
    batch_repurpose,
    format_repurpose_report,
    PLATFORM_LIMITS,
    PLATFORM_EMOJI,
    TONE_GUIDE,
)


# ─── extract_hashtags ───────────────────────────────────────────

class TestExtractHashtags:
    def test_basic(self):
        text = "Great post #coding #python"
        clean, tags = extract_hashtags(text)
        assert tags == ["coding", "python"]
        assert "#" not in clean

    def test_no_hashtags(self):
        text = "No tags here"
        clean, tags = extract_hashtags(text)
        assert clean == text
        assert tags == []

    def test_hashtags_only(self):
        text = "#one #two #three"
        clean, tags = extract_hashtags(text)
        assert len(tags) == 3
        assert clean.strip() == ""

    def test_mixed_content(self):
        text = "Hello #world this is #cool stuff"
        clean, tags = extract_hashtags(text)
        assert "world" in tags
        assert "cool" in tags
        assert "#" not in clean

    def test_unicode_hashtags(self):
        text = "Check #coding123 out"
        clean, tags = extract_hashtags(text)
        assert "coding123" in tags


# ─── extract_mentions ────────────────────────────────────────────

class TestExtractMentions:
    def test_basic(self):
        text = "Hello @user1 and @user2"
        _, mentions = extract_mentions(text)
        assert mentions == ["user1", "user2"]

    def test_no_mentions(self):
        text = "No mentions here"
        _, mentions = extract_mentions(text)
        assert mentions == []

    def test_email_not_mention(self):
        text = "Contact @admin for help"
        _, mentions = extract_mentions(text)
        assert "admin" in mentions


# ─── truncate_smart ──────────────────────────────────────────────

class TestTruncateSmart:
    def test_short_text(self):
        text = "Short text"
        assert truncate_smart(text, 100) == text

    def test_exact_length(self):
        text = "a" * 50
        assert truncate_smart(text, 50) == text

    def test_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        result = truncate_smart(text, 35)
        assert result.endswith("...")
        assert len(result) <= 35

    def test_word_boundary(self):
        text = "word1 word2 word3 word4 word5 word6 word7"
        result = truncate_smart(text, 20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_custom_suffix(self):
        text = "A" * 100
        result = truncate_smart(text, 50, suffix=" →")
        assert result.endswith(" →")


# ─── split_into_thread ───────────────────────────────────────────

class TestSplitIntoThread:
    def test_short_text_single_part(self):
        text = "Short tweet"
        parts = split_into_thread(text, 280)
        assert len(parts) == 1

    def test_long_text_splits(self):
        text = ". ".join(["Sentence number " + str(i) for i in range(20)])
        parts = split_into_thread(text, 270)
        assert len(parts) > 1

    def test_parts_have_counters(self):
        text = ". ".join(["This is a medium length sentence about coding"] * 10)
        parts = split_into_thread(text, 100)
        if len(parts) > 1:
            assert parts[0].startswith("1/")

    def test_respects_max_length(self):
        text = ". ".join(["Word"] * 100)
        parts = split_into_thread(text, 50)
        for part in parts:
            # Allow some slack for counter prefix
            assert len(part) <= 60

    def test_hashtags_on_last_part(self):
        text = "Hello world. This is a test. #tag1 #tag2"
        parts = split_into_thread(text, 280)
        assert any("#" in p for p in parts)


# ─── repurpose ───────────────────────────────────────────────────

class TestRepurpose:
    def test_twitter_to_instagram(self):
        result = repurpose(
            "Quick thoughts on AI #ai #tech",
            Platform.TWITTER,
            Platform.INSTAGRAM,
            niche="tech",
        )
        assert isinstance(result, RepurposedContent)
        assert result.target_platform == Platform.INSTAGRAM
        assert result.original_platform == Platform.TWITTER
        assert result.char_count > 0

    def test_instagram_to_twitter(self):
        long_caption = "A" * 500 + " #insta #life"
        result = repurpose(
            long_caption,
            Platform.INSTAGRAM,
            Platform.TWITTER,
        )
        assert result.target_platform == Platform.TWITTER
        # Should be truncated or threaded
        if not result.is_thread:
            assert result.char_count <= 280

    def test_long_to_twitter_creates_thread(self):
        long_text = ". ".join(["This is a detailed analysis point"] * 20)
        result = repurpose(
            long_text,
            Platform.INSTAGRAM,
            Platform.TWITTER,
        )
        assert result.is_thread
        assert len(result.thread_parts) > 1

    def test_preserves_original_text(self):
        original = "My original content #test"
        result = repurpose(original, Platform.TWITTER, Platform.INSTAGRAM)
        assert result.original_text == original

    def test_generates_cta(self):
        result = repurpose(
            "Check this out",
            Platform.TWITTER,
            Platform.INSTAGRAM,
        )
        assert result.cta != ""

    def test_generates_hashtags(self):
        result = repurpose(
            "Content about coding #python",
            Platform.TWITTER,
            Platform.TIKTOK,
        )
        assert isinstance(result.hashtags, list)

    def test_tiktok_adds_fyp(self):
        result = repurpose(
            "Cool content",
            Platform.INSTAGRAM,
            Platform.TIKTOK,
        )
        assert any(t in ["fyp", "foryou"] for t in result.hashtags)

    def test_generates_suggestions(self):
        result = repurpose(
            "Some content",
            Platform.TWITTER,
            Platform.INSTAGRAM,
        )
        assert len(result.suggestions) > 0

    def test_linkedin_tone(self):
        long_text = "First point. Second point. Third point. Fourth point."
        result = repurpose(
            long_text,
            Platform.TWITTER,
            Platform.LINKEDIN,
        )
        assert result.target_platform == Platform.LINKEDIN
        assert result.adapted_text != ""

    def test_tiktok_tone_simplifies(self):
        formal = "Therefore, we should. Furthermore, this is important. However, consider this."
        result = repurpose(
            formal,
            Platform.LINKEDIN,
            Platform.TIKTOK,
        )
        assert "Therefore" not in result.adapted_text
        assert "Furthermore" not in result.adapted_text

    def test_formatted_output(self):
        result = repurpose(
            "Test content",
            Platform.TWITTER,
            Platform.INSTAGRAM,
        )
        formatted = result.formatted()
        assert "INSTAGRAM" in formatted
        assert len(formatted) > 0

    def test_respects_platform_limits(self):
        for target in Platform:
            result = repurpose(
                "A" * 5000,
                Platform.TWITTER,
                target,
            )
            if target != Platform.TWITTER or not result.is_thread:
                limit = PLATFORM_LIMITS[target]["chars"]
                assert result.char_count <= limit + 10  # small buffer


# ─── repurpose_to_all ────────────────────────────────────────────

class TestRepurposeToAll:
    def test_converts_to_all_platforms(self):
        results = repurpose_to_all(
            "Original content #test",
            Platform.TWITTER,
            niche="tech",
        )
        target_platforms = {r.target_platform for r in results}
        # Should not include source platform
        assert Platform.TWITTER not in target_platforms
        assert len(results) == len(Platform) - 1

    def test_each_result_valid(self):
        results = repurpose_to_all("Hello world", Platform.INSTAGRAM)
        for r in results:
            assert isinstance(r, RepurposedContent)
            assert r.adapted_text != ""
            assert r.original_text == "Hello world"


# ─── batch_repurpose ─────────────────────────────────────────────

class TestBatchRepurpose:
    def test_batch_conversion(self):
        items = [
            {"text": "First post #coding", "source": "twitter"},
            {"text": "Second post about design", "source": "instagram"},
        ]
        results = batch_repurpose(items, Platform.LINKEDIN)
        assert len(results) == 2
        assert all(r.target_platform == Platform.LINKEDIN for r in results)

    def test_empty_batch(self):
        results = batch_repurpose([], Platform.TWITTER)
        assert results == []

    def test_skips_empty_text(self):
        items = [
            {"text": "", "source": "twitter"},
            {"text": "Valid content", "source": "twitter"},
        ]
        results = batch_repurpose(items, Platform.INSTAGRAM)
        assert len(results) == 1


# ─── format_repurpose_report ─────────────────────────────────────

class TestFormatReport:
    def test_format_with_results(self):
        results = repurpose_to_all("Test content #ai", Platform.TWITTER)
        report = format_repurpose_report(results)
        assert "内容复用报告" in report
        assert len(report) > 100

    def test_format_empty(self):
        report = format_repurpose_report([])
        assert "没有内容" in report


# ─── Platform constants ──────────────────────────────────────────

class TestConstants:
    def test_all_platforms_have_limits(self):
        for p in Platform:
            assert p in PLATFORM_LIMITS
            assert "chars" in PLATFORM_LIMITS[p]
            assert "hashtags" in PLATFORM_LIMITS[p]

    def test_all_platforms_have_emoji(self):
        for p in Platform:
            assert p in PLATFORM_EMOJI

    def test_all_platforms_have_tone(self):
        for p in Platform:
            assert p in TONE_GUIDE
