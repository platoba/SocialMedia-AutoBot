# SocialMedia-AutoBot v2.0

🤖 **多平台社交媒体自动化运营 Telegram Bot** — 支持 Instagram、Twitter/X、TikTok 三大平台的一站式内容管理。

[![CI](https://github.com/platoba/SocialMedia-AutoBot/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/SocialMedia-AutoBot/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ 功能特性

### 🎯 多平台集成
- **Instagram** — 发帖、轮播、Stories、Insights数据、标签搜索
- **Twitter/X** — 搜索推文、用户分析、趋势追踪
- **TikTok** — 视频管理、搜索、上传、创作者数据

### 📊 竞品分析
- 追踪竞品账号 (Instagram/Twitter/TikTok)
- 粉丝增长监控 + 快照对比
- 互动率计算和趋势分析

### 📅 智能排期
- SQLite持久化排期队列
- 自动发布到时帖子
- 发布统计 (成功/失败/取消)
- 最佳发帖时间推荐

### 💡 内容工具
- AI标签推荐 (6大领域, 80+标签)
- 内容创意生成器 (15+模板)
- 分平台文案生成器
- 最佳发帖时间查询

## 🏗️ 架构

```
app/
├── __init__.py          # 入口
├── config.py            # 配置管理 (dataclass + env)
├── telegram.py          # Telegram Bot API 客户端
├── analytics.py         # 竞品追踪 + SQLite分析
├── scheduler.py         # 内容排期 + SQLite持久化
├── content.py           # 标签/创意/文案生成
└── platforms/
    ├── instagram.py     # Instagram Graph API
    ├── twitter.py       # Twitter API v2
    └── tiktok.py        # TikTok Content API
```

## 🚀 快速开始

### 本地运行
```bash
cp .env.example .env
# 编辑 .env 填入 BOT_TOKEN + 平台API密钥

pip install -e ".[dev]"
python -m app
```

### Docker
```bash
cp .env.example .env
docker compose up -d
```

## 📱 TG Bot 命令

| 命令 | 说明 |
|------|------|
| `/start` | 欢迎 + 帮助 |
| `/help` | 命令列表 |
| `/ig profile` | Instagram资料 |
| `/ig posts` | 最近帖子 |
| `/ig insights` | 今日数据 |
| `/ig publish <url> <文案>` | 发布图片 |
| `/tw search <关键词>` | 搜索推文 |
| `/tw user <用户名>` | 用户分析 |
| `/tt profile` | TikTok资料 |
| `/tt videos` | 最近视频 |
| `/tt search <关键词>` | 搜索视频 |
| `/track <平台> <用户名>` | 追踪竞品 |
| `/untrack <平台> <用户名>` | 取消追踪 |
| `/tracked` | 追踪列表 |
| `/growth <平台> <用户名>` | 增长报告 |
| `/schedule <平台> <时间> <文案>` | 排期发布 |
| `/queue` | 排期队列 |
| `/cancel <ID>` | 取消排期 |
| `/hashtags <领域>` | 标签推荐 |
| `/ideas <领域>` | 内容灵感 |
| `/caption <平台> <话题>` | 生成文案 |
| `/times <平台>` | 最佳发帖时间 |

## 🧪 测试

```bash
make test           # 运行测试
make coverage       # 覆盖率报告
make lint           # 代码检查
```

**测试覆盖:**
- `test_config.py` — 配置管理 (12项)
- `test_content.py` — 内容工具 (18项)
- `test_analytics.py` — 竞品分析 (16项)
- `test_scheduler.py` — 排期系统 (14项)
- `test_telegram.py` — Bot API (12项)
- `test_platforms.py` — 三平台客户端 (22项)

## 📄 License

MIT
