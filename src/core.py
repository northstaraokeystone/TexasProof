"""
TexasProof Core Module - CLAUDEME-compliant foundation.

Every other file imports this. Contains dual_hash, emit_receipt, merkle, StopRuleException.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from typing import Any, Union

# Try to import blake3, fallback to sha256 if not available
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False

# Constants
TENANT_ID = "texasproof"

# Receipt schema for autodocumentation
RECEIPT_SCHEMA = {
    "base_fields": {
        "receipt_type": "str",
        "ts": "ISO8601",
        "tenant_id": "str",
        "payload_hash": "sha256:blake3"
    },
    "types": [
        "ingest",
        "ols_contractor",
        "pac_influence",
        "predatory_lending",
        "unauthorized_invoice",
        "trust_disbursement",
        "prohibited_contribution",
        "wound",
        "genesis_birth",
        "sim_complete",
        "anomaly",
        "anchor",
        "baseline_scenario",
        "stress_scenario",
        "genesis_scenario",
        "colony_ridge_scenario",
        "fund_diversion_scenario",
        "godel_scenario"
    ]
}

# Monte Carlo Defaults
DEFAULT_CYCLES = 1000
DEFAULT_MONTE_CARLO_RUNS = 10000
DEFAULT_SEED = 42

# Scenario Thresholds
BASELINE_DETECTION_THRESHOLD = 0.95
STRESS_ALPHA_THRESHOLD = 0.70
STRESS_PRESSURE_LEVEL = 0.50
GENESIS_MIN_WATCHERS = 1
GENESIS_AUTOCATALYSIS_THRESHOLD = 5
COLONY_RIDGE_CHURN_THRESHOLD = 0.90
FUND_DIVERSION_THRESHOLD = 0.85

# Fraud Detection Thresholds
EMERGENCY_CONTRACT_HIGH_RISK = 0.70
PAC_CAPTURE_HIGH_RISK = 0.80
PREDATORY_FORECLOSURE_MULTIPLIER = 7.5
CHURNING_PERIOD_YEARS = 3
CHURNING_MIN_SALES = 2

# Texas Fraud Data (from Grok research)
OLS_TOTAL_SPENT_USD = 11_000_000_000
GOTHAMS_CONTRACT_USD = 65_000_000
WYNNE_CONTRACT_USD = 220_000_000
WYNNE_COST_PER_PASSENGER = 1800
TDCJ_DIVERSION_2022_USD = 359_600_000
DUNN_DONATIONS_USD = 9_700_000
WILKS_DONATIONS_USD = 4_800_000
TEXANS_UNITED_2024_USD = 3_000_000
COLONY_RIDGE_FORECLOSURE_RATE = 0.30
NATIONAL_FORECLOSURE_RATE = 0.02
IGT_FINE_USD = 180_000
PAXTON_TRUST_DISBURSEMENT_USD = 20_000

# Pass/Fail
MAX_CONSECUTIVE_FAILURES = 2
SCENARIO_NAMES = [
    "baseline",
    "stress",
    "genesis",
    "colony_ridge",
    "fund_diversion",
    "godel"
]

# Scenario tolerances (entropy conservation)
SCENARIO_TOLERANCES = {
    "baseline": 0.10,
    "stress": 0.20,
    "genesis": 0.15,
    "colony_ridge": 0.10,
    "fund_diversion": 0.15,
    "godel": 0.10
}


class StopRuleException(Exception):
    """Raised when stoprule triggers. Never catch silently."""

    def __init__(self, message: str, metric: str = "unknown", action: str = "halt"):
        super().__init__(message)
        self.metric = metric
        self.action = action


def dual_hash(data: Union[bytes, str]) -> str:
    """
    SHA256:BLAKE3 format per CLAUDEME §8. Pure function.

    Args:
        data: Bytes or string to hash

    Returns:
        String in format "sha256_hex:blake3_hex"
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    sha = hashlib.sha256(data).hexdigest()

    if HAS_BLAKE3:
        b3 = blake3.blake3(data).hexdigest()
    else:
        # Fallback: use sha256 again but with different prefix
        b3 = hashlib.sha256(b"blake3_fallback:" + data).hexdigest()

    return f"{sha}:{b3}"


def emit_receipt(receipt_type: str, data: dict, output: bool = True) -> dict:
    """
    Creates receipt with ts, tenant_id, payload_hash. Prints JSON to stdout.

    Args:
        receipt_type: Type of receipt (e.g., "ingest", "ols_contractor")
        data: Receipt payload data
        output: Whether to print to stdout (default True)

    Returns:
        Complete receipt dict
    """
    # Ensure tenant_id is set
    if "tenant_id" not in data:
        data["tenant_id"] = TENANT_ID

    # Create timestamp
    ts = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Create payload hash
    payload_hash = dual_hash(json.dumps(data, sort_keys=True))

    # Build receipt
    receipt = {
        "receipt_type": receipt_type,
        "ts": ts,
        "tenant_id": data.get("tenant_id", TENANT_ID),
        "payload_hash": payload_hash,
        **data
    }

    # Output to stdout (append-only ledger in dev mode)
    if output:
        print(json.dumps(receipt), flush=True)

    return receipt


def merkle(items: list) -> str:
    """
    Compute Merkle root using dual_hash. Handle empty and odd counts.

    Args:
        items: List of items to build tree from

    Returns:
        Merkle root hash string
    """
    if not items:
        return dual_hash(b"empty")

    # Hash each item
    hashes = [dual_hash(json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item))
              for item in items]

    # Build tree
    while len(hashes) > 1:
        # Handle odd count by duplicating last
        if len(hashes) % 2:
            hashes.append(hashes[-1])

        # Pair and hash
        hashes = [dual_hash(hashes[i] + hashes[i+1])
                  for i in range(0, len(hashes), 2)]

    return hashes[0]


def stoprule_detection_rate(rate: float, threshold: float = 0.70) -> None:
    """Stoprule for detection rate below threshold."""
    if rate < threshold:
        emit_receipt("anomaly", {
            "metric": "detection_rate",
            "baseline": threshold,
            "delta": rate - threshold,
            "classification": "degradation",
            "action": "halt"
        })
        raise StopRuleException(
            f"Detection rate {rate:.2%} below threshold {threshold:.2%}",
            metric="detection_rate",
            action="halt"
        )


def stoprule_memory(current_gb: float, max_gb: float = 8.0) -> None:
    """Stoprule for memory usage above threshold."""
    if current_gb > max_gb:
        emit_receipt("anomaly", {
            "metric": "memory_usage",
            "baseline": max_gb,
            "delta": current_gb - max_gb,
            "classification": "violation",
            "action": "compact"
        })
        raise StopRuleException(
            f"Memory usage {current_gb:.1f}GB exceeds {max_gb:.1f}GB limit",
            metric="memory_usage",
            action="compact"
        )


def stoprule_consecutive_failures(failures: int, max_failures: int = 2) -> None:
    """Stoprule for consecutive gate failures."""
    if failures > max_failures:
        emit_receipt("anomaly", {
            "metric": "consecutive_failures",
            "baseline": max_failures,
            "delta": failures - max_failures,
            "classification": "violation",
            "action": "halt"
        })
        raise StopRuleException(
            f"Consecutive failures {failures} exceeds maximum {max_failures}",
            metric="consecutive_failures",
            action="halt"
        )


def validate_receipt(receipt: dict) -> bool:
    """Validate that a receipt has all required fields."""
    required = ["receipt_type", "ts", "tenant_id", "payload_hash"]
    return all(field in receipt for field in required)


def anchor_receipts(receipts: list) -> dict:
    """Create anchor receipt for a batch of receipts."""
    return emit_receipt("anchor", {
        "merkle_root": merkle(receipts),
        "hash_algos": ["SHA256", "BLAKE3"],
        "batch_size": len(receipts),
        "tenant_id": TENANT_ID
    })
