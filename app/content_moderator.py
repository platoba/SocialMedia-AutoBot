"""
Content Moderator — 内容审核引擎
- 敏感词检测 (政治/色情/暴力/违禁品)
- 合规检测 (广告法/平台规则)
- 风险评分 (0-100)
- 自动修正建议
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"           # 0-20
    LOW = "low"             # 21-40
    MEDIUM = "medium"       # 41-60
    HIGH = "high"           # 61-80
    CRITICAL = "critical"   # 81-100


class ViolationType(Enum):
    """违规类型"""
    POLITICAL = "political"         # 政治敏感
    SEXUAL = "sexual"               # 色情低俗
    VIOLENCE = "violence"           # 暴力血腥
    ILLEGAL = "illegal"             # 违禁品
    ADVERTISING = "advertising"     # 广告法违规
    PLATFORM = "platform"           # 平台规则
    SPAM = "spam"                   # 垃圾信息
    PERSONAL_INFO = "personal_info" # 个人信息泄露


@dataclass
class Violation:
    """违规项"""
    type: ViolationType
    keyword: str
    position: int
    severity: int  # 1-10
    suggestion: Optional[str] = None


@dataclass
class ModerationResult:
    """审核结果"""
    is_safe: bool
    risk_score: int  # 0-100
    risk_level: RiskLevel
    violations: List[Violation]
    suggestions: List[str]
    cleaned_text: Optional[str] = None


class ContentModerator:
    """内容审核器"""
    
    # 敏感词库 (示例，实际应从外部加载)
    POLITICAL_KEYWORDS = [
        "政治敏感词1", "政治敏感词2",  # 占位符
    ]
    
    SEXUAL_KEYWORDS = [
        "色情", "裸体", "性交", "约炮", "援交",
        "成人", "黄色", "情色", "激情", "诱惑",
    ]
    
    VIOLENCE_KEYWORDS = [
        "杀人", "自杀", "血腥", "暴力", "恐怖",
        "虐待", "伤害", "死亡", "尸体", "枪支",
    ]
    
    ILLEGAL_KEYWORDS = [
        "毒品", "大麻", "海洛因", "冰毒", "摇头丸",
        "赌博", "博彩", "六合彩", "私彩", "黑彩",
        "假币", "假钞", "洗钱", "走私", "贩卖",
    ]
    
    # 广告法违禁词
    ADVERTISING_KEYWORDS = [
        "国家级", "世界级", "最高级", "最佳", "最大",
        "第一", "唯一", "首个", "首选", "顶级",
        "极品", "王牌", "冠军", "领袖", "领导品牌",
        "填补国内空白", "绝对", "独家", "首家", "最新技术",
    ]
    
    # 平台规则违规
    PLATFORM_KEYWORDS = [
        "加微信", "加QQ", "私聊", "联系方式", "电话",
        "外链", "跳转", "下载", "点击链接", "扫码",
    ]
    
    # 垃圾信息
    SPAM_KEYWORDS = [
        "免费领取", "限时优惠", "点击领取", "立即抢购",
        "不转不是中国人", "转发有奖", "集赞", "砍价",
    ]
    
    # 个人信息模式
    PERSONAL_INFO_PATTERNS = [
        (r'\d{11}', "手机号"),
        (r'\d{15}|\d{18}', "身份证号"),
        (r'\d{3,4}-\d{7,8}', "座机号"),
        (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "邮箱"),
    ]
    
    # 高危类型 (严重违规)
    CRITICAL_TYPES = {
        ViolationType.POLITICAL,
        ViolationType.SEXUAL,
        ViolationType.VIOLENCE,
        ViolationType.ILLEGAL,
    }
    
    def __init__(self):
        """初始化"""
        self.keyword_map = {
            ViolationType.POLITICAL: (self.POLITICAL_KEYWORDS, 10),
            ViolationType.SEXUAL: (self.SEXUAL_KEYWORDS, 9),
            ViolationType.VIOLENCE: (self.VIOLENCE_KEYWORDS, 8),
            ViolationType.ILLEGAL: (self.ILLEGAL_KEYWORDS, 10),
            ViolationType.ADVERTISING: (self.ADVERTISING_KEYWORDS, 5),
            ViolationType.PLATFORM: (self.PLATFORM_KEYWORDS, 6),
            ViolationType.SPAM: (self.SPAM_KEYWORDS, 4),
        }
    
    def moderate(self, text: str, platform: str = "general") -> ModerationResult:
        """
        审核文本
        
        Args:
            text: 待审核文本
            platform: 平台 (instagram/twitter/tiktok/general)
        
        Returns:
            ModerationResult
        """
        violations = []
        
        # 1. 关键词检测
        for vtype, (keywords, severity) in self.keyword_map.items():
            for keyword in keywords:
                if keyword in text:
                    pos = text.find(keyword)
                    suggestion = self._get_suggestion(vtype, keyword)
                    violations.append(Violation(
                        type=vtype,
                        keyword=keyword,
                        position=pos,
                        severity=severity,
                        suggestion=suggestion
                    ))
        
        # 2. 个人信息检测
        for pattern, info_type in self.PERSONAL_INFO_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.PERSONAL_INFO,
                    keyword=match.group(),
                    position=match.start(),
                    severity=7,
                    suggestion=f"移除{info_type}或用***代替"
                ))
        
        # 3. 计算风险分数
        risk_score = self._calculate_risk_score(violations)
        risk_level = self._get_risk_level(risk_score)
        
        # 4. 判断是否安全 (有高危违规即不安全)
        has_critical = any(v.type in self.CRITICAL_TYPES for v in violations)
        is_safe = not has_critical and risk_score < 40
        
        # 5. 生成建议
        suggestions = self._generate_suggestions(violations, platform)
        
        # 6. 自动清理 (仅低风险)
        cleaned_text = None
        if risk_score < 60:
            cleaned_text = self._clean_text(text, violations)
        
        return ModerationResult(
            is_safe=is_safe,
            risk_score=risk_score,
            risk_level=risk_level,
            violations=violations,
            suggestions=suggestions,
            cleaned_text=cleaned_text
        )
    
    def _calculate_risk_score(self, violations: List[Violation]) -> int:
        """计算风险分数"""
        if not violations:
            return 0
        
        # 基础分数 = 违规项数量 * 10
        base_score = min(len(violations) * 10, 50)
        
        # 严重度加权
        severity_score = sum(v.severity for v in violations)
        
        # 总分 = 基础分 + 严重度分
        total = min(base_score + severity_score, 100)
        return total
    
    def _get_risk_level(self, score: int) -> RiskLevel:
        """获取风险等级"""
        if score <= 20:
            return RiskLevel.SAFE
        elif score <= 40:
            return RiskLevel.LOW
        elif score <= 60:
            return RiskLevel.MEDIUM
        elif score <= 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _get_suggestion(self, vtype: ViolationType, keyword: str) -> str:
        """获取修正建议"""
        suggestions_map = {
            ViolationType.POLITICAL: f"移除政治敏感词 '{keyword}'",
            ViolationType.SEXUAL: f"移除色情低俗内容 '{keyword}'",
            ViolationType.VIOLENCE: f"移除暴力血腥内容 '{keyword}'",
            ViolationType.ILLEGAL: f"移除违禁品信息 '{keyword}'",
            ViolationType.ADVERTISING: f"替换广告法违禁词 '{keyword}' (如: 最佳→优质, 第一→领先)",
            ViolationType.PLATFORM: f"移除联系方式/外链 '{keyword}'",
            ViolationType.SPAM: f"移除垃圾营销内容 '{keyword}'",
        }
        return suggestions_map.get(vtype, f"移除违规内容 '{keyword}'")
    
    def _generate_suggestions(self, violations: List[Violation], platform: str) -> List[str]:
        """生成综合建议"""
        if not violations:
            suggestions = ["✅ 内容安全，可以发布"]
        else:
            suggestions = []
            
            # 按类型分组
            by_type = {}
            for v in violations:
                by_type.setdefault(v.type, []).append(v)
            
            # 生成建议
            for vtype, items in by_type.items():
                count = len(items)
                if vtype == ViolationType.ADVERTISING:
                    suggestions.append(f"⚠️ 发现 {count} 处广告法违规，建议替换为合规表述")
                elif vtype == ViolationType.PLATFORM:
                    suggestions.append(f"⚠️ 发现 {count} 处平台规则违规 (联系方式/外链)，建议移除")
                elif vtype == ViolationType.SPAM:
                    suggestions.append(f"⚠️ 发现 {count} 处垃圾营销内容，建议优化文案")
                elif vtype == ViolationType.PERSONAL_INFO:
                    suggestions.append(f"⚠️ 发现 {count} 处个人信息泄露，建议脱敏处理")
                else:
                    suggestions.append(f"🚫 发现 {count} 处 {vtype.value} 违规，必须移除")
        
        # 平台特定建议
        if platform == "instagram":
            suggestions.append("💡 Instagram: 避免过多标签 (建议≤30个)")
        elif platform == "twitter":
            suggestions.append("💡 Twitter: 注意字数限制 (280字符)")
        elif platform == "tiktok":
            suggestions.append("💡 TikTok: 避免敏感话题，多用正能量内容")
        
        return suggestions
    
    def _clean_text(self, text: str, violations: List[Violation]) -> str:
        """自动清理文本 (仅处理低风险违规)"""
        cleaned = text
        
        # 只处理广告法、平台规则、垃圾信息
        safe_types = {
            ViolationType.ADVERTISING,
            ViolationType.PLATFORM,
            ViolationType.SPAM,
        }
        
        for v in violations:
            if v.type in safe_types:
                # 简单替换为 ***
                cleaned = cleaned.replace(v.keyword, "***")
        
        # 移除个人信息
        for pattern, _ in self.PERSONAL_INFO_PATTERNS:
            cleaned = re.sub(pattern, "***", cleaned)
        
        return cleaned
    
    def batch_moderate(self, texts: List[str], platform: str = "general") -> List[ModerationResult]:
        """批量审核"""
        return [self.moderate(text, platform) for text in texts]
    
    def get_stats(self, results: List[ModerationResult]) -> Dict:
        """统计审核结果"""
        total = len(results)
        safe = sum(1 for r in results if r.is_safe)
        
        by_level = {level: 0 for level in RiskLevel}
        for r in results:
            by_level[r.risk_level] += 1
        
        by_type = {}
        for r in results:
            for v in r.violations:
                by_type[v.type.value] = by_type.get(v.type.value, 0) + 1
        
        return {
            "total": total,
            "safe": safe,
            "unsafe": total - safe,
            "safe_rate": safe / total if total > 0 else 0,
            "by_level": {k.value: v for k, v in by_level.items()},
            "by_type": by_type,
        }
