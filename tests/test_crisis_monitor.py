"""
测试危机监测模块
"""
import pytest
from datetime import datetime
from app.crisis_monitor import CrisisMonitor, CrisisAlert

@pytest.fixture
def monitor():
    return CrisisMonitor(brand_keywords=['TestBrand', '测试品牌'])

@pytest.mark.asyncio
async def test_detect_negative_mention(monitor):
    """测试负面提及检测"""
    mentions = [{
        'content': 'TestBrand is a scam! Terrible product!',
        'author': '@user1',
        'engagement': 100,
        'author_followers': 1000
    }]
    
    alerts = await monitor.monitor_mentions('twitter', mentions)
    
    assert len(alerts) > 0
    assert alerts[0].severity in ['low', 'medium', 'high']
    assert 'scam' in alerts[0].keywords

@pytest.mark.asyncio
async def test_viral_negative_detection(monitor):
    """测试病毒式负面检测"""
    mentions = [{
        'content': 'TestBrand worst experience ever!',
        'author': '@viral_user',
        'engagement': 5000,  # 超过阈值
        'author_followers': 50000
    }]
    
    alerts = await monitor.monitor_mentions('instagram', mentions)
    
    assert len(alerts) > 0
    assert alerts[0].severity == 'critical'

@pytest.mark.asyncio
async def test_influencer_mention(monitor):
    """测试KOL提及"""
    mentions = [{
        'content': 'TestBrand is terrible and fake! Not impressed with quality',
        'author': '@big_influencer',
        'engagement': 500,
        'author_followers': 200000  # 大V
    }]
    
    alerts = await monitor.monitor_mentions('tiktok', mentions)
    
    assert len(alerts) > 0
    assert alerts[0].trigger_type == 'influencer_mention'
    assert alerts[0].severity == 'critical'

def test_sentiment_analysis(monitor):
    """测试情感分析"""
    positive = monitor._analyze_sentiment('Great product! Love TestBrand!')
    negative = monitor._analyze_sentiment('Scam! Fake! Terrible!')
    neutral = monitor._analyze_sentiment('TestBrand released new product')
    
    assert positive > 0
    assert negative < 0
    assert neutral == 0

def test_crisis_report(monitor):
    """测试危机报告生成"""
    # 添加模拟警报
    monitor.alerts = [
        CrisisAlert(
            platform='twitter',
            severity='high',
            trigger_type='negative_spike',
            content='Test alert',
            author='@user',
            url='',
            sentiment_score=-0.8,
            engagement=100,
            detected_at=datetime.now(),
            keywords=['scam']
        )
    ]
    
    report = monitor.get_crisis_report(hours=24)
    
    assert report['total_alerts'] == 1
    assert report['by_severity']['high'] == 1
    assert len(report['most_critical']) == 1

def test_response_suggestions(monitor):
    """测试响应建议"""
    critical_alert = CrisisAlert(
        platform='twitter',
        severity='critical',
        trigger_type='influencer_mention',
        content='Scam alert!',
        author='@influencer',
        url='',
        sentiment_score=-0.9,
        engagement=10000,
        detected_at=datetime.now(),
        keywords=['scam']
    )
    
    suggestions = monitor.get_response_suggestions(critical_alert)
    
    assert len(suggestions) > 0
    assert any('公关' in s for s in suggestions)
    assert any('私信' in s for s in suggestions)
