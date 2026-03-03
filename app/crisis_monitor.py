"""
社交媒体危机监测模块
实时监控品牌提及、负面评论、舆情预警
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import re

@dataclass
class CrisisAlert:
    """危机预警"""
    platform: str
    severity: str  # low, medium, high, critical
    trigger_type: str  # negative_spike, viral_negative, influencer_mention
    content: str
    author: str
    url: str
    sentiment_score: float
    engagement: int
    detected_at: datetime
    keywords: List[str]

class CrisisMonitor:
    """危机监测器"""
    
    # 负面关键词库
    NEGATIVE_KEYWORDS = {
        'scam', 'fraud', 'fake', 'terrible', 'worst', 'awful', 'horrible',
        '骗子', '假货', '垃圾', '差评', '退款', '投诉', '曝光'
    }
    
    # 危机阈值
    THRESHOLDS = {
        'negative_spike': 10,  # 1小时内负面提及数
        'viral_negative': 1000,  # 单条负面互动数
        'sentiment_drop': -0.5,  # 情感分数骤降
    }
    
    def __init__(self, brand_keywords: List[str]):
        self.brand_keywords = brand_keywords
        self.alerts: List[CrisisAlert] = []
        self.mention_history: List[Dict] = []
    
    async def monitor_mentions(
        self,
        platform: str,
        mentions: List[Dict]
    ) -> List[CrisisAlert]:
        """监控品牌提及"""
        new_alerts = []
        
        for mention in mentions:
            # 情感分析
            sentiment = self._analyze_sentiment(mention['content'])
            
            # 检测负面关键词
            negative_keywords = self._detect_negative_keywords(mention['content'])
            
            # 判断危机等级
            severity = self._assess_severity(
                sentiment=sentiment,
                engagement=mention.get('engagement', 0),
                keywords=negative_keywords,
                author_followers=mention.get('author_followers', 0)
            )
            
            if severity != 'none':
                alert = CrisisAlert(
                    platform=platform,
                    severity=severity,
                    trigger_type=self._determine_trigger_type(mention, sentiment),
                    content=mention['content'][:200],
                    author=mention['author'],
                    url=mention.get('url', ''),
                    sentiment_score=sentiment,
                    engagement=mention.get('engagement', 0),
                    detected_at=datetime.now(),
                    keywords=negative_keywords
                )
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        # 检测负面激增
        spike_alerts = self._detect_negative_spike(platform)
        new_alerts.extend(spike_alerts)
        
        return new_alerts
    
    def _analyze_sentiment(self, text: str) -> float:
        """简单情感分析 (-1.0 到 1.0)"""
        text_lower = text.lower()
        
        # 负面词计数
        negative_count = sum(1 for word in self.NEGATIVE_KEYWORDS if word in text_lower)
        
        # 正面词
        positive_words = {'great', 'love', 'amazing', 'excellent', 'perfect', '好评', '推荐', '满意'}
        positive_count = sum(1 for word in positive_words if word in text_lower)
        
        # 简单计算
        total = negative_count + positive_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _detect_negative_keywords(self, text: str) -> List[str]:
        """检测负面关键词"""
        text_lower = text.lower()
        return [kw for kw in self.NEGATIVE_KEYWORDS if kw in text_lower]
    
    def _assess_severity(
        self,
        sentiment: float,
        engagement: int,
        keywords: List[str],
        author_followers: int
    ) -> str:
        """评估危机严重程度"""
        if sentiment >= -0.3:
            return 'none'
        
        # 高影响力账号 + 负面
        if author_followers > 100000 and sentiment < -0.5:
            return 'critical'
        
        # 病毒式传播负面
        if engagement > self.THRESHOLDS['viral_negative']:
            return 'critical'
        
        # 多个负面关键词
        if len(keywords) >= 3:
            return 'high'
        
        # 中等负面
        if sentiment < -0.5 or engagement > 500:
            return 'medium'
        
        return 'low'
    
    def _determine_trigger_type(self, mention: Dict, sentiment: float) -> str:
        """判断触发类型"""
        engagement = mention.get('engagement', 0)
        followers = mention.get('author_followers', 0)
        
        if followers > 50000:
            return 'influencer_mention'
        
        if engagement > self.THRESHOLDS['viral_negative']:
            return 'viral_negative'
        
        return 'negative_spike'
    
    def _detect_negative_spike(self, platform: str) -> List[CrisisAlert]:
        """检测负面激增"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        recent_negatives = [
            a for a in self.alerts
            if a.platform == platform
            and a.detected_at > one_hour_ago
            and a.sentiment_score < -0.3
        ]
        
        if len(recent_negatives) >= self.THRESHOLDS['negative_spike']:
            return [CrisisAlert(
                platform=platform,
                severity='high',
                trigger_type='negative_spike',
                content=f'过去1小时检测到{len(recent_negatives)}条负面提及',
                author='系统检测',
                url='',
                sentiment_score=-0.7,
                engagement=0,
                detected_at=datetime.now(),
                keywords=['负面激增']
            )]
        
        return []
    
    def get_crisis_report(self, hours: int = 24) -> Dict:
        """生成危机报告"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alerts if a.detected_at > cutoff]
        
        return {
            'total_alerts': len(recent_alerts),
            'by_severity': {
                'critical': len([a for a in recent_alerts if a.severity == 'critical']),
                'high': len([a for a in recent_alerts if a.severity == 'high']),
                'medium': len([a for a in recent_alerts if a.severity == 'medium']),
                'low': len([a for a in recent_alerts if a.severity == 'low']),
            },
            'by_platform': {},
            'top_keywords': self._get_top_keywords(recent_alerts),
            'most_critical': sorted(
                recent_alerts,
                key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x.severity],
                reverse=True
            )[:5]
        }
    
    def _get_top_keywords(self, alerts: List[CrisisAlert]) -> List[tuple]:
        """获取高频负面关键词"""
        keyword_counts = {}
        for alert in alerts:
            for kw in alert.keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        return sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    def get_response_suggestions(self, alert: CrisisAlert) -> List[str]:
        """危机响应建议"""
        suggestions = []
        
        if alert.severity == 'critical':
            suggestions.append('🚨 立即通知公关团队')
            suggestions.append('📞 准备官方声明')
            suggestions.append('👥 联系法务评估')
        
        if alert.trigger_type == 'influencer_mention':
            suggestions.append('🤝 尝试私信沟通')
            suggestions.append('📧 发送官方邮件说明')
        
        if 'scam' in alert.keywords or '骗子' in alert.keywords:
            suggestions.append('🔍 核实事实真相')
            suggestions.append('📝 准备澄清说明')
        
        suggestions.append('📊 监控后续发酵情况')
        suggestions.append('💬 准备客服话术')
        
        return suggestions

# 使用示例
async def example_usage():
    monitor = CrisisMonitor(brand_keywords=['MyBrand', '我的品牌'])
    
    # 模拟监控数据
    mentions = [
        {
            'content': 'This MyBrand product is a total scam! Terrible quality!',
            'author': '@angry_customer',
            'engagement': 1500,
            'author_followers': 5000,
            'url': 'https://twitter.com/...'
        }
    ]
    
    alerts = await monitor.monitor_mentions('twitter', mentions)
    
    for alert in alerts:
        print(f"🚨 {alert.severity.upper()} - {alert.platform}")
        print(f"   {alert.content}")
        print(f"   建议: {monitor.get_response_suggestions(alert)}")
