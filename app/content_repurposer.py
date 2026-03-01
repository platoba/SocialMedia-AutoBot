"""Cross-Platform Content Repurposer.

Convert content from one platform format to another, maximizing reach
by adapting tone, length, hashtags, and structure for each platform.

Supported conversions:
- Tweet → Instagram caption / TikTok script / LinkedIn post / Thread
- Blog post → Tweet thread / Instagram carousel / TikTok script
- Instagram caption → Tweet / LinkedIn post
- Any text → Platform-optimized version
"""

import re
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    THREADS = "threads"


PLATFORM_LIMITS = {
    Platform.TWITTER: {"chars": 280, "hashtags": 3, "mentions": 5},
    Platform.INSTAGRAM: {"chars": 2200, "hashtags": 30, "mentions": 20},
    Platform.TIKTOK: {"chars": 2200, "hashtags": 5, "mentions": 5},
    Platform.LINKEDIN: {"chars": 3000, "hashtags": 5, "mentions": 10},
    Platform.FACEBOOK: {"chars": 63206, "hashtags": 5, "mentions": 20},
    Platform.YOUTUBE: {"chars": 5000, "hashtags": 15, "mentions": 0},
    Platform.THREADS: {"chars": 500, "hashtags": 5, "mentions": 5},
}

PLATFORM_EMOJI = {
    Platform.TWITTER: "🐦",
    Platform.INSTAGRAM: "📸",
    Platform.TIKTOK: "🎵",
    Platform.LINKEDIN: "💼",
    Platform.FACEBOOK: "📘",
    Platform.YOUTUBE: "🎬",
    Platform.THREADS: "🧵",
}

# Tone adjustments per platform
TONE_GUIDE = {
    Platform.TWITTER: "concise, witty, conversational, thread-worthy",
    Platform.INSTAGRAM: "visual, inspirational, story-driven, emoji-rich",
    Platform.TIKTOK: "casual, trendy, hook-first, Gen-Z friendly",
    Platform.LINKEDIN: "professional, insightful, value-driven, thought leadership",
    Platform.FACEBOOK: "friendly, community-focused, shareable",
    Platform.YOUTUBE: "descriptive, SEO-optimized, keyword-rich",
    Platform.THREADS: "casual, brief, conversation-starting",
}


@dataclass
class RepurposedContent:
    """Result of content repurposing."""
    original_platform: Platform
    target_platform: Platform
    original_text: str
    adapted_text: str
    hashtags: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    cta: str = ""
    char_count: int = 0
    is_thread: bool = False
    thread_parts: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.char_count = len(self.adapted_text)

    def formatted(self) -> str:
        emoji = PLATFORM_EMOJI.get(self.target_platform, "📝")
        lines = [
            f"{emoji} {self.target_platform.value.upper()} 版本",
            f"({self.char_count} chars)",
            "",
            self.adapted_text,
        ]
        if self.hashtags:
            lines.append("")
            lines.append(" ".join(f"#{t}" for t in self.hashtags))
        if self.cta:
            lines.append("")
            lines.append(f"📢 CTA: {self.cta}")
        if self.is_thread and self.thread_parts:
            lines.append("")
            lines.append(f"🧵 Thread ({len(self.thread_parts)} parts):")
            for i, part in enumerate(self.thread_parts, 1):
                lines.append(f"  {i}/{len(self.thread_parts)}: {part[:80]}...")
        if self.suggestions:
            lines.append("")
            lines.append("💡 建议:")
            for s in self.suggestions:
                lines.append(f"  • {s}")
        return "\n".join(lines)


def extract_hashtags(text: str) -> tuple[str, list[str]]:
    """Extract hashtags from text, return cleaned text and hashtags list."""
    hashtags = re.findall(r"#(\w+)", text)
    cleaned = re.sub(r"\s*#\w+", "", text).strip()
    return cleaned, hashtags


def extract_mentions(text: str) -> tuple[str, list[str]]:
    """Extract @mentions from text."""
    mentions = re.findall(r"@(\w+)", text)
    return text, mentions


def truncate_smart(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text at sentence boundary if possible."""
    if len(text) <= max_chars:
        return text

    target = max_chars - len(suffix)
    # Try to break at sentence
    for sep in [". ", "! ", "? ", "\n"]:
        idx = text.rfind(sep, 0, target)
        if idx > target * 0.5:
            return text[: idx + 1].rstrip() + suffix

    # Break at word boundary
    idx = text.rfind(" ", 0, target)
    if idx > 0:
        return text[:idx].rstrip() + suffix

    return text[:target] + suffix


def split_into_thread(text: str, max_per_part: int = 270) -> list[str]:
    """Split long text into tweet-thread parts."""
    clean, hashtags = extract_hashtags(text)
    sentences = re.split(r"(?<=[.!?])\s+", clean)

    parts: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_per_part:
            if current:
                parts.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence

    if current:
        parts.append(current.strip())

    # Add counter prefix
    total = len(parts)
    if total > 1:
        parts = [f"{i}/{total} {p}" for i, p in enumerate(parts, 1)]

    # Add hashtags to last part if room
    if hashtags and parts:
        tag_str = " " + " ".join(f"#{t}" for t in hashtags[:3])
        if len(parts[-1]) + len(tag_str) <= max_per_part:
            parts[-1] += tag_str

    return parts


def _add_hook(text: str, platform: Platform) -> str:
    """Add a platform-appropriate hook to the beginning."""
    hooks = {
        Platform.TWITTER: [
            "🧵", "Hot take:", "Unpopular opinion:", "This →",
            "Thread:", "Let's talk about", "PSA:",
        ],
        Platform.TIKTOK: [
            "Wait for it...", "POV:", "Storytime:", "Nobody talks about this but",
            "This changed everything:", "Life hack:",
        ],
        Platform.INSTAGRAM: [
            "✨", "Save this for later 📌", "Real talk:",
            "Swipe for more →", "The truth about",
        ],
        Platform.LINKEDIN: [
            "I learned something important:", "Here's what nobody tells you about",
            "After years in this industry:", "3 lessons:",
            "A thread on", "Controversial take:",
        ],
    }
    platform_hooks = hooks.get(platform, [])
    if not platform_hooks:
        return text

    # Don't add hook if text already starts with an emoji or hook-like text
    if text and (text[0] in "🧵🔥💡✨📌🎯💰" or text.startswith(("Thread", "Hot take", "POV"))):
        return text

    return text  # Return as-is; hooks are provided in suggestions


def _adapt_tone(text: str, source: Platform, target: Platform) -> str:
    """Adapt text tone for target platform."""
    adapted = text

    if target == Platform.TWITTER:
        # Make concise
        adapted = re.sub(r"\n{2,}", "\n", adapted)
        # Remove verbose phrases
        verbose = [
            "In this post, I'll discuss ",
            "Today I want to share ",
            "Let me explain ",
            "I'd like to talk about ",
        ]
        for phrase in verbose:
            adapted = adapted.replace(phrase, "")

    elif target == Platform.LINKEDIN:
        # Add line breaks for readability
        sentences = re.split(r"(?<=[.!?])\s+", adapted)
        if len(sentences) > 3:
            # LinkedIn loves one-sentence paragraphs
            adapted = "\n\n".join(sentences)

    elif target == Platform.TIKTOK:
        # Keep it short and punchy
        adapted = re.sub(r"\n{2,}", "\n", adapted)
        # Remove formal language
        adapted = adapted.replace("Therefore, ", "So ")
        adapted = adapted.replace("Furthermore, ", "Plus, ")
        adapted = adapted.replace("However, ", "But ")
        adapted = adapted.replace("In conclusion, ", "Bottom line: ")

    elif target == Platform.INSTAGRAM:
        # Add emoji spacing
        adapted = re.sub(r"\n{3,}", "\n\n", adapted)

    return adapted.strip()


def _generate_cta(platform: Platform, niche: str = "") -> str:
    """Generate platform-specific call-to-action."""
    ctas = {
        Platform.TWITTER: [
            "RT if you agree 🔄",
            "Like + Follow for more",
            "Thoughts? 👇",
            "Drop a 🔥 if this helped",
        ],
        Platform.INSTAGRAM: [
            "Save this for later 📌",
            "Tag someone who needs this ❤️",
            "Link in bio 👆",
            "Double tap if you agree 💛",
            "Follow for more tips ✨",
        ],
        Platform.TIKTOK: [
            "Follow for Part 2!",
            "Comment what you want to see next 👇",
            "Share with someone who needs this",
            "Like if this helped 🙏",
        ],
        Platform.LINKEDIN: [
            "Follow for more insights",
            "Agree? Disagree? Let me know below",
            "♻️ Repost to share with your network",
            "What would you add to this list?",
        ],
        Platform.FACEBOOK: [
            "Share with someone who needs this!",
            "What do you think? Comment below 👇",
            "Like this page for more!",
        ],
    }
    import random
    options = ctas.get(platform, ["Let me know your thoughts!"])
    return random.choice(options)


def _select_hashtags(
    source_tags: list[str], target: Platform, niche: str = ""
) -> list[str]:
    """Select and limit hashtags for target platform."""
    limit = PLATFORM_LIMITS.get(target, {}).get("hashtags", 5)

    # Platform-specific always-add tags
    platform_tags = {
        Platform.TIKTOK: ["fyp", "foryou"],
        Platform.INSTAGRAM: [],
        Platform.TWITTER: [],
        Platform.LINKEDIN: [],
    }
    must_add = platform_tags.get(target, [])

    # Combine: must-add + source tags (deduplicated)
    seen = set()
    result = []
    for tag in must_add + source_tags:
        tag_lower = tag.lower().lstrip("#")
        if tag_lower not in seen:
            seen.add(tag_lower)
            result.append(tag_lower)

    return result[:limit]


def repurpose(
    text: str,
    source: Platform,
    target: Platform,
    niche: str = "",
) -> RepurposedContent:
    """Repurpose content from source platform to target platform.

    Args:
        text: Original content text
        source: Source platform
        target: Target platform
        niche: Content niche for hashtag optimization

    Returns:
        RepurposedContent with adapted text and metadata
    """
    # Extract existing hashtags and mentions
    clean_text, source_tags = extract_hashtags(text)
    _, mentions = extract_mentions(clean_text)

    # Adapt tone
    adapted = _adapt_tone(clean_text, source, target)

    # Handle length constraints
    max_chars = PLATFORM_LIMITS.get(target, {}).get("chars", 2000)
    is_thread = False
    thread_parts: list[str] = []

    if target == Platform.TWITTER and len(adapted) > 280:
        # Convert to thread
        thread_parts = split_into_thread(adapted)
        if len(thread_parts) > 1:
            adapted = thread_parts[0]
            is_thread = True
        else:
            # Single block text (no sentence boundaries) — truncate
            adapted = truncate_smart(adapted, 280)
    else:
        adapted = truncate_smart(adapted, max_chars)

    # Select hashtags
    hashtags = _select_hashtags(source_tags, target, niche)

    # Generate CTA
    cta = _generate_cta(target, niche)

    # Build suggestions
    suggestions = _build_suggestions(source, target, clean_text)

    return RepurposedContent(
        original_platform=source,
        target_platform=target,
        original_text=text,
        adapted_text=adapted,
        hashtags=hashtags,
        cta=cta,
        is_thread=is_thread,
        thread_parts=thread_parts,
        suggestions=suggestions,
    )


def _build_suggestions(source: Platform, target: Platform, text: str) -> list[str]:
    """Generate platform-specific adaptation suggestions."""
    suggestions = []

    if target == Platform.INSTAGRAM:
        suggestions.append("添加高质量配图或轮播图提升互动")
        if len(text) > 500:
            suggestions.append("考虑做成轮播图(Carousel)，每页一个要点")
        suggestions.append("前125字最重要——'更多'折叠前的hook")

    elif target == Platform.TIKTOK:
        suggestions.append("前3秒是关键——用strong hook开场")
        suggestions.append("考虑用画外音+字幕文本叠加")
        if len(text) > 300:
            suggestions.append("内容较长，建议拆分为系列(Part 1/2/3)")

    elif target == Platform.TWITTER:
        if len(text) > 280:
            suggestions.append(f"内容已自动拆分为Thread")
        suggestions.append("添加一张信息图会提升RT率2-3倍")
        suggestions.append("考虑使用Twitter Poll增加互动")

    elif target == Platform.LINKEDIN:
        suggestions.append("LinkedIn偏好'故事型'内容，开头讲个人经历")
        suggestions.append("每段只写1-2句，增加可读性")
        suggestions.append("文末提问可以5x提升评论数")

    elif target == Platform.YOUTUBE:
        suggestions.append("标题加入关键词提升搜索排名")
        suggestions.append("前30秒决定观众留存率")

    # Cross-platform suggestions
    if source == Platform.TWITTER and target == Platform.INSTAGRAM:
        suggestions.append("Twitter的简洁观点可以扩展为Instagram故事")

    if source == Platform.INSTAGRAM and target == Platform.TWITTER:
        suggestions.append("提炼Instagram长文的核心观点做精简版")

    return suggestions


def repurpose_to_all(text: str, source: Platform, niche: str = "") -> list[RepurposedContent]:
    """Repurpose content to all other platforms."""
    results = []
    for target in Platform:
        if target != source:
            results.append(repurpose(text, source, target, niche))
    return results


def batch_repurpose(
    items: list[dict], target: Platform, niche: str = ""
) -> list[RepurposedContent]:
    """Batch repurpose multiple content items.

    Each item should have: {'text': str, 'source': str}
    """
    results = []
    for item in items:
        text = item.get("text", "")
        source = Platform(item.get("source", "twitter"))
        if text:
            results.append(repurpose(text, source, target, niche))
    return results


def format_repurpose_report(results: list[RepurposedContent]) -> str:
    """Format multiple repurposed results into a readable report."""
    if not results:
        return "📝 没有内容需要转换"

    lines = [f"🔄 内容复用报告 ({len(results)} 个平台)\n"]
    for r in results:
        lines.append(r.formatted())
        lines.append("")
        lines.append("─" * 40)
        lines.append("")

    return "\n".join(lines)
