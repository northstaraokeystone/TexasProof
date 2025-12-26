"""
TexasProof Monte Carlo Simulation Harness.

6 mandatory Texas scenarios. 10k+ runs for production.
"""

from dataclasses import dataclass, field
from typing import Any, Callable
import random
import sys

from .core import (
    emit_receipt,
    merkle,
    TENANT_ID,
    SCENARIO_NAMES,
    SCENARIO_TOLERANCES,
    DEFAULT_CYCLES,
    DEFAULT_MONTE_CARLO_RUNS,
    DEFAULT_SEED,
    MAX_CONSECUTIVE_FAILURES,
    StopRuleException,
    stoprule_detection_rate,
    stoprule_consecutive_failures,
)
from .entropy import system_entropy
from .scenarios import (
    scenario_baseline,
    scenario_stress,
    scenario_genesis,
    scenario_colony_ridge,
    scenario_fund_diversion,
    scenario_godel,
    ScenarioResult,
    run_scenario as run_single_scenario,
)
from .watcher import create_fraud_vector_watchers, run_watcher_cycle
from .genesis import run_genesis_cycle


@dataclass
class SimConfig:
    """Simulation configuration."""
    n_cycles: int = DEFAULT_CYCLES
    n_monte_carlo_runs: int = DEFAULT_MONTE_CARLO_RUNS
    wound_rate: float = 0.1
    resource_budget: float = 1.0
    conservation_tolerance: float = 0.1
    random_seed: int = DEFAULT_SEED


@dataclass
class SimState:
    """Simulation state."""
    active_watchers: list = field(default_factory=list)
    wound_history: list = field(default_factory=list)
    receipt_ledger: list = field(default_factory=list)
    entropy_trace: list = field(default_factory=list)
    violations: list = field(default_factory=list)
    cycle: int = 0


@dataclass
class SimResult:
    """Simulation result."""
    final_state: SimState
    all_passed: bool
    scenario_results: dict
    violations: list
    receipt_hash: str


def simulate_cycle(state: SimState, config: SimConfig) -> SimState:
    """
    Run one cycle: ingest → detect → validate.

    Args:
        state: Current simulation state
        config: Simulation configuration

    Returns:
        Updated simulation state
    """
    state.cycle += 1

    # Generate wounds with some probability
    if random.random() < config.wound_rate:
        wound = {
            "receipt_type": "wound",
            "wound_type": random.choice([
                "high_risk_contract",
                "suspicious_donation",
                "unauthorized_invoice",
                "audit_delay"
            ]),
            "cycle": state.cycle,
            "severity": random.choice(["low", "medium", "high"])
        }
        state.wound_history.append(wound)
        state.receipt_ledger.append(wound)

    # Run watchers
    if state.active_watchers:
        new_receipts = state.receipt_ledger[-10:]  # Last 10 receipts
        responses = run_watcher_cycle(state.active_watchers, new_receipts)
        state.receipt_ledger.extend(responses)

    # Compute entropy
    entropy = system_entropy(state.receipt_ledger)
    state.entropy_trace.append(entropy)

    # Genesis cycle every 50 cycles
    if state.cycle % 50 == 0:
        genesis_result = run_genesis_cycle(state.receipt_ledger, state.active_watchers)
        state.active_watchers.extend(genesis_result.get("new_watchers", []))

    return state


def validate_constraints(state: SimState, config: SimConfig) -> list:
    """
    Check all validators, return list of violations.

    Args:
        state: Current simulation state
        config: Simulation configuration

    Returns:
        List of violation strings
    """
    violations = []

    # Check entropy conservation
    if len(state.entropy_trace) >= 2:
        initial = state.entropy_trace[0] if state.entropy_trace[0] > 0 else 1.0
        current = state.entropy_trace[-1]
        change = abs(current - initial) / initial

        if change > config.conservation_tolerance:
            violations.append(f"Entropy change {change:.2%} exceeds tolerance {config.conservation_tolerance:.2%}")

    # Check wound accumulation
    if len(state.wound_history) > config.n_cycles * config.wound_rate * 2:
        violations.append("Wound accumulation exceeds expected rate")

    return violations


def run_simulation(config: SimConfig) -> SimResult:
    """
    Execute full simulation. Return final state with violations.

    Args:
        config: Simulation configuration

    Returns:
        SimResult with final state and results
    """
    random.seed(config.random_seed)

    # Initialize state
    state = SimState()
    state.active_watchers = create_fraud_vector_watchers()

    # Run cycles
    for _ in range(config.n_cycles):
        state = simulate_cycle(state, config)

        # Validate periodically
        if state.cycle % 100 == 0:
            violations = validate_constraints(state, config)
            state.violations.extend(violations)

    # Run all scenarios
    scenario_results = {}
    all_passed = True
    consecutive_failures = 0

    for scenario_name in SCENARIO_NAMES:
        try:
            result = run_single_scenario(scenario_name, seed=config.random_seed)
            scenario_results[scenario_name] = {
                "passed": result.passed,
                "metrics": result.metrics,
                "violations": result.violations
            }

            if not result.passed:
                all_passed = False
                consecutive_failures += 1
                if consecutive_failures > MAX_CONSECUTIVE_FAILURES:
                    state.violations.append(f"Consecutive failures ({consecutive_failures}) exceed maximum")
                    break
            else:
                consecutive_failures = 0

        except StopRuleException as e:
            scenario_results[scenario_name] = {
                "passed": False,
                "error": str(e),
                "violations": [str(e)]
            }
            all_passed = False
            consecutive_failures += 1

    # Compute final receipt hash
    receipt_hash = merkle(state.receipt_ledger) if state.receipt_ledger else "empty"

    # Emit simulation complete receipt
    emit_receipt("sim_complete", {
        "tenant_id": TENANT_ID,
        "cycles": config.n_cycles,
        "all_passed": all_passed,
        "scenarios_run": len(scenario_results),
        "watchers_active": len(state.active_watchers),
        "total_receipts": len(state.receipt_ledger),
        "receipt_hash": receipt_hash
    })

    return SimResult(
        final_state=state,
        all_passed=all_passed,
        scenario_results=scenario_results,
        violations=state.violations,
        receipt_hash=receipt_hash
    )


def run_scenario(name: str, config: SimConfig) -> dict:
    """
    Run single named scenario.

    Args:
        name: Scenario name
        config: Simulation configuration

    Returns:
        Scenario result dict
    """
    result = run_single_scenario(name, seed=config.random_seed)
    return {
        "name": name,
        "passed": result.passed,
        "metrics": result.metrics,
        "violations": result.violations
    }


def run_all_scenarios(config: SimConfig) -> dict:
    """
    Run all 6 scenarios, return results.

    Args:
        config: Simulation configuration

    Returns:
        Dict with scenario results and summary
    """
    result = run_simulation(config)

    return {
        "all_passed": result.all_passed,
        "scenario_results": result.scenario_results,
        "violations": result.violations,
        "receipt_hash": result.receipt_hash,
        "summary": {
            "total_scenarios": len(SCENARIO_NAMES),
            "passed": sum(1 for r in result.scenario_results.values() if r.get("passed")),
            "failed": sum(1 for r in result.scenario_results.values() if not r.get("passed")),
            "watchers_spawned": len(result.final_state.active_watchers),
            "total_receipts": len(result.final_state.receipt_ledger)
        }
    }


def monte_carlo_run(
    scenario_name: str,
    n_runs: int = 1000,
    config: SimConfig = None
) -> dict:
    """
    Run Monte Carlo simulation for a single scenario.

    Args:
        scenario_name: Name of scenario to run
        n_runs: Number of Monte Carlo runs
        config: Base configuration

    Returns:
        Monte Carlo results
    """
    config = config or SimConfig()

    results = []
    passed_count = 0

    for i in range(n_runs):
        # Vary seed for each run
        run_seed = config.random_seed + i

        try:
            result = run_single_scenario(scenario_name, seed=run_seed)
            results.append({
                "run": i,
                "passed": result.passed,
                "metrics": result.metrics
            })
            if result.passed:
                passed_count += 1
        except Exception as e:
            results.append({
                "run": i,
                "passed": False,
                "error": str(e)
            })

    pass_rate = passed_count / n_runs if n_runs > 0 else 0

    return {
        "scenario": scenario_name,
        "n_runs": n_runs,
        "pass_rate": pass_rate,
        "passed_count": passed_count,
        "failed_count": n_runs - passed_count,
        "results": results[:10]  # First 10 results for inspection
    }


def full_monte_carlo(config: SimConfig = None) -> dict:
    """
    Run full Monte Carlo simulation across all scenarios.

    Args:
        config: Simulation configuration

    Returns:
        Full Monte Carlo results
    """
    config = config or SimConfig()

    scenario_results = {}
    overall_passed = True

    for scenario_name in SCENARIO_NAMES:
        mc_result = monte_carlo_run(
            scenario_name,
            n_runs=min(config.n_monte_carlo_runs, 1000),  # Cap per-scenario runs
            config=config
        )
        scenario_results[scenario_name] = mc_result

        # Check if scenario meets threshold
        if mc_result["pass_rate"] < 0.95:
            overall_passed = False

    emit_receipt("monte_carlo_complete", {
        "tenant_id": TENANT_ID,
        "n_scenarios": len(SCENARIO_NAMES),
        "n_runs_per_scenario": min(config.n_monte_carlo_runs, 1000),
        "overall_passed": overall_passed,
        "scenario_pass_rates": {name: r["pass_rate"] for name, r in scenario_results.items()}
    })

    return {
        "overall_passed": overall_passed,
        "scenario_results": scenario_results,
        "config": {
            "n_cycles": config.n_cycles,
            "n_monte_carlo_runs": config.n_monte_carlo_runs,
            "random_seed": config.random_seed
        }
    }
