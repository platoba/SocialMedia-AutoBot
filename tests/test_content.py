"""Tests for app.content module."""

import pytest
from app.content import (
    suggest_hashtags,
    generate_ideas,
    generate_caption,
    get_best_posting_times,
    HASHTAG_DB,
    IDEA_TEMPLATES,
    CAPTION_TEMPLATES,
)


class TestSuggestHashtags:
    def test_known_niche(self):
        result = suggest_hashtags("ecommerce")
        assert "推荐标签" in result
        assert "#" in result

    def test_partial_match(self):
        result = suggest_hashtags("tech startup")
        assert "#" in result

    def test_unknown_niche_fallback(self):
        result = suggest_hashtags("xyznonexistent")
        assert "标签" in result
        assert "#" in result

    def test_custom_count(self):
        result = suggest_hashtags("ecommerce", count=3)
        assert result.count("#") >= 3

    def test_all_niches_have_tags(self):
        for niche in HASHTAG_DB:
            result = suggest_hashtags(niche)
            assert "#" in result


class TestGenerateIdeas:
    def test_default_count(self):
        result = generate_ideas("ecommerce")
        assert "内容灵感" in result
        lines = [l for l in result.split("\n") if l.strip().startswith(("1.", "2.", "3."))]
        assert len(lines) >= 3

    def test_custom_count(self):
        result = generate_ideas("tech", count=3)
        assert "tech" in result

    def test_empty_niche_default(self):
        result = generate_ideas("")
        assert "ecommerce" in result

    def test_niche_in_output(self):
        result = generate_ideas("finance")
        assert "finance" in result

    def test_all_templates_valid(self):
        for tmpl in IDEA_TEMPLATES:
            formatted = tmpl.format(niche="test")
            assert "test" in formatted


class TestGenerateCaption:
    def test_ig_caption(self):
        result = generate_caption("ig", "测试话题", "正文内容", "ecommerce")
        assert "测试话题" in result
        assert "#" in result

    def test_tw_caption(self):
        result = generate_caption("tw", "测试")
        assert "测试" in result

    def test_tt_caption(self):
        result = generate_caption("tt", "测试视频")
        assert "测试视频" in result

    def test_unknown_platform_fallback(self):
        result = generate_caption("unknown", "topic")
        assert "topic" in result

    def test_no_body_default(self):
        result = generate_caption("ig", "topic")
        assert "关于topic" in result

    def test_all_platform_templates(self):
        for platform in CAPTION_TEMPLATES:
            for tmpl in CAPTION_TEMPLATES[platform]:
                result = tmpl.format(topic="T", body="B", hashtags="#x")
                assert "T" in result


class TestBestPostingTimes:
    def test_ig_times(self):
        result = get_best_posting_times("ig")
        assert "Instagram" in result
        assert "黄金时段" in result

    def test_tw_times(self):
        result = get_best_posting_times("tw")
        assert "Twitter" in result

    def test_tt_times(self):
        result = get_best_posting_times("tt")
        assert "TikTok" in result

    def test_unknown_platform(self):
        result = get_best_posting_times("weibo")
        assert "请指定平台" in result

    def test_case_insensitive(self):
        result = get_best_posting_times("IG")
        assert "Instagram" in result
