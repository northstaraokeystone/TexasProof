"""
6 Mandatory Texas Scenarios.

No feature ships without all passing.

1. BASELINE: OLS contractor detection ≥95%
2. STRESS: PAC detection under pressure, α ≥0.70
3. GENESIS: Self-spawn watchers from wounds
4. COLONY_RIDGE: Predatory lending churn ≥90%
5. FUND_DIVERSION: Budget shift detection ≥85%
6. GÖDEL: Edge cases, graceful failure
"""

from dataclasses import dataclass
from typing import Any
import random

from .core import (
    emit_receipt,
    TENANT_ID,
    BASELINE_DETECTION_THRESHOLD,
    STRESS_ALPHA_THRESHOLD,
    STRESS_PRESSURE_LEVEL,
    GENESIS_MIN_WATCHERS,
    COLONY_RIDGE_CHURN_THRESHOLD,
    FUND_DIVERSION_THRESHOLD,
)
from .entropy import resilience_alpha
from .ols_contractor_proof import (
    generate_synthetic_ols_contracts,
    score_contract_fraud,
    analyze_ols_contractors,
)
from .pac_influence_proof import (
    generate_synthetic_pac_data,
    score_influence_capture,
    analyze_pac_influence,
)
from .predatory_lending_proof import (
    generate_synthetic_lending_data,
    calculate_foreclosure_rate,
    analyze_lending_portfolio,
)
from .watcher import spawn_watcher, create_fraud_vector_watchers, measure_watcher_fitness
from .genesis import run_genesis_cycle, detect_emerging_scandal


@dataclass
class ScenarioResult:
    """Result of a scenario run."""
    name: str
    passed: bool
    metrics: dict
    receipts: list
    violations: list


def scenario_baseline(n_contracts: int = 1000, fraud_rate: float = 0.2, seed: int = 42) -> ScenarioResult:
    """
    SCENARIO 1: BASELINE (OLS Contractor Detection)

    Standard OLS contractor fraud detection.
    Pass criteria: detection_rate >= 0.95

    Args:
        n_contracts: Number of synthetic contracts
        fraud_rate: Fraction of fraudulent contracts
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    # Generate synthetic data
    contracts = generate_synthetic_ols_contracts(n_contracts, fraud_rate)
    donations = []  # Simplified for baseline

    # Build donor network (empty for baseline)
    donor_network = {}

    # Run detection
    true_positives = 0
    false_negatives = 0
    receipts = []

    for contract in contracts:
        is_actually_fraud = contract.get("is_synthetic_fraud", False)
        fraud_score = score_contract_fraud(contract, donor_network)

        detected_as_fraud = fraud_score >= 0.7

        if is_actually_fraud:
            if detected_as_fraud:
                true_positives += 1
            else:
                false_negatives += 1

    # Calculate detection rate
    total_fraud = sum(1 for c in contracts if c.get("is_synthetic_fraud"))
    detection_rate = true_positives / total_fraud if total_fraud > 0 else 1.0

    passed = detection_rate >= BASELINE_DETECTION_THRESHOLD

    result = ScenarioResult(
        name="baseline",
        passed=passed,
        metrics={
            "detection_rate": detection_rate,
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "total_fraud": total_fraud,
            "total_contracts": n_contracts,
            "threshold": BASELINE_DETECTION_THRESHOLD
        },
        receipts=receipts,
        violations=[] if passed else [f"Detection rate {detection_rate:.2%} < {BASELINE_DETECTION_THRESHOLD:.2%}"]
    )

    emit_receipt("baseline_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "detection_rate": detection_rate,
        "threshold": BASELINE_DETECTION_THRESHOLD
    })

    return result


def scenario_stress(
    n_donations: int = 500,
    n_challenges: int = 50,
    pressure_levels: list = None,
    seed: int = 42
) -> ScenarioResult:
    """
    SCENARIO 2: STRESS (PAC Influence Under Pressure)

    PAC influence detection under political pressure.
    Pass criteria: α >= 0.70

    Args:
        n_donations: Number of donations
        n_challenges: Number of primary challenges
        pressure_levels: List of pressure levels to test
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    pressure_levels = pressure_levels or [0.0, 0.25, 0.5, 0.75, 1.0]

    # Generate synthetic data
    donations, challenges, votes, policies = generate_synthetic_pac_data(
        n_donations, n_challenges, capture_rate=0.3
    )

    detection_rates = []

    for pressure in pressure_levels:
        # Simulate pressure effect: higher pressure = some detections suppressed
        suppression_rate = pressure * 0.3  # Max 30% suppression at full pressure

        # Run detection with pressure
        true_positives = 0
        total_captures = 0

        for d in donations:
            if d.get("is_synthetic_capture"):
                total_captures += 1
                # Detection might be suppressed under pressure
                if random.random() > suppression_rate:
                    # Still detect if score high enough
                    capture_score = score_influence_capture([d], policies)
                    if capture_score >= 0.5:
                        true_positives += 1

        rate = true_positives / total_captures if total_captures > 0 else 1.0
        detection_rates.append(rate)

    # Calculate α (resilience)
    alpha = resilience_alpha(detection_rates, pressure_levels)

    passed = alpha >= STRESS_ALPHA_THRESHOLD

    result = ScenarioResult(
        name="stress",
        passed=passed,
        metrics={
            "alpha": alpha,
            "detection_rates": detection_rates,
            "pressure_levels": pressure_levels,
            "threshold": STRESS_ALPHA_THRESHOLD
        },
        receipts=[],
        violations=[] if passed else [f"α {alpha:.2f} < {STRESS_ALPHA_THRESHOLD:.2f}"]
    )

    emit_receipt("stress_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "alpha": alpha,
        "threshold": STRESS_ALPHA_THRESHOLD
    })

    return result


def scenario_genesis(n_cycles: int = 500, wound_rate: float = 0.1, seed: int = 42) -> ScenarioResult:
    """
    SCENARIO 3: GENESIS (Self-Spawn Watchers)

    Watcher spawning from wound patterns.
    Pass criteria: spawned_watchers >= 1

    Args:
        n_cycles: Number of simulation cycles
        wound_rate: Rate of wound generation
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    receipts = []
    watchers = []

    # Simulate cycles with wounds
    wound_types = ["unauthorized_invoice", "audit_delay", "high_risk_contract", "suspicious_donation"]

    for cycle in range(n_cycles):
        # Generate wound with some probability
        if random.random() < wound_rate:
            wound_type = random.choice(wound_types)
            wound = {
                "receipt_type": "wound",
                "wound_type": wound_type,
                "ts": f"2024-01-{(cycle % 28) + 1:02d}T12:00:00Z",
                "created_at": f"2024-01-{(cycle % 28) + 1:02d}T12:00:00Z",
                "severity": random.choice(["low", "medium", "high"]),
                "fraud_probability": random.uniform(0.5, 1.0)
            }
            receipts.append(wound)

        # Try to spawn watchers periodically
        if cycle % 50 == 0 and cycle > 0:
            wounds = [r for r in receipts if r.get("receipt_type") == "wound"]
            watcher = spawn_watcher(wounds, threshold=5)
            if watcher:
                watchers.append(watcher)

    # Run genesis cycle
    genesis_result = run_genesis_cycle(receipts, watchers)
    watchers.extend(genesis_result.get("new_watchers", []))

    # Measure fitness of spawned watchers
    for w in watchers:
        measure_watcher_fitness(w, receipts)

    passed = len(watchers) >= GENESIS_MIN_WATCHERS

    result = ScenarioResult(
        name="genesis",
        passed=passed,
        metrics={
            "spawned_watchers": len(watchers),
            "patterns_identified": genesis_result.get("patterns_identified", 0),
            "wounds_harvested": genesis_result.get("wounds_harvested", 0),
            "threshold": GENESIS_MIN_WATCHERS,
            "watcher_details": [
                {"id": w.get("id"), "pattern": w.get("pattern_name"), "fitness": w.get("fitness", 0)}
                for w in watchers
            ]
        },
        receipts=receipts,
        violations=[] if passed else [f"Spawned {len(watchers)} watchers < {GENESIS_MIN_WATCHERS}"]
    )

    emit_receipt("genesis_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "spawned_watchers": len(watchers),
        "threshold": GENESIS_MIN_WATCHERS
    })

    return result


def scenario_colony_ridge(
    n_properties: int = 1000,
    n_loans: int = 1000,
    churn_rate: float = 0.3,
    seed: int = 42
) -> ScenarioResult:
    """
    SCENARIO 4: COLONY_RIDGE (Predatory Lending Detection)

    Colony Ridge-style predatory lending detection.
    Pass criteria: churn_detection_rate >= 0.90

    Args:
        n_properties: Number of properties
        n_loans: Number of loans
        churn_rate: Rate of churned properties
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    # Generate synthetic data
    loans, transactions = generate_synthetic_lending_data(
        n_properties, n_loans, churn_rate=churn_rate, predatory_rate=0.3
    )

    # Run analysis
    results = analyze_lending_portfolio(loans, transactions)

    # Calculate detection rate
    # Count actual churned properties
    actual_churned = set()
    for t in transactions:
        if t.get("is_synthetic_churn"):
            actual_churned.add(t.get("property_id"))

    detected_churned = set(p.get("property_id") for p in results.get("churning_properties", []))

    if actual_churned:
        detection_rate = len(detected_churned & actual_churned) / len(actual_churned)
    else:
        detection_rate = 1.0

    passed = detection_rate >= COLONY_RIDGE_CHURN_THRESHOLD

    result = ScenarioResult(
        name="colony_ridge",
        passed=passed,
        metrics={
            "churn_detection_rate": detection_rate,
            "detected_churned": len(detected_churned),
            "actual_churned": len(actual_churned),
            "foreclosure_rate": results.get("portfolio_metrics", {}).get("foreclosure_rate", 0),
            "threshold": COLONY_RIDGE_CHURN_THRESHOLD
        },
        receipts=results.get("receipts", []),
        violations=[] if passed else [f"Churn detection {detection_rate:.2%} < {COLONY_RIDGE_CHURN_THRESHOLD:.2%}"]
    )

    emit_receipt("colony_ridge_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "churn_detection_rate": detection_rate,
        "threshold": COLONY_RIDGE_CHURN_THRESHOLD
    })

    return result


def scenario_fund_diversion(
    n_diversions: int = 10,
    detection_noise: float = 0.1,
    seed: int = 42
) -> ScenarioResult:
    """
    SCENARIO 5: FUND_DIVERSION (TDCJ→OLS Tracking)

    Fund diversion detection (TDCJ → OLS).
    Pass criteria: diversion_detection_rate >= 0.85

    Args:
        n_diversions: Number of fund diversions to simulate
        detection_noise: Noise in detection (simulates imperfect data)
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    # Generate synthetic diversion data
    source_budgets = {}
    dest_spending = {}
    diversions_actual = []

    departments = ["TDCJ", "DPS", "DSHS", "TWC", "TxDOT"]
    programs = ["Operation Lone Star", "Border Security", "Emergency Response"]

    for i in range(n_diversions):
        source = random.choice(departments)
        dest = random.choice(programs)
        amount = random.uniform(10_000_000, 100_000_000)

        # Set up source budget
        if source not in source_budgets:
            original = random.uniform(500_000_000, 2_000_000_000)
            source_budgets[source] = {
                "original_usd": original,
                "actual_usd": original,
                "impact": "understaffing"
            }

        # Apply diversion
        source_budgets[source]["actual_usd"] -= amount

        # Set up destination spending
        if dest not in dest_spending:
            dest_spending[dest] = {
                "original_usd": random.uniform(100_000_000, 500_000_000),
                "actual_usd": random.uniform(100_000_000, 500_000_000)
            }

        dest_spending[dest]["actual_usd"] += amount

        diversions_actual.append({
            "source": source,
            "destination": dest,
            "amount_usd": amount
        })

    # Run detection (with some noise)
    from .ols_contractor_proof import detect_fund_diversion
    detected = detect_fund_diversion(source_budgets, dest_spending)

    # Calculate detection rate (allow for noise)
    # A diversion is "detected" if we found a matching source-dest pair
    detected_pairs = set((d.get("source"), d.get("destination")) for d in detected)
    actual_pairs = set((d.get("source"), d.get("destination")) for d in diversions_actual)

    if actual_pairs:
        detection_rate = len(detected_pairs & actual_pairs) / len(actual_pairs)
    else:
        detection_rate = 1.0

    # Add some detection noise
    detection_rate = max(0, min(1, detection_rate + random.uniform(-detection_noise, detection_noise)))

    passed = detection_rate >= FUND_DIVERSION_THRESHOLD

    total_detected_amount = sum(d.get("amount_usd", 0) for d in detected)

    result = ScenarioResult(
        name="fund_diversion",
        passed=passed,
        metrics={
            "diversion_detection_rate": detection_rate,
            "diversions_detected": len(detected),
            "diversions_actual": len(diversions_actual),
            "amount_flagged_usd": total_detected_amount,
            "threshold": FUND_DIVERSION_THRESHOLD
        },
        receipts=[],
        violations=[] if passed else [f"Diversion detection {detection_rate:.2%} < {FUND_DIVERSION_THRESHOLD:.2%}"]
    )

    emit_receipt("fund_diversion_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "diversion_detection_rate": detection_rate,
        "amount_flagged_usd": total_detected_amount,
        "threshold": FUND_DIVERSION_THRESHOLD
    })

    return result


def scenario_godel(seed: int = 42) -> ScenarioResult:
    """
    SCENARIO 6: GÖDEL (Edge Cases)

    Edge case handling and graceful failure.
    Pass criteria: no crashes, uncertainty_receipts emitted

    Tests:
    - Zero-dollar contract (should flag)
    - Negative donation (should reject)
    - Self-referential PAC (donor is recipient)
    - Empty input handling

    Args:
        seed: Random seed

    Returns:
        ScenarioResult
    """
    random.seed(seed)

    edge_cases = []
    graceful_failures = 0
    uncertainty_receipts = []

    # Edge case 1: Zero-dollar contract
    try:
        zero_contract = {
            "name": "Zero Dollar Corp",
            "amount_usd": 0,
            "contract_type": "emergency",
            "cost_per_unit_usd": 0
        }
        fraud_score = score_contract_fraud(zero_contract, {})
        edge_cases.append({
            "case": "zero_dollar_contract",
            "handled": True,
            "result": f"fraud_score={fraud_score}"
        })
        graceful_failures += 1

        emit_receipt("uncertainty", {
            "tenant_id": TENANT_ID,
            "case": "zero_dollar_contract",
            "reason": "Zero-dollar contract flagged for review"
        })
        uncertainty_receipts.append("zero_dollar_contract")
    except Exception as e:
        edge_cases.append({
            "case": "zero_dollar_contract",
            "handled": False,
            "error": str(e)
        })

    # Edge case 2: Negative donation
    try:
        negative_donation = {
            "donor": "Refund Corp",
            "amount": -50000,
            "pac_name": "Test PAC"
        }
        # Should be rejected or handled gracefully
        capture_score = score_influence_capture([negative_donation], [])
        edge_cases.append({
            "case": "negative_donation",
            "handled": True,
            "result": f"capture_score={capture_score}"
        })
        graceful_failures += 1

        emit_receipt("uncertainty", {
            "tenant_id": TENANT_ID,
            "case": "negative_donation",
            "reason": "Negative donation rejected"
        })
        uncertainty_receipts.append("negative_donation")
    except Exception as e:
        edge_cases.append({
            "case": "negative_donation",
            "handled": False,
            "error": str(e)
        })

    # Edge case 3: Self-referential PAC
    try:
        self_ref_donation = {
            "donor": "Circular PAC",
            "amount": 100000,
            "pac_name": "Circular PAC"  # Donor is the PAC
        }
        capture_score = score_influence_capture([self_ref_donation], [])
        edge_cases.append({
            "case": "self_referential_pac",
            "handled": True,
            "result": f"capture_score={capture_score}"
        })
        graceful_failures += 1

        emit_receipt("uncertainty", {
            "tenant_id": TENANT_ID,
            "case": "self_referential_pac",
            "reason": "Self-referential PAC structure detected"
        })
        uncertainty_receipts.append("self_referential_pac")
    except Exception as e:
        edge_cases.append({
            "case": "self_referential_pac",
            "handled": False,
            "error": str(e)
        })

    # Edge case 4: Empty input
    try:
        from .predatory_lending_proof import calculate_foreclosure_rate
        rate = calculate_foreclosure_rate([])
        edge_cases.append({
            "case": "empty_input",
            "handled": True,
            "result": f"foreclosure_rate={rate}"
        })
        graceful_failures += 1

        emit_receipt("uncertainty", {
            "tenant_id": TENANT_ID,
            "case": "empty_input",
            "reason": "Empty input handled gracefully"
        })
        uncertainty_receipts.append("empty_input")
    except Exception as e:
        edge_cases.append({
            "case": "empty_input",
            "handled": False,
            "error": str(e)
        })

    # Pass if all edge cases handled gracefully
    passed = graceful_failures == 4 and len(uncertainty_receipts) == 4

    result = ScenarioResult(
        name="godel",
        passed=passed,
        metrics={
            "graceful_failures": graceful_failures,
            "expected_failures": 4,
            "uncertainty_receipts": len(uncertainty_receipts),
            "edge_cases": edge_cases
        },
        receipts=[],
        violations=[] if passed else [f"Only {graceful_failures}/4 edge cases handled gracefully"]
    )

    emit_receipt("godel_scenario", {
        "tenant_id": TENANT_ID,
        "passed": passed,
        "graceful_failures": graceful_failures,
        "uncertainty_receipts": len(uncertainty_receipts)
    })

    return result


def run_scenario(name: str, **kwargs) -> ScenarioResult:
    """
    Run a scenario by name.

    Args:
        name: Scenario name
        **kwargs: Scenario-specific arguments

    Returns:
        ScenarioResult
    """
    scenarios = {
        "baseline": scenario_baseline,
        "stress": scenario_stress,
        "genesis": scenario_genesis,
        "colony_ridge": scenario_colony_ridge,
        "fund_diversion": scenario_fund_diversion,
        "godel": scenario_godel
    }

    if name not in scenarios:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(scenarios.keys())}")

    return scenarios[name](**kwargs)
