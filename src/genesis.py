"""
Genesis Module - Pattern crystallization into watchers.

What bleeds, breeds. Recurring wound patterns crystallize into watchers.
"""

from typing import Any
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import uuid

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    GENESIS_AUTOCATALYSIS_THRESHOLD,
)
from .watcher import create_watcher, spawn_watcher, check_autocatalysis


def harvest_wounds(receipts: list, days: int = 30) -> list:
    """
    Collect wound_receipts from last N days.

    Args:
        receipts: All receipts
        days: Number of days to look back

    Returns:
        List of wound receipts from the period
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    wounds = []
    for r in receipts:
        # Check if it's a wound receipt
        receipt_type = r.get("receipt_type", "")
        if "wound" in receipt_type or "anomaly" in receipt_type or "violation" in receipt_type:
            # Parse timestamp
            try:
                ts = datetime.fromisoformat(r.get("ts", "").replace("Z", ""))
                if ts >= cutoff:
                    wounds.append(r)
            except (ValueError, TypeError):
                # If timestamp invalid, include it (conservative)
                wounds.append(r)

    return wounds


def identify_patterns(wounds: list) -> list:
    """
    Group wounds by type, find recurring patterns.

    Args:
        wounds: List of wound receipts

    Returns:
        List of pattern dicts
    """
    patterns = []

    # Group by wound type/receipt type
    type_groups = defaultdict(list)
    for w in wounds:
        wound_type = w.get("wound_type", w.get("receipt_type", "unknown"))
        type_groups[wound_type].append(w)

    # Analyze each group
    for wound_type, group in type_groups.items():
        if len(group) >= GENESIS_AUTOCATALYSIS_THRESHOLD:
            # Calculate statistics
            amounts = [w.get("amount_usd", 0) for w in group if w.get("amount_usd")]
            probabilities = [w.get("fraud_probability", 0) for w in group if w.get("fraud_probability")]

            pattern = {
                "pattern_id": f"pattern-{uuid.uuid4().hex[:8]}",
                "wound_type": wound_type,
                "occurrence_count": len(group),
                "first_occurrence": min(w.get("ts", "") for w in group),
                "last_occurrence": max(w.get("ts", "") for w in group),
                "avg_amount_usd": sum(amounts) / len(amounts) if amounts else 0,
                "avg_fraud_probability": sum(probabilities) / len(probabilities) if probabilities else 0,
                "sample_wounds": group[:5],  # Keep first 5 as samples
                "is_recurring": True,
                "exceeds_threshold": len(group) >= GENESIS_AUTOCATALYSIS_THRESHOLD
            }
            patterns.append(pattern)

    return patterns


def synthesize_blueprint(pattern: dict) -> dict:
    """
    Create watcher blueprint from wound pattern.

    Args:
        pattern: Pattern dict from identify_patterns

    Returns:
        Watcher blueprint dict
    """
    wound_type = pattern.get("wound_type", "unknown")

    # Create trigger condition
    def make_trigger(wt, min_prob):
        def trigger(receipt):
            rt = receipt.get("receipt_type", "")
            prob = receipt.get("fraud_probability", 0)
            return (wt in rt or rt == wt) and prob >= min_prob
        return trigger

    min_probability = max(0.5, pattern.get("avg_fraud_probability", 0.5) - 0.1)

    blueprint = {
        "id": f"genesis-{uuid.uuid4().hex[:8]}",
        "pattern_id": pattern.get("pattern_id"),
        "pattern_name": f"genesis_{wound_type}",
        "wound_type": wound_type,
        "trigger_condition": make_trigger(wound_type, min_probability),
        "occurrence_threshold": pattern.get("occurrence_count", GENESIS_AUTOCATALYSIS_THRESHOLD),
        "probability_threshold": min_probability,
        "synthesized_at": datetime.utcnow().isoformat() + "Z",
        "status": "blueprint",
        "source_pattern": pattern
    }

    emit_receipt("genesis_blueprint", {
        "tenant_id": TENANT_ID,
        "blueprint_id": blueprint["id"],
        "pattern_id": pattern.get("pattern_id"),
        "wound_type": wound_type,
        "occurrence_count": pattern.get("occurrence_count"),
        "probability_threshold": min_probability
    })

    return blueprint


def emit_genesis_receipt(blueprint: dict) -> dict:
    """
    Emit genesis_birth_receipt when watcher spawns.

    Args:
        blueprint: Watcher blueprint that was activated

    Returns:
        Genesis birth receipt
    """
    return emit_receipt("genesis_birth", {
        "tenant_id": TENANT_ID,
        "watcher_id": blueprint.get("id"),
        "pattern_name": blueprint.get("pattern_name"),
        "wound_type": blueprint.get("wound_type"),
        "occurrence_threshold": blueprint.get("occurrence_threshold"),
        "probability_threshold": blueprint.get("probability_threshold"),
        "source_pattern_id": blueprint.get("pattern_id"),
        "birth_time": datetime.utcnow().isoformat() + "Z"
    })


def run_genesis_cycle(receipts: list, existing_watchers: list = None) -> dict:
    """
    Run one genesis cycle: harvest wounds → identify patterns → synthesize watchers.

    Args:
        receipts: All receipts in the system
        existing_watchers: List of already-active watchers

    Returns:
        Genesis cycle results
    """
    existing_watchers = existing_watchers or []
    existing_patterns = set(w.get("pattern_name", "") for w in existing_watchers)

    results = {
        "wounds_harvested": 0,
        "patterns_identified": 0,
        "watchers_spawned": 0,
        "new_watchers": [],
        "patterns": []
    }

    # Harvest wounds
    wounds = harvest_wounds(receipts, days=30)
    results["wounds_harvested"] = len(wounds)

    if not wounds:
        return results

    # Identify patterns
    patterns = identify_patterns(wounds)
    results["patterns_identified"] = len(patterns)
    results["patterns"] = patterns

    # Synthesize watchers for new patterns
    for pattern in patterns:
        if pattern.get("exceeds_threshold"):
            pattern_name = f"genesis_{pattern.get('wound_type', 'unknown')}"

            # Skip if watcher already exists for this pattern
            if pattern_name in existing_patterns:
                continue

            blueprint = synthesize_blueprint(pattern)

            # Activate the watcher
            blueprint["status"] = "active"
            results["new_watchers"].append(blueprint)
            results["watchers_spawned"] += 1

            # Emit birth receipt
            emit_genesis_receipt(blueprint)

    return results


def detect_emerging_scandal(
    receipts: list,
    scandal_indicators: list = None
) -> list:
    """
    Detect TSU-type emerging scandals from receipt patterns.

    Args:
        receipts: Recent receipts
        scandal_indicators: Optional list of indicator patterns

    Returns:
        List of emerging scandal detections
    """
    scandal_indicators = scandal_indicators or [
        {"type": "audit_delay", "threshold": 2, "weight": 0.3},
        {"type": "unauthorized", "threshold": 5, "weight": 0.4},
        {"type": "political_timing", "threshold": 0.5, "weight": 0.3}
    ]

    emerging_scandals = []

    # Group receipts by entity
    entity_receipts = defaultdict(list)
    for r in receipts:
        entity = r.get("entity", r.get("contractor_name", r.get("trust_name", "unknown")))
        entity_receipts[entity].append(r)

    # Check each entity for scandal indicators
    for entity, entity_r in entity_receipts.items():
        scandal_score = 0.0
        indicators_found = []

        for indicator in scandal_indicators:
            ind_type = indicator["type"]
            threshold = indicator["threshold"]
            weight = indicator["weight"]

            # Count matching receipts
            matches = sum(1 for r in entity_r if ind_type in r.get("receipt_type", "").lower())

            if matches >= threshold:
                scandal_score += weight
                indicators_found.append({
                    "type": ind_type,
                    "count": matches,
                    "threshold": threshold
                })

        if scandal_score >= 0.5:
            emerging_scandals.append({
                "entity": entity,
                "scandal_score": scandal_score,
                "indicators": indicators_found,
                "receipt_count": len(entity_r),
                "detected_at": datetime.utcnow().isoformat() + "Z"
            })

            emit_receipt("emerging_scandal", {
                "tenant_id": TENANT_ID,
                "entity": entity,
                "scandal_score": scandal_score,
                "indicator_count": len(indicators_found),
                "receipt_count": len(entity_r)
            })

    return emerging_scandals


def crystallize_scandal_watcher(scandal: dict) -> dict:
    """
    Crystallize an emerging scandal detection into a permanent watcher.

    Args:
        scandal: Emerging scandal dict

    Returns:
        Crystallized watcher
    """
    entity = scandal.get("entity", "unknown")

    def make_entity_trigger(e):
        def trigger(receipt):
            return (
                receipt.get("entity", "") == e or
                receipt.get("contractor_name", "") == e or
                receipt.get("trust_name", "") == e
            )
        return trigger

    watcher = create_watcher(
        pattern_name=f"scandal_{entity.lower().replace(' ', '_')}",
        trigger_condition=make_entity_trigger(entity)
    )

    watcher["status"] = "active"
    watcher["scandal_source"] = scandal
    watcher["is_autocatalytic"] = scandal.get("scandal_score", 0) >= 0.8

    emit_receipt("scandal_watcher_crystallized", {
        "tenant_id": TENANT_ID,
        "watcher_id": watcher["id"],
        "entity": entity,
        "scandal_score": scandal.get("scandal_score"),
        "is_autocatalytic": watcher["is_autocatalytic"]
    })

    return watcher
