"""A/B Testing Framework for Social Media Content.

Test different content variants (captions, hashtags, posting times, visuals)
and track which combinations drive the most engagement.

Features:
- Create experiments with multiple variants
- Track metrics per variant
- Statistical significance testing (chi-squared / z-test)
- Auto-winner selection
- Experiment history with SQLite persistence
- Multi-metric optimization (engagement, reach, conversions)
"""

import json
import math
import sqlite3
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    ENGAGEMENT_RATE = "engagement_rate"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    SAVES = "saves"
    CLICKS = "clicks"
    REACH = "reach"
    IMPRESSIONS = "impressions"
    CONVERSIONS = "conversions"
    CTR = "ctr"  # click-through rate


class VariantType(str, Enum):
    CAPTION = "caption"
    HASHTAG_SET = "hashtag_set"
    POSTING_TIME = "posting_time"
    CONTENT_TYPE = "content_type"
    VISUAL_STYLE = "visual_style"
    CTA = "cta"
    HOOK = "hook"


@dataclass
class Variant:
    """A single variant in an A/B test."""
    id: str
    name: str
    variant_type: VariantType
    content: str
    metrics: dict[str, float] = field(default_factory=dict)
    sample_size: int = 0
    is_control: bool = False

    def add_metric(self, metric: MetricType, value: float):
        key = metric.value
        if key not in self.metrics:
            self.metrics[key] = 0.0
        # Running average
        old_total = self.metrics[key] * max(self.sample_size - 1, 0)
        self.metrics[key] = (old_total + value) / max(self.sample_size, 1)

    def get_metric(self, metric: MetricType) -> float:
        return self.metrics.get(metric.value, 0.0)


@dataclass
class ExperimentResult:
    """Result of an A/B test experiment."""
    experiment_id: str
    experiment_name: str
    winner_id: Optional[str]
    winner_name: Optional[str]
    primary_metric: MetricType
    confidence: float  # 0-100%
    is_significant: bool
    lift_percent: float  # % improvement over control
    variant_results: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"🧪 实验结果: {self.experiment_name}",
            f"📊 主指标: {self.primary_metric.value}",
            "",
        ]
        if self.is_significant and self.winner_id:
            lines.append(f"🏆 赢家: {self.winner_name}")
            lines.append(f"📈 提升: +{self.lift_percent:.1f}%")
            lines.append(f"🎯 置信度: {self.confidence:.1f}%")
        else:
            lines.append("⚠️ 结果不显著 — 需要更多数据")
            lines.append(f"当前置信度: {self.confidence:.1f}% (需 ≥95%)")

        lines.append("")
        lines.append("📋 各变体表现:")
        for vr in self.variant_results:
            ctrl = " (control)" if vr.get("is_control") else ""
            lines.append(
                f"  {'🔵' if vr.get('is_control') else '🔴'} {vr['name']}{ctrl}: "
                f"{vr.get('metric_value', 0):.2f} (n={vr.get('sample_size', 0)})"
            )

        if self.recommendations:
            lines.append("")
            lines.append("💡 建议:")
            for r in self.recommendations:
                lines.append(f"  • {r}")

        return "\n".join(lines)


class ABTestEngine:
    """A/B Testing engine with SQLite persistence."""

    def __init__(self, db_path: str = "data/ab_tests.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                primary_metric TEXT DEFAULT 'engagement_rate',
                status TEXT DEFAULT 'draft',
                min_sample_size INTEGER DEFAULT 100,
                confidence_threshold REAL DEFAULT 95.0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS variants (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                name TEXT NOT NULL,
                variant_type TEXT NOT NULL,
                content TEXT DEFAULT '',
                is_control INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            );

            CREATE TABLE IF NOT EXISTS variant_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                recorded_at TEXT NOT NULL,
                post_id TEXT DEFAULT '',
                FOREIGN KEY (variant_id) REFERENCES variants(id)
            );

            CREATE INDEX IF NOT EXISTS idx_variants_experiment
                ON variants(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_variant
                ON variant_metrics(variant_id, metric_type);
        """)
        self.db.commit()

    def create_experiment(
        self,
        name: str,
        platform: str,
        primary_metric: MetricType = MetricType.ENGAGEMENT_RATE,
        min_sample_size: int = 100,
        confidence_threshold: float = 95.0,
        notes: str = "",
    ) -> str:
        """Create a new A/B test experiment."""
        import hashlib
        exp_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        self.db.execute(
            "INSERT INTO experiments (id, name, platform, primary_metric, "
            "min_sample_size, confidence_threshold, created_at, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (exp_id, name, platform, primary_metric.value,
             min_sample_size, confidence_threshold,
             datetime.now().isoformat(), notes)
        )
        self.db.commit()
        return exp_id

    def add_variant(
        self,
        experiment_id: str,
        name: str,
        variant_type: VariantType,
        content: str,
        is_control: bool = False,
    ) -> str:
        """Add a variant to an experiment."""
        import hashlib
        var_id = hashlib.md5(
            f"{experiment_id}{name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        self.db.execute(
            "INSERT INTO variants (id, experiment_id, name, variant_type, content, is_control) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (var_id, experiment_id, name, variant_type.value, content, int(is_control))
        )
        self.db.commit()
        return var_id

    def start_experiment(self, experiment_id: str) -> str:
        """Start an experiment."""
        variants = self.db.execute(
            "SELECT COUNT(*) as cnt FROM variants WHERE experiment_id=?",
            (experiment_id,)
        ).fetchone()

        if not variants or variants["cnt"] < 2:
            return "❌ 至少需要2个变体才能开始实验"

        control = self.db.execute(
            "SELECT COUNT(*) as cnt FROM variants "
            "WHERE experiment_id=? AND is_control=1",
            (experiment_id,)
        ).fetchone()

        if not control or control["cnt"] == 0:
            return "❌ 需要指定一个控制组(control)"

        self.db.execute(
            "UPDATE experiments SET status=?, started_at=? WHERE id=?",
            (ExperimentStatus.RUNNING.value, datetime.now().isoformat(), experiment_id)
        )
        self.db.commit()
        return f"✅ 实验 {experiment_id} 已开始运行"

    def record_metric(
        self,
        variant_id: str,
        metric: MetricType,
        value: float,
        post_id: str = "",
    ):
        """Record a metric observation for a variant."""
        self.db.execute(
            "INSERT INTO variant_metrics (variant_id, metric_type, value, recorded_at, post_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (variant_id, metric.value, value, datetime.now().isoformat(), post_id)
        )
        # Update sample size
        self.db.execute(
            "UPDATE variants SET sample_size = sample_size + 1 WHERE id=?",
            (variant_id,)
        )
        self.db.commit()

    def get_results(self, experiment_id: str) -> ExperimentResult:
        """Analyze experiment results with statistical testing."""
        exp = self.db.execute(
            "SELECT * FROM experiments WHERE id=?", (experiment_id,)
        ).fetchone()

        if not exp:
            return ExperimentResult(
                experiment_id=experiment_id,
                experiment_name="Unknown",
                winner_id=None,
                winner_name=None,
                primary_metric=MetricType.ENGAGEMENT_RATE,
                confidence=0,
                is_significant=False,
                lift_percent=0,
            )

        primary_metric = MetricType(exp["primary_metric"])
        confidence_threshold = exp["confidence_threshold"]

        # Get variants and their metrics
        variants = self.db.execute(
            "SELECT * FROM variants WHERE experiment_id=? ORDER BY is_control DESC",
            (experiment_id,)
        ).fetchall()

        variant_data = []
        control_data = None

        for v in variants:
            metrics = self.db.execute(
                "SELECT AVG(value) as avg_val, COUNT(*) as cnt "
                "FROM variant_metrics WHERE variant_id=? AND metric_type=?",
                (v["id"], primary_metric.value)
            ).fetchone()

            all_values = self.db.execute(
                "SELECT value FROM variant_metrics "
                "WHERE variant_id=? AND metric_type=? ORDER BY recorded_at",
                (v["id"], primary_metric.value)
            ).fetchall()

            vd = {
                "id": v["id"],
                "name": v["name"],
                "is_control": bool(v["is_control"]),
                "metric_value": metrics["avg_val"] or 0,
                "sample_size": metrics["cnt"] or 0,
                "values": [r["value"] for r in all_values],
            }
            variant_data.append(vd)

            if v["is_control"]:
                control_data = vd

        if not control_data or not variant_data:
            return ExperimentResult(
                experiment_id=experiment_id,
                experiment_name=exp["name"],
                winner_id=None,
                winner_name=None,
                primary_metric=primary_metric,
                confidence=0,
                is_significant=False,
                lift_percent=0,
                variant_results=variant_data,
            )

        # Find best non-control variant
        non_control = [v for v in variant_data if not v["is_control"]]
        if not non_control:
            best = control_data
        else:
            best = max(non_control, key=lambda v: v["metric_value"])

        # Statistical significance test (z-test for proportions)
        confidence = 0.0
        is_significant = False
        lift = 0.0

        if control_data["sample_size"] > 0 and best["sample_size"] > 0:
            lift = _calculate_lift(control_data["metric_value"], best["metric_value"])
            confidence = _z_test_confidence(
                control_data["metric_value"],
                control_data["sample_size"],
                best["metric_value"],
                best["sample_size"],
            )
            is_significant = confidence >= confidence_threshold

        # If control is actually the best, check that
        winner_data = best
        if control_data["metric_value"] > best["metric_value"]:
            winner_data = control_data
            lift = 0  # Control won, no lift

        # Recommendations
        recommendations = _generate_recommendations(
            variant_data, control_data, is_significant, primary_metric
        )

        return ExperimentResult(
            experiment_id=experiment_id,
            experiment_name=exp["name"],
            winner_id=winner_data["id"] if is_significant else None,
            winner_name=winner_data["name"] if is_significant else None,
            primary_metric=primary_metric,
            confidence=confidence,
            is_significant=is_significant,
            lift_percent=lift,
            variant_results=variant_data,
            recommendations=recommendations,
        )

    def list_experiments(self, status: Optional[ExperimentStatus] = None) -> str:
        """List experiments with optional status filter."""
        if status:
            rows = self.db.execute(
                "SELECT * FROM experiments WHERE status=? ORDER BY created_at DESC",
                (status.value,)
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM experiments ORDER BY created_at DESC LIMIT 20"
            ).fetchall()

        if not rows:
            return "🧪 暂无实验\n\n使用 /ab_create <名称> <平台> 创建新实验"

        status_emoji = {
            "draft": "📝", "running": "🔬", "paused": "⏸️",
            "completed": "✅", "cancelled": "🚫",
        }
        lines = [f"🧪 实验列表 ({len(rows)}个)\n"]
        for r in rows:
            emoji = status_emoji.get(r["status"], "❓")
            lines.append(
                f"  {emoji} [{r['id']}] {r['name']} ({r['platform']}) — {r['status']}"
            )
        return "\n".join(lines)

    def complete_experiment(self, experiment_id: str) -> ExperimentResult:
        """Mark experiment as completed and return final results."""
        self.db.execute(
            "UPDATE experiments SET status=?, completed_at=? WHERE id=?",
            (ExperimentStatus.COMPLETED.value, datetime.now().isoformat(), experiment_id)
        )
        self.db.commit()
        return self.get_results(experiment_id)

    def delete_experiment(self, experiment_id: str) -> str:
        """Delete an experiment and all associated data."""
        # Get variant IDs first
        variants = self.db.execute(
            "SELECT id FROM variants WHERE experiment_id=?", (experiment_id,)
        ).fetchall()

        for v in variants:
            self.db.execute("DELETE FROM variant_metrics WHERE variant_id=?", (v["id"],))

        self.db.execute("DELETE FROM variants WHERE experiment_id=?", (experiment_id,))
        cur = self.db.execute("DELETE FROM experiments WHERE id=?", (experiment_id,))
        self.db.commit()

        if cur.rowcount:
            return f"✅ 实验 {experiment_id} 已删除"
        return f"⚠️ 未找到实验 {experiment_id}"

    def close(self):
        self.db.close()


def _calculate_lift(control_value: float, test_value: float) -> float:
    """Calculate lift percentage of test over control."""
    if control_value <= 0:
        return 0.0
    return ((test_value - control_value) / control_value) * 100


def _z_test_confidence(
    control_rate: float,
    control_n: int,
    test_rate: float,
    test_n: int,
) -> float:
    """Perform z-test for two proportions and return confidence level.

    Treats rates as proportions (0-100 scale → 0-1 scale).
    """
    if control_n < 2 or test_n < 2:
        return 0.0

    # Convert percentage rates to proportions
    p1 = min(control_rate / 100.0, 1.0)
    p2 = min(test_rate / 100.0, 1.0)

    # Pooled proportion
    p_pool = (p1 * control_n + p2 * test_n) / (control_n + test_n)

    if p_pool <= 0 or p_pool >= 1:
        return 0.0

    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1/control_n + 1/test_n))
    if se <= 0:
        return 0.0

    # Z-score
    z = abs(p2 - p1) / se

    # Convert z-score to confidence (approximate)
    # Using standard normal CDF approximation
    confidence = _z_to_confidence(z)
    return confidence


def _z_to_confidence(z: float) -> float:
    """Approximate conversion of z-score to confidence percentage."""
    # Common z-score to confidence mappings
    if z >= 3.29:
        return 99.9
    elif z >= 2.576:
        return 99.0
    elif z >= 2.326:
        return 98.0
    elif z >= 1.96:
        return 95.0
    elif z >= 1.645:
        return 90.0
    elif z >= 1.28:
        return 80.0
    elif z >= 1.036:
        return 70.0
    elif z >= 0.842:
        return 60.0
    elif z >= 0.674:
        return 50.0
    else:
        # Linear interpolation below 50%
        return max(0.0, z / 0.674 * 50.0)


def _generate_recommendations(
    variant_data: list[dict],
    control_data: dict,
    is_significant: bool,
    primary_metric: MetricType,
) -> list[str]:
    """Generate recommendations based on experiment results."""
    recs = []

    total_samples = sum(v["sample_size"] for v in variant_data)

    if not is_significant:
        min_needed = 100
        if total_samples < min_needed:
            recs.append(
                f"继续收集数据 — 当前 {total_samples} 样本, "
                f"建议至少 {min_needed} 样本/变体"
            )
        else:
            recs.append("差异不显著 — 两个变体表现类似, 选择成本更低的方案")

    # Check if any variant significantly underperforms
    for v in variant_data:
        if v["is_control"]:
            continue
        if control_data["metric_value"] > 0:
            diff = (v["metric_value"] - control_data["metric_value"]) / control_data["metric_value"]
            if diff < -0.2:
                recs.append(f"变体 '{v['name']}' 表现明显低于控制组 ({diff*100:.1f}%), 考虑停用")
            elif diff > 0.5:
                recs.append(f"变体 '{v['name']}' 表现优异 (+{diff*100:.1f}%), 建议全量采用")

    # Metric-specific suggestions
    if primary_metric == MetricType.ENGAGEMENT_RATE:
        recs.append("高互动内容要素: 提问、投票、争议观点、情绪共鸣")
    elif primary_metric == MetricType.CLICKS:
        recs.append("提升点击: 明确CTA、好奇心gap、紧迫感词汇")
    elif primary_metric == MetricType.SHARES:
        recs.append("促进分享: 实用价值、身份认同、社交货币")

    return recs
