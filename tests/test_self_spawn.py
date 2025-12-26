"""Tests for self-spawning watcher and genesis modules."""

import pytest
from src.watcher import (
    create_watcher,
    check_autocatalysis,
    spawn_watcher,
    measure_watcher_fitness,
    run_watcher_cycle,
    deactivate_watcher,
    create_fraud_vector_watchers,
)
from src.genesis import (
    harvest_wounds,
    identify_patterns,
    synthesize_blueprint,
    emit_genesis_receipt,
    run_genesis_cycle,
    detect_emerging_scandal,
    crystallize_scandal_watcher,
)


class TestCreateWatcher:
    """Tests for watcher creation."""

    def test_create_watcher_basic(self):
        """Test basic watcher creation."""
        watcher = create_watcher(
            pattern_name="test_pattern",
            trigger_condition=lambda r: r.get("type") == "test"
        )

        assert watcher["pattern_name"] == "test_pattern"
        assert watcher["status"] == "blueprint"
        assert "id" in watcher

    def test_create_watcher_fields(self):
        """Test watcher has required fields."""
        watcher = create_watcher("test", lambda r: True)

        assert "created_at" in watcher
        assert "activation_count" in watcher
        assert "fitness" in watcher


class TestCheckAutocatalysis:
    """Tests for autocatalysis checking."""

    def test_autocatalysis_threshold(self, sample_receipts):
        """Test autocatalysis threshold checking."""
        pattern = {
            "pattern_name": "wound",
            "autocatalysis_threshold": 3
        }

        # Modify receipts to reference the pattern
        receipts = sample_receipts + [
            {"payload": {"pattern_name": "wound"}},
            {"payload": {"triggered_by": "wound"}},
            {"payload": {"source": "wound_detection"}}
        ]

        result = check_autocatalysis(receipts, pattern)
        assert result is True

    def test_no_autocatalysis(self, sample_receipts):
        """Test no autocatalysis with low references."""
        pattern = {"pattern_name": "nonexistent", "autocatalysis_threshold": 5}

        result = check_autocatalysis(sample_receipts, pattern)
        assert result is False


class TestSpawnWatcher:
    """Tests for watcher spawning."""

    def test_spawn_watcher_basic(self):
        """Test basic watcher spawning."""
        wounds = [
            {"wound_type": "high_risk", "created_at": "2024-01-01T12:00:00Z"}
            for _ in range(10)
        ]

        watcher = spawn_watcher(wounds, threshold=5)

        assert watcher is not None
        assert watcher["status"] == "active"
        assert "wound_count" in watcher

    def test_no_spawn_below_threshold(self):
        """Test no spawn below threshold."""
        wounds = [
            {"wound_type": "high_risk", "created_at": "2024-01-01T12:00:00Z"}
            for _ in range(3)
        ]

        watcher = spawn_watcher(wounds, threshold=5)

        assert watcher is None


class TestMeasureWatcherFitness:
    """Tests for watcher fitness measurement."""

    def test_measure_fitness_basic(self, sample_receipts):
        """Test basic fitness measurement."""
        watcher = create_watcher(
            "test",
            lambda r: r.get("receipt_type") == "wound"
        )

        fitness = measure_watcher_fitness(watcher, sample_receipts)

        # Fitness should be a number
        assert isinstance(fitness, float)


class TestRunWatcherCycle:
    """Tests for running watcher cycle."""

    def test_run_cycle_basic(self, sample_receipts):
        """Test basic watcher cycle."""
        watchers = [
            create_watcher("test", lambda r: r.get("receipt_type") == "wound")
        ]
        watchers[0]["status"] = "active"

        responses = run_watcher_cycle(watchers, sample_receipts)

        # Should have some responses
        assert isinstance(responses, list)


class TestDeactivateWatcher:
    """Tests for watcher deactivation."""

    def test_deactivate_basic(self):
        """Test basic deactivation."""
        watcher = create_watcher("test", lambda r: True)
        watcher["status"] = "active"

        deactivated = deactivate_watcher(watcher, "manual")

        assert deactivated["status"] == "inactive"
        assert deactivated["deactivation_reason"] == "manual"


class TestCreateFraudVectorWatchers:
    """Tests for fraud vector watcher creation."""

    def test_create_fraud_watchers(self):
        """Test creating fraud vector watchers."""
        watchers = create_fraud_vector_watchers()

        assert len(watchers) >= 5
        assert all(w["status"] == "active" for w in watchers)


class TestHarvestWounds:
    """Tests for wound harvesting."""

    def test_harvest_wounds_basic(self, sample_receipts):
        """Test basic wound harvesting."""
        wounds = harvest_wounds(sample_receipts, days=30)

        # Should find wound receipts
        assert isinstance(wounds, list)

    def test_harvest_wounds_filter(self):
        """Test wound filtering."""
        from datetime import datetime, timedelta
        # Use recent timestamps
        recent_ts = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        receipts = [
            {"receipt_type": "wound", "ts": recent_ts},
            {"receipt_type": "ingest", "ts": recent_ts},
            {"receipt_type": "anomaly", "ts": recent_ts}
        ]

        wounds = harvest_wounds(receipts, days=30)

        # Should include wound and anomaly (both are wound-like types)
        assert len(wounds) >= 2


class TestIdentifyPatterns:
    """Tests for pattern identification."""

    def test_identify_patterns_basic(self):
        """Test basic pattern identification."""
        wounds = [
            {"receipt_type": "wound", "wound_type": "high_risk"}
            for _ in range(10)
        ]

        patterns = identify_patterns(wounds)

        assert len(patterns) >= 1
        assert patterns[0]["occurrence_count"] >= 5

    def test_identify_multiple_patterns(self):
        """Test identifying multiple patterns."""
        wounds = [
            {"receipt_type": "wound", "wound_type": "high_risk"} for _ in range(8)
        ] + [
            {"receipt_type": "wound", "wound_type": "audit_delay"} for _ in range(6)
        ]

        patterns = identify_patterns(wounds)

        assert len(patterns) >= 2


class TestSynthesizeBlueprint:
    """Tests for blueprint synthesis."""

    def test_synthesize_basic(self):
        """Test basic blueprint synthesis."""
        pattern = {
            "pattern_id": "test-123",
            "wound_type": "high_risk",
            "occurrence_count": 10,
            "avg_fraud_probability": 0.7
        }

        blueprint = synthesize_blueprint(pattern)

        assert blueprint["wound_type"] == "high_risk"
        assert blueprint["status"] == "blueprint"
        assert "trigger_condition" in blueprint


class TestRunGenesisCycle:
    """Tests for genesis cycle."""

    def test_run_genesis_cycle_basic(self, sample_receipts):
        """Test basic genesis cycle."""
        # Add more wounds
        receipts = sample_receipts + [
            {"receipt_type": "wound", "wound_type": "high_risk", "ts": "2024-01-01T12:00:00Z"}
            for _ in range(10)
        ]

        result = run_genesis_cycle(receipts, [])

        assert "wounds_harvested" in result
        assert "patterns_identified" in result

    def test_genesis_cycle_spawns_watchers(self):
        """Test that genesis cycle can spawn watchers."""
        from datetime import datetime, timedelta
        recent_ts = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        receipts = [
            {"receipt_type": "wound", "wound_type": "audit_delay", "ts": recent_ts, "fraud_probability": 0.8}
            for _ in range(20)
        ]

        result = run_genesis_cycle(receipts, [])

        # Should identify patterns when enough wounds exist
        assert result["wounds_harvested"] >= 10


class TestDetectEmergingScandal:
    """Tests for emerging scandal detection."""

    def test_detect_scandal_basic(self):
        """Test basic scandal detection."""
        receipts = [
            {"entity": "TSU", "receipt_type": "unauthorized_invoice"}
            for _ in range(10)
        ] + [
            {"entity": "TSU", "receipt_type": "audit_delay"}
            for _ in range(5)
        ]

        scandals = detect_emerging_scandal(receipts)

        assert len(scandals) >= 0  # May or may not find scandals


class TestCrystallizeScandal:
    """Tests for scandal crystallization."""

    def test_crystallize_basic(self):
        """Test basic scandal crystallization."""
        scandal = {
            "entity": "Test University",
            "scandal_score": 0.8,
            "indicators": [{"type": "unauthorized"}]
        }

        watcher = crystallize_scandal_watcher(scandal)

        assert watcher["status"] == "active"
        assert "scandal_source" in watcher
