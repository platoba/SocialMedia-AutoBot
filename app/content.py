"""Content tools: hashtag research, content ideas, caption generator."""

import random
from typing import Optional


# Curated hashtag database by niche
HASHTAG_DB: dict[str, list[str]] = {
    "ecommerce": [
        "#ecommerce", "#dropshipping", "#shopify", "#amazon", "#onlineshopping",
        "#smallbusiness", "#entrepreneur", "#crossborder", "#aliexpress",
        "#onlinestore", "#ecommercetips", "#shopifytips", "#amazonfba",
    ],
    "tech": [
        "#ai", "#chatgpt", "#coding", "#startup", "#saas", "#nocode",
        "#automation", "#machinelearning", "#deeplearning", "#tech",
        "#programming", "#developer", "#artificialintelligence",
    ],
    "lifestyle": [
        "#lifestyle", "#travel", "#fitness", "#food", "#fashion",
        "#beauty", "#wellness", "#motivation", "#mindset", "#selfcare",
        "#healthylifestyle", "#travelgram", "#foodie",
    ],
    "marketing": [
        "#digitalmarketing", "#socialmedia", "#contentmarketing", "#seo",
        "#branding", "#marketing", "#growthhacking", "#emailmarketing",
        "#influencer", "#affiliatemarketing", "#marketingtips",
    ],
    "finance": [
        "#investing", "#crypto", "#bitcoin", "#stocks", "#trading",
        "#personalfinance", "#wealth", "#financialfreedom", "#money",
        "#passiveincome", "#realestate", "#forex",
    ],
    "gaming": [
        "#gaming", "#gamer", "#esports", "#twitch", "#streamer",
        "#videogames", "#pcgaming", "#ps5", "#xbox", "#nintendo",
    ],
}

# Content idea templates
IDEA_TEMPLATES = [
    "📹 「{niche}新手必看的5个坑」",
    "📊 「{niche}数据对比：2025 vs 2026」",
    "🎯 「我用{niche}月入$X的真实经历」",
    "🔥 「{niche}最新趋势解读」",
    "💰 「{niche}省钱/赚钱技巧Top10」",
    "❌ 「{niche}最常见的错误」",
    "✅ 「{niche}工具推荐清单」",
    "🆚 「{niche} A vs B 深度对比」",
    "📱 「{niche}一天的Vlog」",
    "🎤 「采访{niche}大佬的3个问题」",
    "📈 「{niche}从0到1完整教程」",
    "🤔 「{niche}你不知道的冷知识」",
    "💡 「{niche}效率提升300%的方法」",
    "🏆 「{niche}年度最佳盘点」",
    "⚡ 「60秒了解{niche}核心概念」",
]

# Caption templates by platform
CAPTION_TEMPLATES = {
    "ig": [
        "✨ {topic}\n\n{body}\n\n{hashtags}\n\n👉 Link in bio",
        "🔥 {topic}\n\n{body}\n\n💬 你怎么看？评论区见\n\n{hashtags}",
        "📸 {topic}\n\n{body}\n\n❤️ 双击保存\n\n{hashtags}",
    ],
    "tw": [
        "🧵 {topic}\n\n{body}\n\n{hashtags}",
        "{topic}\n\n{body}\n\nRT if you agree 🔄",
        "💡 {topic}\n\n{body}\n\n{hashtags}",
    ],
    "tt": [
        "{topic} 🎵\n\n{body}\n\n{hashtags} #fyp #foryou",
        "POV: {topic}\n\n{body}\n\n{hashtags} #viral",
        "等等...{topic}?!\n\n{body}\n\n{hashtags} #trending",
    ],
}


def suggest_hashtags(niche: str, count: int = 15) -> str:
    """Get hashtag suggestions for a niche."""
    niche_lower = niche.lower().strip()

    # Direct match
    for key, tags in HASHTAG_DB.items():
        if key in niche_lower or niche_lower in key:
            selected = random.sample(tags, min(count, len(tags)))
            return f"🏷️ {niche} 推荐标签 ({len(selected)}个):\n\n" + " ".join(selected)

    # Mix from all
    all_tags = [t for tags in HASHTAG_DB.values() for t in tags]
    selected = random.sample(all_tags, min(count, len(all_tags)))
    return f"🏷️ 热门标签:\n\n" + " ".join(selected)


def generate_ideas(niche: str, count: int = 7) -> str:
    """Generate content ideas for a niche."""
    niche = niche.strip() or "ecommerce"
    selected = random.sample(IDEA_TEMPLATES, min(count, len(IDEA_TEMPLATES)))
    lines = [f"💡 {niche} 内容灵感:\n"]
    for i, tmpl in enumerate(selected, 1):
        lines.append(f"{i}. {tmpl.format(niche=niche)}")
    return "\n".join(lines)


def generate_caption(platform: str, topic: str, body: str = "",
                     niche: str = "general") -> str:
    """Generate a platform-specific caption."""
    platform = platform.lower()
    templates = CAPTION_TEMPLATES.get(platform, CAPTION_TEMPLATES["ig"])
    template = random.choice(templates)

    # Get relevant hashtags
    niche_lower = niche.lower()
    hashtags = []
    for key, tags in HASHTAG_DB.items():
        if key in niche_lower or niche_lower in key:
            hashtags = random.sample(tags, min(5, len(tags)))
            break
    if not hashtags:
        all_tags = [t for tags in HASHTAG_DB.values() for t in tags]
        hashtags = random.sample(all_tags, 5)

    return template.format(
        topic=topic,
        body=body or f"关于{topic}的分享",
        hashtags=" ".join(hashtags),
    )


def get_best_posting_times(platform: str) -> str:
    """Get recommended posting times by platform."""
    times = {
        "ig": (
            "📸 Instagram 最佳发帖时间:\n\n"
            "🌅 周一-周五: 6:00-9:00, 12:00-14:00\n"
            "🌆 周六-周日: 9:00-11:00\n"
            "⭐ 黄金时段: 周三 11:00, 周五 10:00-11:00\n"
            "💡 Reels最佳: 9:00, 12:00, 19:00"
        ),
        "tw": (
            "🐦 Twitter/X 最佳发帖时间:\n\n"
            "🌅 周一-周五: 8:00-10:00, 12:00-13:00\n"
            "🌆 周六: 9:00-11:00\n"
            "⭐ 黄金时段: 周二-周四 9:00\n"
            "💡 Thread最佳: 工作日早8:00"
        ),
        "tt": (
            "🎵 TikTok 最佳发帖时间:\n\n"
            "🌅 周一-周五: 7:00-9:00, 12:00-15:00, 19:00-23:00\n"
            "🌆 周六-周日: 10:00-14:00, 19:00-23:00\n"
            "⭐ 黄金时段: 周二 9:00, 周四 12:00, 周五 17:00\n"
            "💡 提示: 发布后1小时内互动最关键"
        ),
    }
    return times.get(platform.lower(), "📊 请指定平台: ig, tw, tt")
