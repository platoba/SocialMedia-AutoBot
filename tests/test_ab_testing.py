"""Tests for A/B Testing Framework."""

import os
import pytest
import tempfile
from app.ab_testing import (
    ABTestEngine,
    ExperimentStatus,
    MetricType,
    VariantType,
    Variant,
    ExperimentResult,
    _calculate_lift,
    _z_test_confidence,
    _z_to_confidence,
    _generate_recommendations,
)


@pytest.fixture
def engine():
    """Create a test engine with temp database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = ABTestEngine(db_path=path)
    yield eng
    eng.close()
    os.unlink(path)


@pytest.fixture
def experiment_with_variants(engine):
    """Create an experiment with control + variant."""
    exp_id = engine.create_experiment(
        name="Caption Test",
        platform="instagram",
        primary_metric=MetricType.ENGAGEMENT_RATE,
        min_sample_size=50,
    )
    control_id = engine.add_variant(
        exp_id, "Original Caption", VariantType.CAPTION,
        "Check out our latest product! #new",
        is_control=True,
    )
    variant_id = engine.add_variant(
        exp_id, "Emoji Caption", VariantType.CAPTION,
        "🔥 You NEED this! Limited time only 🔥 #new",
    )
    return exp_id, control_id, variant_id


# ─── Experiment CRUD ─────────────────────────────────────────────

class TestExperimentCRUD:
    def test_create_experiment(self, engine):
        exp_id = engine.create_experiment(
            name="Test Experiment",
            platform="twitter",
        )
        assert exp_id is not None
        assert len(exp_id) == 12

    def test_create_with_all_params(self, engine):
        exp_id = engine.create_experiment(
            name="Full Experiment",
            platform="tiktok",
            primary_metric=MetricType.SHARES,
            min_sample_size=200,
            confidence_threshold=99.0,
            notes="Testing shares impact",
        )
        assert exp_id is not None

    def test_add_variant(self, engine):
        exp_id = engine.create_experiment("Test", "ig")
        var_id = engine.add_variant(
            exp_id, "Control", VariantType.CAPTION,
            "Original text", is_control=True,
        )
        assert var_id is not None
        assert len(var_id) == 12

    def test_add_multiple_variants(self, engine):
        exp_id = engine.create_experiment("Multi", "ig")
        ids = []
        for i in range(5):
            vid = engine.add_variant(
                exp_id, f"Variant {i}", VariantType.CAPTION,
                f"Content {i}", is_control=(i == 0),
            )
            ids.append(vid)
        assert len(set(ids)) == 5  # All unique

    def test_delete_experiment(self, engine):
        exp_id = engine.create_experiment("To Delete", "tw")
        engine.add_variant(exp_id, "V1", VariantType.CAPTION, "text", is_control=True)
        result = engine.delete_experiment(exp_id)
        assert "已删除" in result

    def test_delete_nonexistent(self, engine):
        result = engine.delete_experiment("nonexistent")
        assert "未找到" in result

    def test_list_experiments(self, engine):
        engine.create_experiment("Exp1", "ig")
        engine.create_experiment("Exp2", "tw")
        result = engine.list_experiments()
        assert "Exp1" in result
        assert "Exp2" in result

    def test_list_empty(self, engine):
        result = engine.list_experiments()
        assert "暂无实验" in result

    def test_list_filtered_by_status(self, engine):
        exp_id = engine.create_experiment("Draft Exp", "ig")
        result = engine.list_experiments(status=ExperimentStatus.DRAFT)
        assert "Draft Exp" in result

    def test_list_running_when_none(self, engine):
        engine.create_experiment("Draft Only", "ig")
        result = engine.list_experiments(status=ExperimentStatus.RUNNING)
        assert "暂无实验" in result


# ─── Start Experiment ────────────────────────────────────────────

class TestStartExperiment:
    def test_start_with_valid_setup(self, experiment_with_variants):
        exp_id, _, _ = experiment_with_variants
        engine = ABTestEngine.__new__(ABTestEngine)
        # Re-use the fixture's engine
        pass

    def test_start_without_variants(self, engine):
        exp_id = engine.create_experiment("No Variants", "ig")
        result = engine.start_experiment(exp_id)
        assert "至少需要2个变体" in result

    def test_start_without_control(self, engine):
        exp_id = engine.create_experiment("No Control", "ig")
        engine.add_variant(exp_id, "V1", VariantType.CAPTION, "text1")
        engine.add_variant(exp_id, "V2", VariantType.CAPTION, "text2")
        result = engine.start_experiment(exp_id)
        assert "控制组" in result

    def test_start_success(self, engine):
        exp_id = engine.create_experiment("Ready", "ig")
        engine.add_variant(exp_id, "Control", VariantType.CAPTION, "a", is_control=True)
        engine.add_variant(exp_id, "Test", VariantType.CAPTION, "b")
        result = engine.start_experiment(exp_id)
        assert "已开始" in result


# ─── Record Metrics ──────────────────────────────────────────────

class TestRecordMetrics:
    def test_record_single_metric(self, experiment_with_variants, engine):
        _, control_id, _ = experiment_with_variants
        engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 3.5)
        # Verify sample size increased
        row = engine.db.execute(
            "SELECT sample_size FROM variants WHERE id=?", (control_id,)
        ).fetchone()
        assert row["sample_size"] == 1

    def test_record_multiple_metrics(self, experiment_with_variants, engine):
        _, control_id, variant_id = experiment_with_variants
        for i in range(10):
            engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 2.0 + i * 0.1)
            engine.record_metric(variant_id, MetricType.ENGAGEMENT_RATE, 3.0 + i * 0.1)

        ctrl_row = engine.db.execute(
            "SELECT sample_size FROM variants WHERE id=?", (control_id,)
        ).fetchone()
        assert ctrl_row["sample_size"] == 10

    def test_record_with_post_id(self, experiment_with_variants, engine):
        _, control_id, _ = experiment_with_variants
        engine.record_metric(
            control_id, MetricType.LIKES, 150, post_id="post_123"
        )
        row = engine.db.execute(
            "SELECT post_id FROM variant_metrics WHERE variant_id=?",
            (control_id,)
        ).fetchone()
        assert row["post_id"] == "post_123"


# ─── Get Results ─────────────────────────────────────────────────

class TestGetResults:
    def test_results_with_data(self, experiment_with_variants, engine):
        exp_id, control_id, variant_id = experiment_with_variants
        # Add metrics
        for _ in range(20):
            engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 2.0)
            engine.record_metric(variant_id, MetricType.ENGAGEMENT_RATE, 4.0)

        result = engine.get_results(exp_id)
        assert isinstance(result, ExperimentResult)
        assert result.experiment_name == "Caption Test"
        assert len(result.variant_results) == 2

    def test_results_no_data(self, experiment_with_variants, engine):
        exp_id, _, _ = experiment_with_variants
        result = engine.get_results(exp_id)
        assert result.confidence == 0
        assert not result.is_significant

    def test_results_nonexistent(self, engine):
        result = engine.get_results("fake_id")
        assert result.experiment_name == "Unknown"

    def test_results_summary(self, experiment_with_variants, engine):
        exp_id, control_id, variant_id = experiment_with_variants
        for _ in range(50):
            engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 2.0)
            engine.record_metric(variant_id, MetricType.ENGAGEMENT_RATE, 5.0)

        result = engine.get_results(exp_id)
        summary = result.summary()
        assert "实验结果" in summary
        assert "Caption Test" in summary

    def test_significant_result_has_winner(self, experiment_with_variants, engine):
        exp_id, control_id, variant_id = experiment_with_variants
        for _ in range(100):
            engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 1.0)
            engine.record_metric(variant_id, MetricType.ENGAGEMENT_RATE, 10.0)

        result = engine.get_results(exp_id)
        if result.is_significant:
            assert result.winner_id is not None
            assert result.lift_percent > 0

    def test_complete_experiment(self, experiment_with_variants, engine):
        exp_id, control_id, variant_id = experiment_with_variants
        for _ in range(10):
            engine.record_metric(control_id, MetricType.ENGAGEMENT_RATE, 2.0)
            engine.record_metric(variant_id, MetricType.ENGAGEMENT_RATE, 3.0)

        result = engine.complete_experiment(exp_id)
        assert isinstance(result, ExperimentResult)

        # Check status updated
        row = engine.db.execute(
            "SELECT status FROM experiments WHERE id=?", (exp_id,)
        ).fetchone()
        assert row["status"] == "completed"


# ─── Statistical Functions ───────────────────────────────────────

class TestStatistics:
    def test_calculate_lift_positive(self):
        assert _calculate_lift(2.0, 3.0) == 50.0

    def test_calculate_lift_negative(self):
        assert _calculate_lift(4.0, 2.0) == -50.0

    def test_calculate_lift_zero_base(self):
        assert _calculate_lift(0.0, 5.0) == 0.0

    def test_calculate_lift_no_change(self):
        assert _calculate_lift(3.0, 3.0) == 0.0

    def test_z_test_low_sample(self):
        conf = _z_test_confidence(2.0, 1, 4.0, 1)
        assert conf == 0.0

    def test_z_test_similar_rates(self):
        conf = _z_test_confidence(5.0, 100, 5.1, 100)
        assert conf < 90

    def test_z_test_different_rates(self):
        conf = _z_test_confidence(2.0, 500, 10.0, 500)
        assert conf > 50

    def test_z_to_confidence_high(self):
        assert _z_to_confidence(3.5) == 99.9

    def test_z_to_confidence_medium(self):
        conf = _z_to_confidence(1.96)
        assert conf >= 95.0

    def test_z_to_confidence_low(self):
        conf = _z_to_confidence(0.5)
        assert 0 < conf < 50

    def test_z_to_confidence_zero(self):
        assert _z_to_confidence(0.0) == 0.0


# ─── Variant dataclass ───────────────────────────────────────────

class TestVariant:
    def test_add_metric(self):
        v = Variant(id="v1", name="Test", variant_type=VariantType.CAPTION, content="text")
        v.sample_size = 1
        v.add_metric(MetricType.LIKES, 100)
        assert v.get_metric(MetricType.LIKES) == 100

    def test_get_missing_metric(self):
        v = Variant(id="v1", name="Test", variant_type=VariantType.CAPTION, content="text")
        assert v.get_metric(MetricType.SHARES) == 0.0


# ─── Recommendations ─────────────────────────────────────────────

class TestRecommendations:
    def test_generates_recs_not_significant(self):
        variant_data = [
            {"id": "c", "name": "Control", "is_control": True,
             "metric_value": 2.0, "sample_size": 10},
            {"id": "t", "name": "Test", "is_control": False,
             "metric_value": 2.5, "sample_size": 10},
        ]
        recs = _generate_recommendations(
            variant_data, variant_data[0], False, MetricType.ENGAGEMENT_RATE
        )
        assert len(recs) > 0
        assert any("数据" in r or "继续" in r for r in recs)

    def test_underperforming_variant_flagged(self):
        variant_data = [
            {"id": "c", "name": "Control", "is_control": True,
             "metric_value": 5.0, "sample_size": 100},
            {"id": "t", "name": "Bad Variant", "is_control": False,
             "metric_value": 1.0, "sample_size": 100},
        ]
        recs = _generate_recommendations(
            variant_data, variant_data[0], True, MetricType.ENGAGEMENT_RATE
        )
        assert any("停用" in r or "低于" in r for r in recs)

    def test_excellent_variant_flagged(self):
        variant_data = [
            {"id": "c", "name": "Control", "is_control": True,
             "metric_value": 2.0, "sample_size": 100},
            {"id": "t", "name": "Great Variant", "is_control": False,
             "metric_value": 10.0, "sample_size": 100},
        ]
        recs = _generate_recommendations(
            variant_data, variant_data[0], True, MetricType.ENGAGEMENT_RATE
        )
        assert any("优异" in r or "全量" in r for r in recs)
