"""
Operation Lone Star Contractor Fraud Detection.

Detects emergency contract fraud loops:
Emergency declaration → No-bid contract → Contractor with donor ties → Policy influence → New emergency

$11B+ spent, including:
- Gothams: $65M emergency contract
- Wynne Transportation: $220M at $1,800/passenger
- TDCJ diversion: $359.6M shifted from prisons
"""

from typing import Any

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    EMERGENCY_CONTRACT_HIGH_RISK,
    OLS_TOTAL_SPENT_USD,
    GOTHAMS_CONTRACT_USD,
    WYNNE_CONTRACT_USD,
    WYNNE_COST_PER_PASSENGER,
    TDCJ_DIVERSION_2022_USD,
)
from .entropy import contract_entropy, entropy_fraud_score


def ingest_contract(contract: dict) -> dict:
    """
    Ingest single contract, emit ingest_receipt. Return enriched contract.

    Args:
        contract: Contract dict with name, amount, type, etc.

    Returns:
        Enriched contract with entropy and fraud scores
    """
    # Compute entropy score
    entropy = contract_entropy(contract)
    fraud_score = entropy_fraud_score(contract)

    # Enrich contract
    enriched = {
        **contract,
        "entropy_score": entropy,
        "fraud_probability": fraud_score,
        "ingested": True
    }

    # Emit receipt
    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "ols_contract",
        "contract_name": contract.get("name", "unknown"),
        "amount_usd": contract.get("amount_usd", 0),
        "payload_hash": dual_hash(str(contract))
    })

    return enriched


def detect_emergency_loop(contracts: list, donations: list) -> list:
    """
    Find contractor→donor→contract cycles.

    Pattern:
    1. Emergency contract awarded to contractor X
    2. Contractor X (or affiliate) donates to PAC/campaign
    3. Politician associated with PAC declares new emergency
    4. New contract awarded to contractor X

    Args:
        contracts: List of contract dicts
        donations: List of donation dicts

    Returns:
        List of suspicious loops
    """
    loops = []

    # Build contractor→donation mapping
    contractor_donations = {}
    for donation in donations:
        donor = donation.get("donor", "").lower()
        for contract in contracts:
            contractor = contract.get("name", "").lower()
            # Check if donor is contractor or affiliate
            if contractor in donor or donor in contractor:
                if contractor not in contractor_donations:
                    contractor_donations[contractor] = []
                contractor_donations[contractor].append(donation)

    # Find loops: emergency contract + donation + subsequent contract
    for i, contract in enumerate(contracts):
        contractor = contract.get("name", "").lower()
        contract_type = contract.get("contract_type", "").lower()

        if "emergency" in contract_type or "no-bid" in contract_type:
            # Check for donations from this contractor
            if contractor in contractor_donations:
                # Check for subsequent contracts to same contractor
                for j, subsequent in enumerate(contracts):
                    if j > i and subsequent.get("name", "").lower() == contractor:
                        loops.append({
                            "contractor": contractor,
                            "initial_contract": contract,
                            "donations": contractor_donations[contractor],
                            "subsequent_contract": subsequent,
                            "loop_type": "emergency→donor→contract",
                            "risk_score": 0.9
                        })

    return loops


def score_contract_fraud(contract: dict, donor_network: dict) -> float:
    """
    Compute fraud probability score 0-1. ≥0.7 = high fraud risk.

    Args:
        contract: Contract dict
        donor_network: Dict mapping contractors to donation info

    Returns:
        Fraud probability 0-1
    """
    score = 0.0

    # Contract type factors
    contract_type = contract.get("contract_type", "").lower()
    if "emergency" in contract_type:
        score += 0.3
    if "no-bid" in contract_type or "no_bid" in contract_type:
        score += 0.25

    # Cost anomaly
    amount = contract.get("amount_usd", 0)
    cost_per_unit = contract.get("cost_per_unit_usd", 0)
    market_rate = contract.get("market_rate_usd", cost_per_unit)

    if cost_per_unit > 0 and market_rate > 0:
        if cost_per_unit > market_rate * 3:
            score += 0.25  # >3x market rate
        elif cost_per_unit > market_rate * 2:
            score += 0.15

    # Donor correlation
    contractor_name = contract.get("name", "").lower()
    if contractor_name in donor_network:
        donation_total = donor_network[contractor_name].get("total_usd", 0)
        if donation_total > 100000:
            score += 0.3
        elif donation_total > 10000:
            score += 0.15

    # Large contract without oversight
    if amount > 50_000_000 and "no-bid" in contract_type:
        score += 0.1

    return min(1.0, score)


def detect_fund_diversion(source_budget: dict, dest_spend: dict) -> list:
    """
    Detect TDCJ→OLS-style fund diversions.

    Args:
        source_budget: Dict with department budgets
        dest_spend: Dict with destination program spending

    Returns:
        List of diversion_receipts
    """
    diversions = []

    for source, budget_info in source_budget.items():
        original = budget_info.get("original_usd", 0)
        actual = budget_info.get("actual_usd", original)
        diverted = original - actual

        if diverted > 10_000_000:  # $10M threshold
            # Find destination
            for dest, spend_info in dest_spend.items():
                original_dest = spend_info.get("original_usd", 0)
                actual_dest = spend_info.get("actual_usd", original_dest)
                increase = actual_dest - original_dest

                # Check if diversion matches destination increase
                if abs(diverted - increase) / max(diverted, 1) < 0.2:  # 20% tolerance
                    diversion = {
                        "source": source,
                        "destination": dest,
                        "amount_usd": diverted,
                        "source_impact": budget_info.get("impact", "unknown"),
                        "correlation": 1 - abs(diverted - increase) / max(diverted, 1)
                    }
                    diversions.append(diversion)

                    emit_receipt("fund_diversion", {
                        "tenant_id": TENANT_ID,
                        **diversion
                    })

    return diversions


def emit_ols_receipt(findings: dict) -> dict:
    """
    Emit ols_contractor_receipt with fraud probability.

    Args:
        findings: Detection findings dict

    Returns:
        OLS contractor receipt
    """
    return emit_receipt("ols_contractor", {
        "tenant_id": TENANT_ID,
        "contractor_name": findings.get("contractor_name", "unknown"),
        "contract_amount_usd": findings.get("contract_amount_usd", 0),
        "contract_type": findings.get("contract_type", "unknown"),
        "donor_correlation": findings.get("donor_correlation", 0.0),
        "fund_diversion_detected": findings.get("fund_diversion_detected", False),
        "fraud_probability": findings.get("fraud_probability", 0.0)
    })


def analyze_ols_contractors(contracts: list, donations: list) -> dict:
    """
    Full OLS contractor analysis.

    Args:
        contracts: List of OLS contracts
        donations: List of related donations

    Returns:
        Analysis results with receipts
    """
    results = {
        "total_analyzed": len(contracts),
        "high_risk_count": 0,
        "loops_detected": [],
        "diversions_detected": [],
        "receipts": []
    }

    # Build donor network
    donor_network = {}
    for donation in donations:
        donor = donation.get("donor", "").lower()
        if donor not in donor_network:
            donor_network[donor] = {"total_usd": 0, "donations": []}
        donor_network[donor]["total_usd"] += donation.get("amount", 0)
        donor_network[donor]["donations"].append(donation)

    # Analyze each contract
    for contract in contracts:
        enriched = ingest_contract(contract)
        fraud_score = score_contract_fraud(contract, donor_network)

        if fraud_score >= EMERGENCY_CONTRACT_HIGH_RISK:
            results["high_risk_count"] += 1

        receipt = emit_ols_receipt({
            "contractor_name": contract.get("name"),
            "contract_amount_usd": contract.get("amount_usd", 0),
            "contract_type": contract.get("contract_type"),
            "donor_correlation": enriched.get("entropy_score", 0),
            "fund_diversion_detected": False,
            "fraud_probability": fraud_score
        })
        results["receipts"].append(receipt)

    # Detect loops
    results["loops_detected"] = detect_emergency_loop(contracts, donations)

    return results


def generate_synthetic_ols_contracts(n: int, fraud_rate: float = 0.2) -> list:
    """
    Generate synthetic OLS contracts for simulation.

    Args:
        n: Number of contracts to generate
        fraud_rate: Fraction of contracts that should be fraudulent

    Returns:
        List of synthetic contract dicts
    """
    import random

    contractors = [
        "Gothams", "Wynne Transportation", "BorderGuard LLC",
        "Lone Star Security", "Texas Shield Inc", "Frontier Services",
        "Rio Grande Logistics", "Guardian Defense", "Patriot Border Co",
        "Sentinel Operations"
    ]

    contracts = []
    for i in range(n):
        is_fraud = random.random() < fraud_rate

        if is_fraud:
            contract = {
                "id": f"OLS-{i:06d}",
                "name": random.choice(contractors[:3]),  # Known problematic
                "amount_usd": random.uniform(10_000_000, 100_000_000),
                "contract_type": random.choice(["emergency", "emergency/no-bid", "no-bid"]),
                "cost_per_unit_usd": random.uniform(1500, 2500),
                "market_rate_usd": 500,
                "year": random.randint(2021, 2025),
                "is_synthetic_fraud": True
            }
        else:
            contract = {
                "id": f"OLS-{i:06d}",
                "name": random.choice(contractors[3:]),
                "amount_usd": random.uniform(100_000, 5_000_000),
                "contract_type": random.choice(["competitive", "rfp", "competitive bid"]),
                "cost_per_unit_usd": random.uniform(400, 600),
                "market_rate_usd": 500,
                "year": random.randint(2021, 2025),
                "is_synthetic_fraud": False
            }

        contracts.append(contract)

    return contracts
