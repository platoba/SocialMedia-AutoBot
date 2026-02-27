# SocialMedia AutoBot

🤖 Instagram/Twitter/TikTok automation toolkit via Telegram Bot.

## Features

- 📸 Instagram: profile stats, insights, recent posts, auto-publish
- 🐦 Twitter/X: search tweets, user lookup, trend monitoring
- 📊 Competitor tracking across platforms
- 🏷️ Hashtag research & suggestions
- 💡 AI content idea generator

## Quick Start

```bash
git clone https://github.com/platoba/SocialMedia-AutoBot.git
cd SocialMedia-AutoBot
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/ig_profile` | Instagram account overview |
| `/ig_insights` | Today's Instagram metrics |
| `/ig_posts` | Recent posts with engagement |
| `/ig_publish <url> <caption>` | Publish photo to Instagram |
| `/tw_search <query>` | Search recent tweets |
| `/tw_user <username>` | Twitter user profile |
| `/track <platform> <user>` | Track competitor account |
| `/hashtags <niche>` | Get hashtag suggestions |
| `/content_ideas <niche>` | Generate content ideas |

## Environment Variables

| Variable | Platform | Required |
|----------|----------|----------|
| `BOT_TOKEN` | Telegram | ✅ |
| `IG_ACCESS_TOKEN` | Instagram | ❌ |
| `IG_BUSINESS_ID` | Instagram | ❌ |
| `TW_BEARER_TOKEN` | Twitter | ❌ |
| `TT_ACCESS_TOKEN` | TikTok | ❌ |

## License

MIT

## 🔗 Related

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) - Affiliate link bot
- [AI-Listing-Writer](https://github.com/platoba/AI-Listing-Writer) - AI listing generator
