"""
Tests for content_moderator.py
"""
import pytest
from app.content_moderator import (
    ContentModerator,
    RiskLevel,
    ViolationType,
    Violation,
    ModerationResult,
)


@pytest.fixture
def moderator():
    return ContentModerator()


class TestContentModerator:
    """内容审核器测试"""
    
    def test_safe_content(self, moderator):
        """测试安全内容"""
        text = "今天天气真好，适合出去玩！"
        result = moderator.moderate(text)
        
        assert result.is_safe is True
        assert result.risk_score == 0
        assert result.risk_level == RiskLevel.SAFE
        assert len(result.violations) == 0
        assert "✅ 内容安全" in result.suggestions[0]
    
    def test_sexual_content(self, moderator):
        """测试色情内容"""
        text = "这是一个色情网站，快来看裸体照片"
        result = moderator.moderate(text)
        
        assert result.is_safe is False
        assert result.risk_score >= 38
        assert len(result.violations) >= 2
        assert any(v.type == ViolationType.SEXUAL for v in result.violations)
    
    def test_violence_content(self, moderator):
        """测试暴力内容"""
        text = "教你如何杀人不被发现，血腥场面"
        result = moderator.moderate(text)
        
        assert result.is_safe is False
        assert len(result.violations) >= 2
        assert any(v.type == ViolationType.VIOLENCE for v in result.violations)
    
    def test_illegal_content(self, moderator):
        """测试违禁品"""
        text = "出售大麻、海洛因，支持比特币支付"
        result = moderator.moderate(text)
        
        assert result.is_safe is False
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert any(v.type == ViolationType.ILLEGAL for v in result.violations)
    
    def test_advertising_violations(self, moderator):
        """测试广告法违规"""
        text = "国家级品质，世界第一，最佳选择！"
        result = moderator.moderate(text)
        
        assert len(result.violations) >= 3
        assert all(v.type == ViolationType.ADVERTISING for v in result.violations)
        assert result.cleaned_text is not None
        assert "***" in result.cleaned_text
    
    def test_platform_violations(self, moderator):
        """测试平台规则违规"""
        text = "加微信：abc123，私聊我获取更多信息"
        result = moderator.moderate(text)
        
        assert len(result.violations) >= 2
        assert any(v.type == ViolationType.PLATFORM for v in result.violations)
    
    def test_spam_content(self, moderator):
        """测试垃圾信息"""
        text = "免费领取！限时优惠！点击领取！立即抢购！"
        result = moderator.moderate(text)
        
        assert len(result.violations) >= 4
        assert all(v.type == ViolationType.SPAM for v in result.violations)
    
    def test_personal_info_phone(self, moderator):
        """测试手机号检测"""
        text = "联系我：13800138000"
        result = moderator.moderate(text)
        
        assert len(result.violations) >= 1
        assert any(v.type == ViolationType.PERSONAL_INFO for v in result.violations)
        assert "手机号" in result.violations[0].suggestion
    
    def test_personal_info_email(self, moderator):
        """测试邮箱检测"""
        text = "发送简历到 test@example.com"
        result = moderator.moderate(text)
        
        assert len(result.violations) >= 1
        assert any(v.type == ViolationType.PERSONAL_INFO for v in result.violations)
    
    def test_risk_score_calculation(self, moderator):
        """测试风险分数计算"""
        # 低风险
        text1 = "这是最佳产品"
        result1 = moderator.moderate(text1)
        assert result1.risk_level in [RiskLevel.SAFE, RiskLevel.LOW]
        
        # 中风险
        text2 = "最佳产品，第一品牌，加微信购买"
        result2 = moderator.moderate(text2)
        assert result2.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        
        # 高风险
        text3 = "色情暴力内容，出售毒品"
        result3 = moderator.moderate(text3)
        assert result3.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def test_risk_levels(self, moderator):
        """测试风险等级分类"""
        assert moderator._get_risk_level(10) == RiskLevel.SAFE
        assert moderator._get_risk_level(30) == RiskLevel.LOW
        assert moderator._get_risk_level(50) == RiskLevel.MEDIUM
        assert moderator._get_risk_level(70) == RiskLevel.HIGH
        assert moderator._get_risk_level(90) == RiskLevel.CRITICAL
    
    def test_suggestions_generation(self, moderator):
        """测试建议生成"""
        text = "最佳产品，加微信，免费领取"
        result = moderator.moderate(text)
        
        assert len(result.suggestions) > 0
        assert any("广告法" in s for s in result.suggestions)
        assert any("平台规则" in s for s in result.suggestions)
        assert any("垃圾营销" in s for s in result.suggestions)
    
    def test_platform_specific_suggestions(self, moderator):
        """测试平台特定建议"""
        text = "普通内容"
        
        result_ig = moderator.moderate(text, platform="instagram")
        assert any("Instagram" in s for s in result_ig.suggestions)
        
        result_tw = moderator.moderate(text, platform="twitter")
        assert any("Twitter" in s for s in result_tw.suggestions)
        
        result_tt = moderator.moderate(text, platform="tiktok")
        assert any("TikTok" in s for s in result_tt.suggestions)
    
    def test_text_cleaning(self, moderator):
        """测试文本清理"""
        text = "这是最佳产品，加微信：abc123，手机：13800138000"
        result = moderator.moderate(text)
        
        assert result.cleaned_text is not None
        assert "最佳" not in result.cleaned_text
        assert "加微信" not in result.cleaned_text
        assert "13800138000" not in result.cleaned_text
        assert "***" in result.cleaned_text
    
    def test_high_risk_no_cleaning(self, moderator):
        """测试高风险内容不自动清理"""
        text = "色情暴力内容，出售毒品"
        result = moderator.moderate(text)
        
        # 高风险内容不提供自动清理
        assert result.risk_score >= 50
        # 高危内容也会清理，但不应发布
        assert result.is_safe is False
    
    def test_batch_moderate(self, moderator):
        """测试批量审核"""
        texts = [
            "安全内容",
            "最佳产品",
            "色情内容",
        ]
        results = moderator.batch_moderate(texts)
        
        assert len(results) == 3
        assert results[0].is_safe is True
        assert results[1].is_safe is True  # 广告法违规但风险低
        assert results[2].is_safe is False
    
    def test_get_stats(self, moderator):
        """测试统计功能"""
        texts = [
            "安全内容1",
            "安全内容2",
            "最佳产品",
            "色情内容",
        ]
        results = moderator.batch_moderate(texts)
        stats = moderator.get_stats(results)
        
        assert stats["total"] == 4
        assert stats["safe"] >= 2
        assert stats["unsafe"] >= 1
        assert 0 <= stats["safe_rate"] <= 1
        assert "by_level" in stats
        assert "by_type" in stats
    
    def test_violation_position(self, moderator):
        """测试违规位置记录"""
        text = "前面的内容，色情关键词，后面的内容"
        result = moderator.moderate(text)
        
        violation = result.violations[0]
        assert violation.position >= 0
        assert text[violation.position:violation.position+len(violation.keyword)] == violation.keyword
    
    def test_violation_severity(self, moderator):
        """测试违规严重度"""
        text = "色情暴力毒品"
        result = moderator.moderate(text)
        
        for v in result.violations:
            assert 1 <= v.severity <= 10
            if v.type in [ViolationType.POLITICAL, ViolationType.ILLEGAL]:
                assert v.severity >= 9
    
    def test_empty_text(self, moderator):
        """测试空文本"""
        result = moderator.moderate("")
        
        assert result.is_safe is True
        assert result.risk_score == 0
        assert len(result.violations) == 0
    
    def test_mixed_violations(self, moderator):
        """测试混合违规"""
        text = "最佳产品，色情内容，加微信，出售毒品，手机13800138000"
        result = moderator.moderate(text)
        
        # 应该检测到多种违规类型
        violation_types = {v.type for v in result.violations}
        assert len(violation_types) >= 4
        assert ViolationType.ADVERTISING in violation_types
        assert ViolationType.SEXUAL in violation_types
        assert ViolationType.PLATFORM in violation_types
        assert ViolationType.ILLEGAL in violation_types
    
    def test_suggestion_content(self, moderator):
        """测试建议内容"""
        text = "最佳产品"
        result = moderator.moderate(text)
        
        violation = result.violations[0]
        assert violation.suggestion is not None
        assert "最佳" in violation.suggestion
        assert "替换" in violation.suggestion or "移除" in violation.suggestion


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
