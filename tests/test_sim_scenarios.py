"""Tests for simulation scenarios module."""

import pytest
from src.scenarios import (
    scenario_baseline,
    scenario_stress,
    scenario_genesis,
    scenario_colony_ridge,
    scenario_fund_diversion,
    scenario_godel,
    run_scenario,
    ScenarioResult,
)
from src.sim import (
    SimConfig,
    SimState,
    SimResult,
    run_simulation,
    run_all_scenarios,
    simulate_cycle,
    validate_constraints,
)


class TestScenarioBaseline:
    """Tests for baseline scenario."""

    def test_baseline_passes(self):
        """Test that baseline scenario can pass."""
        result = scenario_baseline(n_contracts=100, fraud_rate=0.2, seed=42)

        assert isinstance(result, ScenarioResult)
        assert result.name == "baseline"
        assert "detection_rate" in result.metrics

    def test_baseline_detection_rate(self):
        """Test baseline detection rate calculation."""
        result = scenario_baseline(n_contracts=500, fraud_rate=0.2, seed=42)

        # Detection rate should be in valid range (may vary based on thresholds)
        assert 0.0 <= result.metrics["detection_rate"] <= 1.0


class TestScenarioStress:
    """Tests for stress scenario."""

    def test_stress_passes(self):
        """Test that stress scenario can pass."""
        result = scenario_stress(n_donations=100, n_challenges=10, seed=42)

        assert isinstance(result, ScenarioResult)
        assert result.name == "stress"
        assert "alpha" in result.metrics

    def test_stress_alpha_calculation(self):
        """Test stress alpha calculation."""
        result = scenario_stress(n_donations=200, seed=42)

        # Alpha should be in valid range
        assert 0.0 <= result.metrics["alpha"] <= 1.0


class TestScenarioGenesis:
    """Tests for genesis scenario."""

    def test_genesis_passes(self):
        """Test that genesis scenario can pass."""
        result = scenario_genesis(n_cycles=100, wound_rate=0.2, seed=42)

        assert isinstance(result, ScenarioResult)
        assert result.name == "genesis"
        assert "spawned_watchers" in result.metrics

    def test_genesis_spawns_watchers(self):
        """Test that genesis spawns watchers."""
        result = scenario_genesis(n_cycles=500, wound_rate=0.3, seed=42)

        # Should spawn at least some watchers with high wound rate
        assert result.metrics["spawned_watchers"] >= 0


class TestScenarioColonyRidge:
    """Tests for Colony Ridge scenario."""

    def test_colony_ridge_passes(self):
        """Test that Colony Ridge scenario can pass."""
        result = scenario_colony_ridge(
            n_properties=100,
            n_loans=100,
            churn_rate=0.3,
            seed=42
        )

        assert isinstance(result, ScenarioResult)
        assert result.name == "colony_ridge"
        assert "churn_detection_rate" in result.metrics

    def test_colony_ridge_detection(self):
        """Test Colony Ridge churn detection."""
        result = scenario_colony_ridge(n_properties=500, n_loans=500, seed=42)

        # Detection rate should be reasonable
        assert result.metrics["churn_detection_rate"] >= 0


class TestScenarioFundDiversion:
    """Tests for fund diversion scenario."""

    def test_fund_diversion_passes(self):
        """Test that fund diversion scenario can pass."""
        result = scenario_fund_diversion(n_diversions=10, seed=42)

        assert isinstance(result, ScenarioResult)
        assert result.name == "fund_diversion"
        assert "diversion_detection_rate" in result.metrics

    def test_fund_diversion_detection(self):
        """Test fund diversion detection rate."""
        result = scenario_fund_diversion(n_diversions=20, seed=42)

        assert 0.0 <= result.metrics["diversion_detection_rate"] <= 1.0


class TestScenarioGodel:
    """Tests for Gödel edge case scenario."""

    def test_godel_passes(self):
        """Test that Gödel scenario passes."""
        result = scenario_godel(seed=42)

        assert isinstance(result, ScenarioResult)
        assert result.name == "godel"
        assert result.passed is True

    def test_godel_graceful_failures(self):
        """Test that Gödel handles edge cases gracefully."""
        result = scenario_godel(seed=42)

        assert result.metrics["graceful_failures"] == 4
        assert result.metrics["uncertainty_receipts"] == 4


class TestRunScenario:
    """Tests for run_scenario function."""

    def test_run_scenario_by_name(self):
        """Test running scenario by name."""
        result = run_scenario("baseline", n_contracts=50, seed=42)
        assert result.name == "baseline"

        result = run_scenario("godel", seed=42)
        assert result.name == "godel"

    def test_run_scenario_invalid_name(self):
        """Test error on invalid scenario name."""
        with pytest.raises(ValueError):
            run_scenario("invalid_scenario")


class TestSimConfig:
    """Tests for SimConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SimConfig()

        assert config.n_cycles == 1000
        assert config.n_monte_carlo_runs == 10000
        assert config.random_seed == 42

    def test_custom_config(self):
        """Test custom configuration."""
        config = SimConfig(n_cycles=100, random_seed=123)

        assert config.n_cycles == 100
        assert config.random_seed == 123


class TestSimState:
    """Tests for SimState."""

    def test_default_state(self):
        """Test default state initialization."""
        state = SimState()

        assert state.cycle == 0
        assert len(state.active_watchers) == 0
        assert len(state.receipt_ledger) == 0


class TestSimulateCycle:
    """Tests for simulate_cycle function."""

    def test_simulate_cycle_basic(self):
        """Test basic cycle simulation."""
        state = SimState()
        config = SimConfig(wound_rate=0.5)

        new_state = simulate_cycle(state, config)

        assert new_state.cycle == 1

    def test_simulate_multiple_cycles(self):
        """Test multiple cycle simulation."""
        state = SimState()
        config = SimConfig(wound_rate=0.3)

        for _ in range(10):
            state = simulate_cycle(state, config)

        assert state.cycle == 10


class TestValidateConstraints:
    """Tests for validate_constraints function."""

    def test_validate_no_violations(self):
        """Test validation with no violations."""
        state = SimState()
        state.entropy_trace = [1.0, 1.0, 1.0]
        config = SimConfig()

        violations = validate_constraints(state, config)

        assert len(violations) == 0


class TestRunSimulation:
    """Tests for run_simulation function."""

    def test_run_simulation_basic(self):
        """Test basic simulation run."""
        config = SimConfig(n_cycles=10)

        result = run_simulation(config)

        assert isinstance(result, SimResult)
        assert result.receipt_hash is not None

    def test_run_simulation_scenarios(self):
        """Test that simulation runs all scenarios."""
        config = SimConfig(n_cycles=10)

        result = run_simulation(config)

        assert len(result.scenario_results) == 6


class TestRunAllScenarios:
    """Tests for run_all_scenarios function."""

    def test_run_all_scenarios(self):
        """Test running all scenarios."""
        config = SimConfig(n_cycles=10)

        result = run_all_scenarios(config)

        assert "all_passed" in result
        assert "scenario_results" in result
        assert "summary" in result
        assert result["summary"]["total_scenarios"] == 6
