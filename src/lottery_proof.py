"""
IGT Lottery Prohibited Contribution Detection.

Detects IGT-style prohibited political contributions:
- State contractors making political contributions
- Contributions to prohibited entities (caucuses)
- Violation of contribution bans

Key data:
- IGT fined $180,000 for prohibited contributions to legislative caucuses
"""

from typing import Any

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    IGT_FINE_USD,
)


def ingest_contribution(contribution: dict) -> dict:
    """
    Ingest political contribution.

    Args:
        contribution: Contribution record dict

    Returns:
        Enriched contribution with analysis
    """
    contributor = contribution.get("contributor", "")
    recipient_type = contribution.get("recipient_type", "").lower()
    is_contractor = contribution.get("is_state_contractor", False)

    flags = []
    if is_contractor and recipient_type in ["caucus", "legislative_caucus", "pac"]:
        flags.append("prohibited_contractor_contribution")
    if "caucus" in recipient_type and is_contractor:
        flags.append("caucus_contribution_by_contractor")

    enriched = {
        **contribution,
        "prohibition_flags": flags,
        "is_prohibited": len(flags) > 0,
        "ingested": True
    }

    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "political_contribution",
        "contributor": contributor,
        "recipient": contribution.get("recipient", "unknown"),
        "amount_usd": contribution.get("amount_usd", 0),
        "flag_count": len(flags),
        "payload_hash": dual_hash(str(contribution))
    })

    return enriched


def detect_prohibited_recipient(
    contributions: list,
    prohibited_list: list
) -> list:
    """
    Find contributions to prohibited entities.

    Args:
        contributions: List of contribution dicts
        prohibited_list: List of prohibited recipient types/names

    Returns:
        List of prohibited contribution dicts
    """
    prohibited_set = set(p.lower() for p in prohibited_list)
    prohibited_contributions = []

    for c in contributions:
        recipient = c.get("recipient", "").lower()
        recipient_type = c.get("recipient_type", "").lower()
        is_contractor = c.get("is_state_contractor", False)

        is_prohibited = False
        reasons = []

        # Check if recipient or type is in prohibited list
        if recipient in prohibited_set or recipient_type in prohibited_set:
            is_prohibited = True
            reasons.append("recipient_prohibited")

        # State contractors have additional restrictions
        if is_contractor:
            if recipient_type in ["caucus", "legislative_caucus"]:
                is_prohibited = True
                reasons.append("contractor_caucus_contribution")
            if recipient_type == "pac" and c.get("pac_type") == "political":
                is_prohibited = True
                reasons.append("contractor_political_pac")

        if is_prohibited:
            prohibited_contributions.append({
                **c,
                "is_prohibited": True,
                "prohibition_reasons": reasons,
                "penalty_estimate_usd": calculate_penalty(c.get("amount_usd", 0), reasons)
            })

    return prohibited_contributions


def calculate_penalty(amount: float, reasons: list) -> float:
    """
    Estimate penalty for prohibited contribution.

    Args:
        amount: Contribution amount
        reasons: List of violation reasons

    Returns:
        Estimated penalty amount
    """
    # Base penalty is typically 2x the contribution
    base_penalty = amount * 2

    # Additional penalty factors
    multiplier = 1.0
    if "contractor_caucus_contribution" in reasons:
        multiplier += 0.5
    if len(reasons) > 1:
        multiplier += 0.25

    return base_penalty * multiplier


def detect_contractor_status(
    contributions: list,
    state_contracts: list
) -> list:
    """
    Cross-reference contributions with state contracts to identify contractors.

    Args:
        contributions: List of contributions
        state_contracts: List of state contracts

    Returns:
        Enriched contributions with contractor status
    """
    # Build contractor set from contracts
    contractors = set()
    for contract in state_contracts:
        contractor_name = contract.get("contractor", "").lower()
        if contractor_name:
            contractors.add(contractor_name)
            # Add variations
            contractors.add(contractor_name.replace(" inc", ""))
            contractors.add(contractor_name.replace(" llc", ""))
            contractors.add(contractor_name.replace(" corp", ""))

    # Enrich contributions
    enriched = []
    for c in contributions:
        contributor = c.get("contributor", "").lower()
        is_contractor = (
            contributor in contractors or
            any(contractor in contributor for contractor in contractors) or
            any(contributor in contractor for contractor in contractors)
        )

        enriched.append({
            **c,
            "is_state_contractor": is_contractor,
            "contractor_match_method": "exact" if contributor in contractors else "partial"
        })

    return enriched


def emit_lottery_receipt(findings: dict) -> dict:
    """
    Emit prohibited_contribution_receipt.

    Args:
        findings: Detection findings dict

    Returns:
        Prohibited contribution receipt
    """
    return emit_receipt("prohibited_contribution", {
        "tenant_id": TENANT_ID,
        "contributor": findings.get("contributor", "unknown"),
        "recipient": findings.get("recipient", "unknown"),
        "recipient_type": findings.get("recipient_type", "unknown"),
        "amount_usd": findings.get("amount_usd", 0),
        "is_state_contractor": findings.get("is_state_contractor", False),
        "prohibition_reasons": findings.get("prohibition_reasons", []),
        "penalty_estimate_usd": findings.get("penalty_estimate_usd", 0),
        "violation_probability": findings.get("violation_probability", 0)
    })


def analyze_contractor_contributions(
    contributions: list,
    state_contracts: list,
    prohibited_recipients: list = None
) -> dict:
    """
    Full contractor contribution analysis.

    Args:
        contributions: List of contributions
        state_contracts: List of state contracts
        prohibited_recipients: Optional list of prohibited recipients

    Returns:
        Analysis results
    """
    prohibited_recipients = prohibited_recipients or [
        "caucus", "legislative_caucus", "legislative caucus"
    ]

    results = {
        "total_contributions": len(contributions),
        "contractor_contributions": [],
        "prohibited_contributions": [],
        "total_prohibited_amount_usd": 0,
        "estimated_penalties_usd": 0,
        "receipts": []
    }

    # Identify contractor contributions
    enriched = detect_contractor_status(contributions, state_contracts)
    results["contractor_contributions"] = [c for c in enriched if c.get("is_state_contractor")]
    results["contractor_contribution_count"] = len(results["contractor_contributions"])

    # Detect prohibited contributions
    prohibited = detect_prohibited_recipient(enriched, prohibited_recipients)
    results["prohibited_contributions"] = prohibited
    results["prohibited_count"] = len(prohibited)
    results["total_prohibited_amount_usd"] = sum(p.get("amount_usd", 0) for p in prohibited)
    results["estimated_penalties_usd"] = sum(p.get("penalty_estimate_usd", 0) for p in prohibited)

    # Emit receipts for prohibited contributions
    for p in prohibited:
        receipt = emit_lottery_receipt({
            "contributor": p.get("contributor"),
            "recipient": p.get("recipient"),
            "recipient_type": p.get("recipient_type"),
            "amount_usd": p.get("amount_usd", 0),
            "is_state_contractor": p.get("is_state_contractor"),
            "prohibition_reasons": p.get("prohibition_reasons", []),
            "penalty_estimate_usd": p.get("penalty_estimate_usd", 0),
            "violation_probability": 0.95 if p.get("is_state_contractor") else 0.7
        })
        results["receipts"].append(receipt)

    return results


def generate_synthetic_lottery_data(
    n_contributions: int,
    n_contracts: int,
    violation_rate: float = 0.15
) -> tuple:
    """
    Generate synthetic lottery/contractor contribution data.

    Returns:
        Tuple of (contributions, contracts)
    """
    import random

    companies = [
        "IGT", "Scientific Games", "Pollard Banknote", "Intralot",
        "Tech Corp", "Services Inc", "Solutions LLC", "Consulting Group"
    ]

    recipients = [
        ("House Republican Caucus", "caucus"),
        ("Senate Democratic Caucus", "caucus"),
        ("Speaker's PAC", "pac"),
        ("Lt Governor PAC", "pac"),
        ("Texas House Campaign", "campaign"),
        ("State Senator Campaign", "campaign")
    ]

    # Generate contracts
    contracts = []
    for i in range(n_contracts):
        contracts.append({
            "id": f"CONTRACT-{i:06d}",
            "contractor": random.choice(companies[:4]),  # First 4 are contractors
            "amount_usd": random.uniform(100000, 10000000),
            "type": "state_lottery" if random.random() < 0.5 else "general"
        })

    # Generate contributions
    contributions = []
    for i in range(n_contributions):
        is_violation = random.random() < violation_rate
        recipient_name, recipient_type = random.choice(recipients)

        if is_violation:
            contribution = {
                "id": f"CONTRIB-{i:06d}",
                "contributor": random.choice(companies[:4]),  # Contractor
                "recipient": recipient_name,
                "recipient_type": recipient_type,
                "amount_usd": random.uniform(5000, 50000),
                "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "is_synthetic_violation": True
            }
        else:
            contribution = {
                "id": f"CONTRIB-{i:06d}",
                "contributor": random.choice(companies[4:]),  # Non-contractor
                "recipient": recipient_name,
                "recipient_type": recipient_type,
                "amount_usd": random.uniform(500, 10000),
                "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "is_synthetic_violation": False
            }

        contributions.append(contribution)

    return contributions, contracts
