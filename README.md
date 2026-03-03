# SocialMedia-AutoBot v4.0

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

## 🛡️ v4.0 新增：内容审核引擎

### 功能特性
- **8类违规检测**
  - 政治敏感 / 色情低俗 / 暴力血腥 / 违禁品
  - 广告法违规 / 平台规则 / 垃圾信息 / 个人信息泄露
- **风险评分系统** (0-100分，5级风险等级)
- **智能建议生成** (分类建议+平台特定提示)
- **自动文本清理** (低风险违规自动修正)
- **批量审核** + **统计分析**

### 使用示例
```python
from app.content_moderator import ContentModerator

moderator = ContentModerator()

# 单条审核
result = moderator.moderate("这是最佳产品，加微信购买", platform="instagram")
print(f"安全: {result.is_safe}, 风险分: {result.risk_score}")
print(f"建议: {result.suggestions}")
print(f"清理后: {result.cleaned_text}")

# 批量审核
texts = ["文案1", "文案2", "文案3"]
results = moderator.batch_moderate(texts, platform="tiktok")
stats = moderator.get_stats(results)
print(f"安全率: {stats['safe_rate']:.1%}")
```

### TG Bot 命令
| 命令 | 说明 |
|------|------|
| `/moderate <文本>` | 审核单条内容 |
| `/moderate_batch` | 批量审核 (发送多行文本) |

### 测试覆盖
- 22项测试 (敏感词/合规/风险评分/建议生成/清理/统计)
- 100% 通过率

## 🆕 v5.0 新功能 - 危机监测

### 🚨 社交媒体危机监测
实时监控品牌提及、负面评论、舆情预警，帮助品牌快速响应危机。

**核心功能:**
- **负面情感检测** — 自动识别负面关键词和情感倾向
- **病毒式传播预警** — 监控高互动负面内容
- **KOL提及追踪** — 重点关注大V账号的品牌评价
- **负面激增检测** — 1小时内负面提及数超过阈值自动报警
- **危机等级评估** — Critical/High/Medium/Low 四级分类
- **响应建议** — 根据危机类型提供处理建议

**使用方法:**
```bash
/crisis              # 查看24小时危机报告
/monitor 品牌名      # 启动实时监控
```

**危机等级判定:**
- 🔴 **Critical** — 大V负面提及 或 病毒式传播负面内容
- 🟠 **High** — 多个负面关键词 或 负面激增
- 🟡 **Medium** — 中等负面情感 或 较高互动
- 🟢 **Low** — 轻微负面提及

**响应建议示例:**
- 🚨 立即通知公关团队
- 📞 准备官方声明
- 🤝 尝试私信沟通
- 🔍 核实事实真相
- 📊 监控后续发酵情况

