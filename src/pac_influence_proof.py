"""
PAC Influence Pipeline Detection.

Detects Dunn/Wilks-style PAC→primary purge→policy influence pipelines:
Large donor → PAC → Primary challenge funding → Vote outcome correlation → Policy alignment

$14M+ Dunn/Wilks donations:
- Tim Dunn: $9.7M to Defend Texas Liberty
- Farris Wilks: $4.8M to Defend Texas Liberty
- Texans United: $3M targeting Paxton impeachment voters
"""

from typing import Any

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    PAC_CAPTURE_HIGH_RISK,
    DUNN_DONATIONS_USD,
    WILKS_DONATIONS_USD,
    TEXANS_UNITED_2024_USD,
)
from .entropy import pac_flow_entropy


def ingest_pac_filing(filing: dict) -> dict:
    """
    Ingest PAC filing, emit pac_ingest_receipt. Return enriched filing.

    Args:
        filing: PAC filing dict

    Returns:
        Enriched filing with analysis
    """
    enriched = {
        **filing,
        "ingested": True,
        "analysis_pending": True
    }

    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "pac_filing",
        "pac_name": filing.get("pac_name", "unknown"),
        "total_usd": filing.get("total_usd", 0),
        "payload_hash": dual_hash(str(filing))
    })

    return enriched


def trace_donor_to_policy(
    donor: str,
    donations: list,
    votes: list,
    policies: list
) -> dict:
    """
    Full pipeline trace: donor → PAC → votes → policy.

    Args:
        donor: Donor name to trace
        donations: List of donation dicts
        votes: List of legislative vote dicts
        policies: List of policy outcome dicts

    Returns:
        Influence chain dict
    """
    chain = {
        "donor": donor,
        "donations": [],
        "influenced_votes": [],
        "aligned_policies": [],
        "capture_probability": 0.0
    }

    # Find donations from this donor
    donor_lower = donor.lower()
    total_donated = 0
    pacs_funded = set()

    for d in donations:
        if d.get("donor", "").lower() == donor_lower:
            chain["donations"].append(d)
            total_donated += d.get("amount", 0)
            pacs_funded.add(d.get("pac_name", ""))

    chain["total_donated_usd"] = total_donated
    chain["pacs_funded"] = list(pacs_funded)

    # Find votes influenced by these PACs
    for vote in votes:
        # Check if PAC recipients voted in donor's interest
        voter_pac = vote.get("funded_by_pac", "")
        if voter_pac in pacs_funded:
            chain["influenced_votes"].append(vote)

    # Find policies that align with donor interests
    for policy in policies:
        beneficiaries = policy.get("beneficiaries", [])
        if donor_lower in [b.lower() for b in beneficiaries]:
            chain["aligned_policies"].append(policy)

    # Compute capture probability
    if total_donated > 1_000_000:
        base_prob = 0.5
    elif total_donated > 100_000:
        base_prob = 0.3
    else:
        base_prob = 0.1

    # Increase based on influence success
    if len(chain["influenced_votes"]) > 0:
        vote_influence = min(0.3, len(chain["influenced_votes"]) * 0.05)
        base_prob += vote_influence

    if len(chain["aligned_policies"]) > 0:
        policy_influence = min(0.2, len(chain["aligned_policies"]) * 0.1)
        base_prob += policy_influence

    chain["capture_probability"] = min(1.0, base_prob)

    return chain


def detect_primary_purge(
    challenges: list,
    outcomes: list,
    impeachment_votes: list
) -> list:
    """
    Correlate PAC funding with impeachment vote retaliation.

    Pattern:
    1. Legislator votes to impeach
    2. PAC funds primary challenger
    3. Incumbent loses or changes behavior

    Args:
        challenges: List of primary challenge dicts
        outcomes: List of election outcome dicts
        impeachment_votes: List of impeachment vote records

    Returns:
        List of purge correlation dicts
    """
    purges = []

    # Build impeachment voter set
    impeach_voters = {}
    for vote in impeachment_votes:
        if vote.get("vote") in ["yes", "aye", "for"]:
            voter = vote.get("legislator", "").lower()
            impeach_voters[voter] = vote

    # Find challenges against impeachment voters
    for challenge in challenges:
        incumbent = challenge.get("incumbent", "").lower()
        challenger = challenge.get("challenger", "")
        pac_funding = challenge.get("pac_funding_usd", 0)
        pac_name = challenge.get("pac_name", "")

        if incumbent in impeach_voters:
            # Find outcome
            outcome = None
            for o in outcomes:
                if o.get("incumbent", "").lower() == incumbent:
                    outcome = o
                    break

            purge = {
                "incumbent": incumbent,
                "impeachment_vote": impeach_voters[incumbent],
                "challenger": challenger,
                "pac_name": pac_name,
                "pac_funding_usd": pac_funding,
                "outcome": outcome,
                "purge_successful": outcome.get("winner") == challenger if outcome else False,
                "retaliation_probability": 0.9 if pac_funding > 100000 else 0.5
            }
            purges.append(purge)

    return purges


def score_influence_capture(donations: list, policy_outcomes: list) -> float:
    """
    Compute probability of policy capture. ≥0.8 = high capture.

    Args:
        donations: List of donations
        policy_outcomes: List of policy outcomes

    Returns:
        Capture probability 0-1
    """
    if not donations or not policy_outcomes:
        return 0.0

    # Use entropy-based correlation
    entropy = pac_flow_entropy(donations, policy_outcomes)

    # Low entropy = high correlation = high capture probability
    # (deterministic donor→policy relationship is suspicious)
    capture_prob = 1.0 - entropy

    # Adjust based on donation magnitude
    total_donations = sum(d.get("amount", 0) for d in donations)
    if total_donations > 10_000_000:
        capture_prob = min(1.0, capture_prob + 0.2)
    elif total_donations > 1_000_000:
        capture_prob = min(1.0, capture_prob + 0.1)

    return capture_prob


def emit_pac_receipt(findings: dict) -> dict:
    """
    Emit pac_influence_receipt with capture probability.

    Args:
        findings: Detection findings dict

    Returns:
        PAC influence receipt
    """
    return emit_receipt("pac_influence", {
        "tenant_id": TENANT_ID,
        "donor_name": findings.get("donor_name", "unknown"),
        "total_donated_usd": findings.get("total_donated_usd", 0),
        "pac_name": findings.get("pac_name", "unknown"),
        "primary_challenges_funded": findings.get("primary_challenges_funded", 0),
        "successful_purges": findings.get("successful_purges", 0),
        "vote_correlation": findings.get("vote_correlation", 0.0),
        "policy_alignment_score": findings.get("policy_alignment_score", 0.0),
        "capture_probability": findings.get("capture_probability", 0.0)
    })


def analyze_pac_influence(
    donations: list,
    challenges: list,
    votes: list,
    policies: list
) -> dict:
    """
    Full PAC influence analysis.

    Args:
        donations: List of PAC donations
        challenges: List of primary challenges
        votes: List of legislative votes
        policies: List of policy outcomes

    Returns:
        Analysis results with receipts
    """
    results = {
        "total_analyzed": len(donations),
        "high_capture_count": 0,
        "donor_chains": [],
        "purges_detected": [],
        "receipts": []
    }

    # Group donations by donor
    donors = {}
    for d in donations:
        donor = d.get("donor", "unknown")
        if donor not in donors:
            donors[donor] = []
        donors[donor].append(d)

    # Trace each major donor
    for donor, donor_donations in donors.items():
        total = sum(d.get("amount", 0) for d in donor_donations)
        if total > 100000:  # Only analyze significant donors
            chain = trace_donor_to_policy(donor, donations, votes, policies)
            results["donor_chains"].append(chain)

            if chain["capture_probability"] >= PAC_CAPTURE_HIGH_RISK:
                results["high_capture_count"] += 1

            receipt = emit_pac_receipt({
                "donor_name": donor,
                "total_donated_usd": total,
                "pac_name": donor_donations[0].get("pac_name", "unknown"),
                "primary_challenges_funded": len(chain.get("influenced_votes", [])),
                "successful_purges": len([p for p in results["purges_detected"] if p.get("purge_successful")]),
                "vote_correlation": len(chain.get("influenced_votes", [])) / max(len(votes), 1),
                "policy_alignment_score": len(chain.get("aligned_policies", [])) / max(len(policies), 1),
                "capture_probability": chain["capture_probability"]
            })
            results["receipts"].append(receipt)

    # Detect primary purges
    impeachment_votes = [v for v in votes if v.get("vote_type") == "impeachment"]
    results["purges_detected"] = detect_primary_purge(challenges, [], impeachment_votes)

    return results


def generate_synthetic_pac_data(
    n_donations: int,
    n_challenges: int,
    capture_rate: float = 0.3
) -> tuple:
    """
    Generate synthetic PAC data for simulation.

    Returns:
        Tuple of (donations, challenges, votes, policies)
    """
    import random

    donors = [
        "Tim Dunn", "Farris Wilks", "Dan Wilks", "Stacy Hock",
        "Michael Dell", "John Arnold", "Laura Arnold"
    ]

    pacs = [
        "Defend Texas Liberty", "Texans United for a Conservative Majority",
        "Texans for Fiscal Responsibility", "Texas First PAC"
    ]

    legislators = [f"Rep_{i}" for i in range(50)]

    # Generate donations
    donations = []
    for i in range(n_donations):
        is_capture = random.random() < capture_rate
        donor = random.choice(donors[:2] if is_capture else donors[2:])

        donations.append({
            "id": f"DON-{i:06d}",
            "donor": donor,
            "amount": random.uniform(100000, 1000000) if is_capture else random.uniform(1000, 50000),
            "pac_name": random.choice(pacs[:2] if is_capture else pacs[2:]),
            "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "is_synthetic_capture": is_capture
        })

    # Generate challenges
    challenges = []
    for i in range(n_challenges):
        is_purge = random.random() < capture_rate

        challenges.append({
            "id": f"CHAL-{i:06d}",
            "incumbent": random.choice(legislators),
            "challenger": f"Challenger_{i}",
            "pac_name": random.choice(pacs[:2] if is_purge else pacs[2:]),
            "pac_funding_usd": random.uniform(200000, 500000) if is_purge else random.uniform(10000, 50000),
            "is_synthetic_purge": is_purge
        })

    # Generate votes
    votes = []
    for leg in legislators[:20]:
        votes.append({
            "legislator": leg,
            "vote_type": "impeachment",
            "vote": random.choice(["yes", "no"]),
            "funded_by_pac": random.choice(pacs) if random.random() < 0.5 else ""
        })

    # Generate policies
    policies = []
    for i in range(10):
        policies.append({
            "id": f"POL-{i:06d}",
            "name": f"Policy_{i}",
            "beneficiaries": [random.choice(donors)] if random.random() < capture_rate else [],
            "outcome": "passed" if random.random() < 0.7 else "failed"
        })

    return donations, challenges, votes, policies
