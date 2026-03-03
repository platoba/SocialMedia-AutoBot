"""
SocialMedia AutoBot - Telegram Bot
Instagram/TikTok/Twitter 社媒自动化工具
通过TG Bot控制，支持内容发布、数据监控、竞品追踪
"""

import os
import re
import time
import json
import random
import requests
from datetime import datetime

TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    raise ValueError("未设置 BOT_TOKEN!")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

# ── Instagram配置 ──
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BUSINESS_ID = os.environ.get("IG_BUSINESS_ID", "")

# ── TikTok配置 ──
TT_ACCESS_TOKEN = os.environ.get("TT_ACCESS_TOKEN", "")

# ── Twitter/X配置 ──
TW_BEARER_TOKEN = os.environ.get("TW_BEARER_TOKEN", "")
TW_API_KEY = os.environ.get("TW_API_KEY", "")
TW_API_SECRET = os.environ.get("TW_API_SECRET", "")
TW_ACCESS_TOKEN = os.environ.get("TW_ACCESS_TOKEN", "")
TW_ACCESS_SECRET = os.environ.get("TW_ACCESS_SECRET", "")


def tg_get(method, params=None):
    try:
        r = requests.get(f"{API_URL}/{method}", params=params, timeout=35)
        return r.json()
    except Exception as e:
        print(f"[API错误] {method}: {e}")
        return None


def tg_send(chat_id, text, reply_to=None, parse_mode="Markdown"):
    params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    if parse_mode:
        params["parse_mode"] = parse_mode
    result = tg_get("sendMessage", params)
    if not result or not result.get("ok"):
        params.pop("parse_mode", None)
        result = tg_get("sendMessage", params)
    return result


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return tg_get("getUpdates", params)


# ── Instagram Graph API ──────────────────────────────────
class Instagram:
    BASE = "https://graph.facebook.com/v19.0"

    @staticmethod
    def get_profile():
        if not IG_ACCESS_TOKEN:
            return "⚠️ 未配置 IG_ACCESS_TOKEN"
        r = requests.get(f"{Instagram.BASE}/{IG_BUSINESS_ID}",
            params={"fields": "username,followers_count,media_count,biography",
                    "access_token": IG_ACCESS_TOKEN}, timeout=15)
        if r.ok:
            d = r.json()
            return (f"📸 @{d.get('username')}\n"
                    f"👥 粉丝: {d.get('followers_count', 0):,}\n"
                    f"📝 帖子: {d.get('media_count', 0)}\n"
                    f"📋 简介: {d.get('biography', '')[:100]}")
        return f"❌ {r.status_code}: {r.text[:200]}"

    @staticmethod
    def get_insights():
        if not IG_ACCESS_TOKEN:
            return "⚠️ 未配置 IG_ACCESS_TOKEN"
        r = requests.get(f"{Instagram.BASE}/{IG_BUSINESS_ID}/insights",
            params={"metric": "impressions,reach,profile_views",
                    "period": "day", "access_token": IG_ACCESS_TOKEN}, timeout=15)
        if r.ok:
            data = r.json().get("data", [])
            lines = ["📊 Instagram 今日数据\n"]
            for m in data:
                val = m.get("values", [{}])[-1].get("value", 0)
                lines.append(f"  {m['title']}: {val:,}")
            return "\n".join(lines)
        return f"❌ {r.status_code}"

    @staticmethod
    def get_recent_media(limit=5):
        if not IG_ACCESS_TOKEN:
            return "⚠️ 未配置 IG_ACCESS_TOKEN"
        r = requests.get(f"{Instagram.BASE}/{IG_BUSINESS_ID}/media",
            params={"fields": "id,caption,like_count,comments_count,timestamp,permalink",
                    "limit": limit, "access_token": IG_ACCESS_TOKEN}, timeout=15)
        if r.ok:
            posts = r.json().get("data", [])
            lines = [f"📸 最近{len(posts)}条帖子\n"]
            for p in posts:
                cap = (p.get("caption") or "")[:40]
                lines.append(f"❤️ {p.get('like_count', 0)} 💬 {p.get('comments_count', 0)} | {cap}")
            return "\n".join(lines)
        return f"❌ {r.status_code}"

    @staticmethod
    def publish_photo(image_url, caption):
        if not IG_ACCESS_TOKEN:
            return "⚠️ 未配置 IG_ACCESS_TOKEN"
        # Step 1: Create container
        r1 = requests.post(f"{Instagram.BASE}/{IG_BUSINESS_ID}/media",
            data={"image_url": image_url, "caption": caption,
                  "access_token": IG_ACCESS_TOKEN}, timeout=30)
        if not r1.ok:
            return f"❌ 创建失败: {r1.text[:200]}"
        container_id = r1.json().get("id")
        # Step 2: Publish
        r2 = requests.post(f"{Instagram.BASE}/{IG_BUSINESS_ID}/media_publish",
            data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN}, timeout=30)
        if r2.ok:
            return f"✅ 发布成功! ID: {r2.json().get('id')}"
        return f"❌ 发布失败: {r2.text[:200]}"


# ── Twitter/X API ─────────────────────────────────────────
class Twitter:
    @staticmethod
    def search(query, max_results=10):
        if not TW_BEARER_TOKEN:
            return "⚠️ 未配置 TW_BEARER_TOKEN"
        r = requests.get("https://api.twitter.com/2/tweets/search/recent",
            params={"query": query, "max_results": max_results,
                    "tweet.fields": "public_metrics,created_at"},
            headers={"Authorization": f"Bearer {TW_BEARER_TOKEN}"}, timeout=15)
        if r.ok:
            tweets = r.json().get("data", [])
            lines = [f"🐦 搜索: {query} ({len(tweets)}条)\n"]
            for t in tweets[:5]:
                m = t.get("public_metrics", {})
                lines.append(f"❤️{m.get('like_count',0)} 🔄{m.get('retweet_count',0)} | {t['text'][:60]}")
            return "\n".join(lines)
        return f"❌ {r.status_code}"

    @staticmethod
    def get_user(username):
        if not TW_BEARER_TOKEN:
            return "⚠️ 未配置 TW_BEARER_TOKEN"
        r = requests.get(f"https://api.twitter.com/2/users/by/username/{username}",
            params={"user.fields": "public_metrics,description"},
            headers={"Authorization": f"Bearer {TW_BEARER_TOKEN}"}, timeout=15)
        if r.ok:
            d = r.json().get("data", {})
            m = d.get("public_metrics", {})
            return (f"🐦 @{d.get('username')}\n"
                    f"👥 粉丝: {m.get('followers_count', 0):,}\n"
                    f"📝 推文: {m.get('tweet_count', 0):,}\n"
                    f"📋 {d.get('description', '')[:100]}")
        return f"❌ {r.status_code}"


# ── 竞品追踪 ──────────────────────────────────────────────
tracked_accounts = {}


def track_account(platform, username):
    key = f"{platform}:{username}"
    tracked_accounts[key] = {"added": datetime.now().isoformat(), "platform": platform, "username": username}
    return f"✅ 已追踪 {platform} @{username}"


def list_tracked():
    if not tracked_accounts:
        return "📋 暂无追踪账号"
    lines = ["📋 追踪列表\n"]
    for k, v in tracked_accounts.items():
        lines.append(f"  {v['platform']} @{v['username']}")
    return "\n".join(lines)


# ── Hashtag研究 ───────────────────────────────────────────
TRENDING_HASHTAGS = {
    "ecommerce": ["#ecommerce", "#dropshipping", "#shopify", "#amazon", "#onlineshopping",
                   "#smallbusiness", "#entrepreneur", "#crossborder", "#aliexpress"],
    "tech": ["#ai", "#chatgpt", "#coding", "#startup", "#saas", "#nocode",
             "#automation", "#machinelearning", "#deeplearning"],
    "lifestyle": ["#lifestyle", "#travel", "#fitness", "#food", "#fashion",
                  "#beauty", "#wellness", "#motivation", "#mindset"],
}


def suggest_hashtags(niche):
    niche_lower = niche.lower()
    for key, tags in TRENDING_HASHTAGS.items():
        if key in niche_lower:
            return f"🏷️ {niche} 推荐标签:\n\n" + " ".join(tags)
    all_tags = [t for tags in TRENDING_HASHTAGS.values() for t in tags]
    return f"🏷️ 热门标签:\n\n" + " ".join(random.sample(all_tags, min(10, len(all_tags))))


# ── 命令处理 ──────────────────────────────────────────────
def handle(chat_id, msg_id, text):
    cmd = text.split()[0].lower() if text else ""
    args = text[len(cmd):].strip() if text else ""

    if cmd == "/start":
        tg_send(chat_id,
            "🤖 *SocialMedia AutoBot*\n\n"
            "社媒自动化工具箱\n\n"
            "📸 *Instagram*\n"
            "  /ig\\_profile — 账号概览\n"
            "  /ig\\_insights — 今日数据\n"
            "  /ig\\_posts — 最近帖子\n"
            "  /ig\\_publish <图片URL> <文案> — 发帖\n\n"
            "🐦 *Twitter/X*\n"
            "  /tw\\_search <关键词> — 搜索推文\n"
            "  /tw\\_user <用户名> — 查看用户\n\n"
            "📊 *工具*\n"
            "  /track <平台> <用户名> — 追踪竞品\n"
            "  /tracked — 查看追踪列表\n"
            "  /hashtags <领域> — 标签推荐\n"
            "  /content\\_ideas <领域> — 内容灵感", msg_id)

    elif cmd == "/ig_profile":
        tg_send(chat_id, Instagram.get_profile(), msg_id)
    elif cmd == "/ig_insights":
        tg_send(chat_id, Instagram.get_insights(), msg_id)
    elif cmd == "/ig_posts":
        tg_send(chat_id, Instagram.get_recent_media(), msg_id)
    elif cmd == "/ig_publish":
        parts = args.split(" ", 1)
        if len(parts) < 2:
            tg_send(chat_id, "用法: /ig_publish <图片URL> <文案>", msg_id)
        else:
            tg_send(chat_id, Instagram.publish_photo(parts[0], parts[1]), msg_id)

    elif cmd == "/tw_search":
        if not args:
            tg_send(chat_id, "用法: /tw_search <关键词>", msg_id)
        else:
            tg_send(chat_id, Twitter.search(args), msg_id)
    elif cmd == "/tw_user":
        if not args:
            tg_send(chat_id, "用法: /tw_user <用户名>", msg_id)
        else:
            tg_send(chat_id, Twitter.get_user(args.lstrip("@")), msg_id)

    elif cmd == "/track":
        parts = args.split()
        if len(parts) < 2:
            tg_send(chat_id, "用法: /track <ig|tw|tt> <用户名>", msg_id)
        else:
            tg_send(chat_id, track_account(parts[0], parts[1]), msg_id)
    elif cmd == "/tracked":
        tg_send(chat_id, list_tracked(), msg_id)
    elif cmd == "/hashtags":
        tg_send(chat_id, suggest_hashtags(args or "general"), msg_id)

    elif cmd == "/content_ideas":
        niche = args or "ecommerce"
        ideas = [
            f"💡 {niche} 内容灵感:\n",
            f"1. 📹 「{niche}新手必看的5个坑」",
            f"2. 📊 「{niche}数据对比：2025 vs 2026」",
            f"3. 🎯 「我用{niche}月入$X的真实经历」",
            f"4. 🔥 「{niche}最新趋势解读」",
            f"5. 💰 「{niche}省钱/赚钱技巧Top10」",
            f"6. ❌ 「{niche}最常见的错误」",
            f"7. ✅ 「{niche}工具推荐清单」",
        ]
        tg_send(chat_id, "\n".join(ideas), msg_id)


def main():
    print(f"\n{'='*50}")
    print(f"  SocialMedia AutoBot")
    platforms = []
    if IG_ACCESS_TOKEN: platforms.append("Instagram")
    if TW_BEARER_TOKEN: platforms.append("Twitter")
    if TT_ACCESS_TOKEN: platforms.append("TikTok")
    print(f"  已配置: {', '.join(platforms) if platforms else '无 (仅工具模式)'}")
    print(f"{'='*50}")

    me = tg_get("getMe")
    if me and me.get("ok"):
        print(f"\n✅ @{me['result']['username']} 已上线!")
    else:
        print("\n❌ 无法连接Telegram!")
        return

    offset = None
    while True:
        try:
            result = get_updates(offset)
            if not result or not result.get("ok"):
                time.sleep(5)
                continue
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue
                text = (msg.get("text") or "").strip()
                if text:
                    handle(msg["chat"]["id"], msg["message_id"], text)
        except KeyboardInterrupt:
            print("\n\n👋 已停止!")
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

# ============ 危机监测功能 ============
from app.crisis_monitor import CrisisMonitor

crisis_monitor = CrisisMonitor(brand_keywords=['YourBrand'])

@bot.message_handler(commands=['crisis'])
async def handle_crisis_command(message):
    """危机监测报告"""
    try:
        report = crisis_monitor.get_crisis_report(hours=24)
        
        response = "🚨 **24小时危机监测报告**\n\n"
        response += f"📊 总警报数: {report['total_alerts']}\n\n"
        response += "**按严重程度:**\n"
        response += f"🔴 Critical: {report['by_severity']['critical']}\n"
        response += f"🟠 High: {report['by_severity']['high']}\n"
        response += f"🟡 Medium: {report['by_severity']['medium']}\n"
        response += f"🟢 Low: {report['by_severity']['low']}\n\n"
        
        if report['top_keywords']:
            response += "**高频负面关键词:**\n"
            for kw, count in report['top_keywords'][:5]:
                response += f"• {kw}: {count}次\n"
        
        if report['most_critical']:
            response += "\n**最严重警报:**\n"
            for alert in report['most_critical'][:3]:
                response += f"\n🚨 {alert.platform} - {alert.severity}\n"
                response += f"   {alert.content[:100]}...\n"
                response += f"   互动: {alert.engagement} | 情感: {alert.sentiment_score:.2f}\n"
        
        await bot.reply_to(message, response, parse_mode='Markdown')
    
    except Exception as e:
        await bot.reply_to(message, f"❌ 错误: {str(e)}")

@bot.message_handler(commands=['monitor'])
async def handle_monitor_command(message):
    """启动实时监控"""
    try:
        args = message.text.split()[1:]
        if not args:
            await bot.reply_to(message, "用法: /monitor <品牌关键词>")
            return
        
        keyword = ' '.join(args)
        
        # 这里应该集成实际的社交媒体API
        # 示例：监控Twitter提及
        mentions = []  # 从API获取
        
        alerts = await crisis_monitor.monitor_mentions('twitter', mentions)
        
        if alerts:
            response = f"🚨 检测到 {len(alerts)} 条警报!\n\n"
            for alert in alerts[:5]:
                response += f"**{alert.severity.upper()}** - {alert.platform}\n"
                response += f"{alert.content[:100]}...\n"
                response += f"建议: {', '.join(crisis_monitor.get_response_suggestions(alert)[:2])}\n\n"
        else:
            response = f"✅ 未检测到危机信号 (关键词: {keyword})"
        
        await bot.reply_to(message, response, parse_mode='Markdown')
    
    except Exception as e:
        await bot.reply_to(message, f"❌ 错误: {str(e)}")
