"""
TexasProof Entropy Module - Information-theoretic fraud detection.

Shannon entropy exposes no-bid contract chaos. Fraud resists compression.

The Physics:
- Legitimate competitive bidding has predictable structure → compresses well
- Emergency no-bid contracts lack causal structure → high entropy, resists compression
- PAC-to-primary-purge pipelines are TOO predictable (low entropy) → suspicious
"""

import math
import zlib
from collections import Counter
from typing import Any

import numpy as np

from .core import emit_receipt, TENANT_ID


def shannon_entropy(distribution: np.ndarray) -> float:
    """
    Compute Shannon entropy: H = -Σ p(x) log₂ p(x)

    Args:
        distribution: Array of probabilities (must sum to 1) or counts

    Returns:
        Shannon entropy in bits
    """
    # Handle numpy array
    dist = np.asarray(distribution, dtype=np.float64)

    # If counts, normalize to probabilities
    if dist.sum() > 1.001 or dist.sum() < 0.999:
        total = dist.sum()
        if total == 0:
            return 0.0
        dist = dist / total

    # Filter out zeros to avoid log(0)
    dist = dist[dist > 0]

    # Compute entropy
    return float(-np.sum(dist * np.log2(dist)))


def system_entropy(receipts: list) -> float:
    """
    Compute entropy of receipt stream. High = disorder.

    Args:
        receipts: List of receipt dicts

    Returns:
        System entropy based on receipt type distribution
    """
    if not receipts:
        return 0.0

    # Count receipt types
    type_counts = Counter(r.get("receipt_type", "unknown") for r in receipts)

    # Convert to distribution
    counts = np.array(list(type_counts.values()), dtype=np.float64)

    return shannon_entropy(counts)


def agent_fitness(
    receipts_before: list,
    receipts_after: list,
    pattern_count: int
) -> float:
    """
    Compute agent fitness as entropy reduction per receipt.
    Positive = agent reduces uncertainty (good).

    Args:
        receipts_before: Receipts before agent intervention
        receipts_after: Receipts after agent intervention
        pattern_count: Number of patterns agent addressed

    Returns:
        Fitness score (positive = effective)
    """
    if pattern_count == 0:
        return 0.0

    entropy_before = system_entropy(receipts_before)
    entropy_after = system_entropy(receipts_after)

    # Entropy reduction per pattern
    return (entropy_before - entropy_after) / pattern_count


def contract_entropy(contract: dict) -> float:
    """
    Compute entropy score for single contract.
    Emergency/no-bid = high entropy (lack of causal structure).

    Args:
        contract: Contract dict with type, amount, etc.

    Returns:
        Entropy score 0-1 (higher = more chaotic/suspicious)
    """
    score = 0.0

    # Contract type factor
    contract_type = contract.get("contract_type", "").lower()
    if "emergency" in contract_type:
        score += 0.4
    if "no-bid" in contract_type or "no_bid" in contract_type:
        score += 0.3

    # Cost anomaly factor
    cost_per_unit = contract.get("cost_per_unit", 0)
    market_rate = contract.get("market_rate", cost_per_unit)
    if market_rate > 0 and cost_per_unit > market_rate * 2:
        score += 0.2

    # Donor correlation factor
    donor_correlation = contract.get("donor_correlation", 0)
    score += donor_correlation * 0.1

    return min(1.0, score)


def pac_flow_entropy(donations: list, outcomes: list) -> float:
    """
    Compute entropy of donor→policy correlation.
    Low entropy = suspicious determinism (too predictable).

    Args:
        donations: List of donation dicts
        outcomes: List of policy outcome dicts

    Returns:
        Entropy score (low = suspicious correlation)
    """
    if not donations or not outcomes:
        return 1.0  # No data = assume random (high entropy)

    # Build correlation matrix
    donor_set = set(d.get("donor", "") for d in donations)
    outcome_set = set(o.get("outcome", "") for o in outcomes)

    if not donor_set or not outcome_set:
        return 1.0

    # Count donor→outcome correlations
    correlations = []
    for donor in donor_set:
        donor_donations = [d for d in donations if d.get("donor") == donor]
        donor_total = sum(d.get("amount", 0) for d in donor_donations)

        # Find outcomes that align with donor interests
        aligned_outcomes = sum(
            1 for o in outcomes
            if o.get("beneficiary") == donor or o.get("aligned_donor") == donor
        )

        if len(outcomes) > 0:
            correlations.append(aligned_outcomes / len(outcomes))

    if not correlations:
        return 1.0

    # Entropy of correlation distribution
    dist = np.array(correlations)
    if dist.sum() == 0:
        return 1.0

    # Normalize
    dist = dist / dist.sum()

    # Compute entropy
    entropy = shannon_entropy(dist)

    # Normalize to 0-1 range (max entropy for N items is log2(N))
    max_entropy = math.log2(len(correlations)) if len(correlations) > 1 else 1.0

    return entropy / max_entropy if max_entropy > 0 else 0.0


def compression_ratio(data: bytes) -> float:
    """
    AXIOM-style compression ratio. Fraud resists compression.

    Args:
        data: Bytes to compress

    Returns:
        Compression ratio (compressed_size / original_size)
        Higher = resists compression = higher fraud probability
    """
    if not data:
        return 0.0

    original_size = len(data)
    compressed = zlib.compress(data, level=9)
    compressed_size = len(compressed)

    return compressed_size / original_size


def mdl_score(data: bytes, model_size: int = 0) -> float:
    """
    Minimum Description Length score.
    High MDL = data doesn't fit expected model = anomaly.

    Args:
        data: Bytes to analyze
        model_size: Size of model used to describe regular data

    Returns:
        MDL score (higher = more anomalous)
    """
    if not data:
        return 0.0

    # Compressed size is an approximation of Kolmogorov complexity
    compressed = zlib.compress(data, level=9)

    # MDL = model_size + data_given_model
    # For fraud, data_given_model is high because fraud doesn't fit the model
    return model_size + len(compressed)


def entropy_fraud_score(contract: dict) -> float:
    """
    Combined entropy-based fraud score for a contract.

    Args:
        contract: Contract dict

    Returns:
        Fraud probability 0-1
    """
    # Contract entropy
    c_entropy = contract_entropy(contract)

    # Compression resistance
    import json
    data = json.dumps(contract, sort_keys=True).encode()
    c_ratio = compression_ratio(data)

    # Combine scores (weighted average)
    # High contract entropy + high compression ratio = fraud
    score = 0.6 * c_entropy + 0.4 * c_ratio

    return min(1.0, score)


def resilience_alpha(
    detection_rates: list,
    pressure_levels: list
) -> float:
    """
    Compute α (alpha) resilience: system stability under political pressure.

    Args:
        detection_rates: List of detection rates at different pressure levels
        pressure_levels: Corresponding pressure levels (0-1)

    Returns:
        α resilience score (higher = more resilient)
    """
    if not detection_rates or not pressure_levels:
        return 1.0

    # α measures how much detection degrades with pressure
    # Perfect resilience: detection stays constant regardless of pressure
    rates = np.array(detection_rates)
    pressures = np.array(pressure_levels)

    if len(rates) < 2:
        return rates[0] if len(rates) == 1 else 1.0

    # Compute slope of detection vs pressure
    # Negative slope = detection degrades with pressure
    try:
        slope, _ = np.polyfit(pressures, rates, 1)
    except np.linalg.LinAlgError:
        return rates.mean()

    # α = base rate - degradation factor
    base_rate = rates[pressures == 0].mean() if (pressures == 0).any() else rates.mean()

    # Normalize: if no degradation (slope=0), α = base_rate
    # If severe degradation (slope=-1), α approaches 0
    alpha = base_rate + slope * 0.5  # 0.5 is reference pressure point

    return max(0.0, min(1.0, alpha))


def emit_entropy_receipt(
    metric_type: str,
    value: float,
    context: dict
) -> dict:
    """Emit entropy-related receipt."""
    return emit_receipt(f"entropy_{metric_type}", {
        "tenant_id": TENANT_ID,
        "metric_type": metric_type,
        "value": value,
        "context": context
    })
