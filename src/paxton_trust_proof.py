"""
Paxton Blind Trust Disbursement Detection.

Detects blind trust anomalies:
- Disbursements to trust creators (self-dealing)
- Legal fee payments from trust
- Unsealing of previously confidential records

Key data:
- $20,000 disbursement to Ken and Angela Paxton for legal fees
- Records unsealed December 19, 2025
"""

from typing import Any
from datetime import datetime

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    PAXTON_TRUST_DISBURSEMENT_USD,
)


def ingest_trust_disbursement(disbursement: dict) -> dict:
    """
    Ingest trust payment, emit trust_ingest_receipt.

    Args:
        disbursement: Trust disbursement record

    Returns:
        Enriched disbursement with analysis flags
    """
    # Check for self-dealing indicators
    beneficiary = disbursement.get("beneficiary", "").lower()
    trustor = disbursement.get("trustor", "").lower()
    purpose = disbursement.get("purpose", "").lower()

    flags = []
    if beneficiary == trustor or trustor in beneficiary:
        flags.append("potential_self_dealing")
    if "legal" in purpose and beneficiary == trustor:
        flags.append("legal_fee_to_trustor")
    if disbursement.get("was_sealed", False):
        flags.append("previously_sealed")

    enriched = {
        **disbursement,
        "self_dealing_flags": flags,
        "flag_count": len(flags),
        "ingested": True
    }

    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "trust_disbursement",
        "trust_name": disbursement.get("trust_name", "unknown"),
        "amount_usd": disbursement.get("amount_usd", 0),
        "beneficiary": beneficiary,
        "flag_count": len(flags),
        "payload_hash": dual_hash(str(disbursement))
    })

    return enriched


def detect_self_dealing(
    disbursements: list,
    beneficiaries: list,
    purposes: list
) -> list:
    """
    Find disbursements to trust creators.

    Args:
        disbursements: List of disbursement dicts
        beneficiaries: List of allowed beneficiaries
        purposes: List of allowed purposes

    Returns:
        List of self-dealing detection dicts
    """
    self_dealing_cases = []
    allowed_beneficiaries = set(b.lower() for b in beneficiaries)
    allowed_purposes = set(p.lower() for p in purposes)

    for d in disbursements:
        trustor = d.get("trustor", "").lower()
        beneficiary = d.get("beneficiary", "").lower()
        purpose = d.get("purpose", "").lower()

        is_self_dealing = False
        reasons = []

        # Check if beneficiary is trustor or close relation
        if trustor == beneficiary:
            is_self_dealing = True
            reasons.append("beneficiary_is_trustor")

        # Check if beneficiary is not in allowed list
        if beneficiary not in allowed_beneficiaries and "trustor" not in beneficiary:
            is_self_dealing = True
            reasons.append("beneficiary_not_allowed")

        # Check purpose
        if purpose not in allowed_purposes:
            # Not automatically self-dealing, but flagged
            reasons.append("purpose_not_standard")

        # Legal fees to trustor is suspicious
        if "legal" in purpose and trustor in beneficiary:
            is_self_dealing = True
            reasons.append("legal_fee_self_payment")

        if is_self_dealing or reasons:
            self_dealing_cases.append({
                **d,
                "is_self_dealing": is_self_dealing,
                "reasons": reasons,
                "severity": "high" if is_self_dealing else "medium"
            })

    return self_dealing_cases


def analyze_trust_timing(disbursements: list, legal_events: list) -> dict:
    """
    Analyze timing of disbursements relative to legal events.

    Args:
        disbursements: List of disbursements
        legal_events: List of legal events (filings, trials, etc.)

    Returns:
        Timing analysis dict
    """
    correlations = []

    for d in disbursements:
        try:
            d_date = datetime.fromisoformat(d.get("date", "2020-01-01"))
        except (ValueError, TypeError):
            continue

        for event in legal_events:
            try:
                e_date = datetime.fromisoformat(event.get("date", "2020-01-01"))
            except (ValueError, TypeError):
                continue

            days_diff = (d_date - e_date).days

            # Disbursement within 30 days before legal event
            if -30 <= days_diff <= 0:
                correlations.append({
                    "disbursement": d,
                    "event": event,
                    "days_before_event": abs(days_diff),
                    "correlation_type": "pre_event_disbursement"
                })

            # Disbursement within 7 days after legal event
            elif 0 < days_diff <= 7:
                correlations.append({
                    "disbursement": d,
                    "event": event,
                    "days_after_event": days_diff,
                    "correlation_type": "post_event_disbursement"
                })

    return {
        "correlations": correlations,
        "correlation_count": len(correlations),
        "suspicious_timing": len(correlations) > 2
    }


def emit_trust_receipt(findings: dict) -> dict:
    """
    Emit trust_disbursement_receipt.

    Args:
        findings: Detection findings dict

    Returns:
        Trust disbursement receipt
    """
    return emit_receipt("trust_disbursement", {
        "tenant_id": TENANT_ID,
        "trust_name": findings.get("trust_name", "unknown"),
        "trustor": findings.get("trustor", "unknown"),
        "beneficiary": findings.get("beneficiary", "unknown"),
        "amount_usd": findings.get("amount_usd", 0),
        "purpose": findings.get("purpose", "unknown"),
        "is_self_dealing": findings.get("is_self_dealing", False),
        "self_dealing_probability": findings.get("self_dealing_probability", 0),
        "was_sealed": findings.get("was_sealed", False)
    })


def analyze_blind_trust(
    trust_name: str,
    disbursements: list,
    allowed_beneficiaries: list,
    allowed_purposes: list,
    legal_events: list = None
) -> dict:
    """
    Full blind trust analysis.

    Args:
        trust_name: Name of the trust
        disbursements: List of disbursements
        allowed_beneficiaries: List of allowed beneficiaries
        allowed_purposes: List of allowed purposes
        legal_events: Optional list of legal events

    Returns:
        Analysis results
    """
    legal_events = legal_events or []

    results = {
        "trust_name": trust_name,
        "total_disbursements": len(disbursements),
        "total_amount_usd": sum(d.get("amount_usd", 0) for d in disbursements),
        "self_dealing_cases": [],
        "timing_analysis": None,
        "receipts": []
    }

    # Ingest all disbursements
    for d in disbursements:
        ingest_trust_disbursement(d)

    # Detect self-dealing
    self_dealing = detect_self_dealing(disbursements, allowed_beneficiaries, allowed_purposes)
    results["self_dealing_cases"] = self_dealing
    results["self_dealing_count"] = len([s for s in self_dealing if s.get("is_self_dealing")])
    results["self_dealing_amount_usd"] = sum(
        s.get("amount_usd", 0) for s in self_dealing if s.get("is_self_dealing")
    )

    # Timing analysis
    if legal_events:
        results["timing_analysis"] = analyze_trust_timing(disbursements, legal_events)

    # Calculate overall probability
    prob = 0.0
    if results["self_dealing_count"] > 0:
        prob += 0.5
    if results["self_dealing_amount_usd"] > 10000:
        prob += 0.2
    if results.get("timing_analysis", {}).get("suspicious_timing"):
        prob += 0.2

    results["self_dealing_probability"] = min(1.0, prob)

    # Emit receipts for self-dealing cases
    for case in self_dealing:
        if case.get("is_self_dealing"):
            receipt = emit_trust_receipt({
                "trust_name": trust_name,
                "trustor": case.get("trustor"),
                "beneficiary": case.get("beneficiary"),
                "amount_usd": case.get("amount_usd", 0),
                "purpose": case.get("purpose"),
                "is_self_dealing": True,
                "self_dealing_probability": results["self_dealing_probability"],
                "was_sealed": case.get("was_sealed", False)
            })
            results["receipts"].append(receipt)

    return results


def generate_synthetic_trust_data(n_disbursements: int, self_dealing_rate: float = 0.2) -> list:
    """
    Generate synthetic trust disbursement data.

    Returns:
        List of disbursement dicts
    """
    import random

    disbursements = []

    for i in range(n_disbursements):
        is_self_dealing = random.random() < self_dealing_rate

        if is_self_dealing:
            disbursement = {
                "id": f"TRUST-{i:06d}",
                "trust_name": "Paxton Blind Trust",
                "trustor": "Ken Paxton",
                "beneficiary": random.choice(["Ken Paxton", "Angela Paxton"]),
                "amount_usd": random.uniform(5000, 50000),
                "purpose": random.choice(["legal fees", "personal expenses", "consulting"]),
                "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "was_sealed": random.random() < 0.7,
                "is_synthetic_self_dealing": True
            }
        else:
            disbursement = {
                "id": f"TRUST-{i:06d}",
                "trust_name": "Paxton Blind Trust",
                "trustor": "Ken Paxton",
                "beneficiary": random.choice(["Charity Foundation", "Investment Fund", "Trust Management Co"]),
                "amount_usd": random.uniform(1000, 20000),
                "purpose": random.choice(["charitable donation", "investment", "administrative"]),
                "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "was_sealed": random.random() < 0.3,
                "is_synthetic_self_dealing": False
            }

        disbursements.append(disbursement)

    return disbursements
