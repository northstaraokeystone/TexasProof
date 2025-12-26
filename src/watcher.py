"""
Self-Spawning Watcher Agents per QED v12 paradigm.

Key Insight: Watchers are not objects that process receipts. Watchers ARE
self-sustaining receipt patterns. When a cluster of receipts achieves
self-reference—when the pattern predicts and emits receipts about itself—
that IS the watcher.

Spawn Conditions:
- Same wound_type appears >5 times in 30 days
- Median resolution time >30 minutes
- Pattern achieves autocatalysis (self-reference)
"""

from typing import Any, Callable
from datetime import datetime, timedelta
from collections import Counter
import uuid

from .core import (
    emit_receipt,
    dual_hash,
    merkle,
    TENANT_ID,
    GENESIS_AUTOCATALYSIS_THRESHOLD,
)
from .entropy import system_entropy, agent_fitness


def create_watcher(pattern_name: str, trigger_condition: Callable) -> dict:
    """
    Create watcher blueprint.

    Args:
        pattern_name: Name of the pattern this watcher monitors
        trigger_condition: Callable that returns True when pattern detected

    Returns:
        Watcher blueprint dict
    """
    watcher_id = f"watcher-{uuid.uuid4().hex[:8]}"

    blueprint = {
        "id": watcher_id,
        "pattern_name": pattern_name,
        "trigger_condition": trigger_condition,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "blueprint",
        "activation_count": 0,
        "receipts_emitted": 0,
        "fitness": 0.0,
        "is_autocatalytic": False
    }

    emit_receipt("watcher_blueprint", {
        "tenant_id": TENANT_ID,
        "watcher_id": watcher_id,
        "pattern_name": pattern_name,
        "status": "created"
    })

    return blueprint


def check_autocatalysis(receipts: list, pattern: dict) -> bool:
    """
    Check if pattern achieves self-reference threshold.
    Autocatalysis = pattern predicts and emits receipts about itself.

    Args:
        receipts: List of recent receipts
        pattern: Pattern dict to check

    Returns:
        True if pattern is autocatalytic
    """
    pattern_name = pattern.get("pattern_name", "")
    threshold = pattern.get("autocatalysis_threshold", GENESIS_AUTOCATALYSIS_THRESHOLD)

    # Count receipts that reference this pattern
    self_references = 0
    for r in receipts:
        payload = r.get("payload", {})
        if isinstance(payload, dict):
            # Check if receipt references the pattern
            if payload.get("pattern_name") == pattern_name:
                self_references += 1
            if payload.get("triggered_by") == pattern_name:
                self_references += 1
            if pattern_name in str(payload.get("source", "")):
                self_references += 1

    # Autocatalysis achieved when self-references exceed threshold
    return self_references >= threshold


def spawn_watcher(wound_receipts: list, threshold: int = 5) -> dict:
    """
    Spawn watcher from recurring wound patterns.

    Args:
        wound_receipts: List of wound receipts
        threshold: Minimum occurrences to spawn

    Returns:
        Spawned watcher dict (or None if threshold not met)
    """
    if len(wound_receipts) < threshold:
        return None

    # Group wounds by type
    wound_types = Counter(r.get("wound_type", "unknown") for r in wound_receipts)

    # Find most common wound type meeting threshold
    for wound_type, count in wound_types.most_common():
        if count >= threshold:
            # Calculate wound statistics
            wound_subset = [r for r in wound_receipts if r.get("wound_type") == wound_type]

            # Parse timestamps and calculate timing
            resolution_times = []
            for w in wound_subset:
                try:
                    created = datetime.fromisoformat(w.get("created_at", "").replace("Z", ""))
                    resolved = w.get("resolved_at")
                    if resolved:
                        resolved = datetime.fromisoformat(resolved.replace("Z", ""))
                        resolution_times.append((resolved - created).total_seconds() / 60)
                except (ValueError, TypeError):
                    pass

            median_resolution = sorted(resolution_times)[len(resolution_times)//2] if resolution_times else 0

            # Create watcher for this wound type
            def make_trigger(wt):
                def trigger(receipt):
                    return receipt.get("wound_type") == wt
                return trigger

            watcher = create_watcher(
                pattern_name=f"wound_{wound_type}",
                trigger_condition=make_trigger(wound_type)
            )

            # Activate immediately
            watcher["status"] = "active"
            watcher["spawn_source"] = "wound_pattern"
            watcher["wound_count"] = count
            watcher["median_resolution_minutes"] = median_resolution
            watcher["is_autocatalytic"] = count >= threshold * 2

            emit_receipt("watcher_spawned", {
                "tenant_id": TENANT_ID,
                "watcher_id": watcher["id"],
                "pattern_name": watcher["pattern_name"],
                "wound_count": count,
                "median_resolution_minutes": median_resolution,
                "is_autocatalytic": watcher["is_autocatalytic"]
            })

            return watcher

    return None


def measure_watcher_fitness(watcher: dict, receipts: list) -> float:
    """
    Measure watcher fitness: entropy reduction per receipt.
    Positive = effective watcher.

    Args:
        watcher: Watcher dict
        receipts: Recent receipt stream

    Returns:
        Fitness score (positive = effective)
    """
    if not receipts:
        return 0.0

    # Split receipts by watcher activation
    trigger = watcher.get("trigger_condition")
    if not callable(trigger):
        return 0.0

    # Find activation points
    activations = []
    for i, r in enumerate(receipts):
        try:
            if trigger(r):
                activations.append(i)
        except (TypeError, ValueError):
            pass

    if not activations:
        return 0.0

    # Calculate entropy before/after each activation
    total_fitness = 0.0
    for act_idx in activations:
        before = receipts[max(0, act_idx-10):act_idx]
        after = receipts[act_idx:min(len(receipts), act_idx+10)]

        if before and after:
            fitness = agent_fitness(before, after, 1)
            total_fitness += fitness

    avg_fitness = total_fitness / len(activations) if activations else 0.0

    # Update watcher
    watcher["fitness"] = avg_fitness
    watcher["activation_count"] = len(activations)

    return avg_fitness


def run_watcher_cycle(watchers: list, receipts: list) -> list:
    """
    Run one cycle of all active watchers.

    Args:
        watchers: List of active watchers
        receipts: New receipts to process

    Returns:
        List of triggered watcher responses
    """
    responses = []

    for watcher in watchers:
        if watcher.get("status") != "active":
            continue

        trigger = watcher.get("trigger_condition")
        if not callable(trigger):
            continue

        for receipt in receipts:
            try:
                if trigger(receipt):
                    response = {
                        "watcher_id": watcher["id"],
                        "pattern_name": watcher["pattern_name"],
                        "triggered_by": receipt,
                        "action": "alert",
                        "ts": datetime.utcnow().isoformat() + "Z"
                    }
                    responses.append(response)
                    watcher["activation_count"] = watcher.get("activation_count", 0) + 1

                    emit_receipt("watcher_triggered", {
                        "tenant_id": TENANT_ID,
                        "watcher_id": watcher["id"],
                        "pattern_name": watcher["pattern_name"],
                        "receipt_type": receipt.get("receipt_type"),
                        "activation_count": watcher["activation_count"]
                    })
            except (TypeError, ValueError):
                pass

    return responses


def deactivate_watcher(watcher: dict, reason: str = "manual") -> dict:
    """
    Deactivate a watcher.

    Args:
        watcher: Watcher to deactivate
        reason: Reason for deactivation

    Returns:
        Updated watcher dict
    """
    watcher["status"] = "inactive"
    watcher["deactivated_at"] = datetime.utcnow().isoformat() + "Z"
    watcher["deactivation_reason"] = reason

    emit_receipt("watcher_deactivated", {
        "tenant_id": TENANT_ID,
        "watcher_id": watcher["id"],
        "pattern_name": watcher["pattern_name"],
        "reason": reason,
        "total_activations": watcher.get("activation_count", 0),
        "final_fitness": watcher.get("fitness", 0)
    })

    return watcher


def create_fraud_vector_watchers() -> list:
    """
    Create default watchers for Texas fraud vectors.

    Returns:
        List of fraud vector watchers
    """
    watchers = []

    # OLS contractor watcher
    watchers.append(create_watcher(
        pattern_name="ols_high_risk",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "ols_contractor" and
            r.get("fraud_probability", 0) >= 0.7
        )
    ))

    # PAC influence watcher
    watchers.append(create_watcher(
        pattern_name="pac_capture",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "pac_influence" and
            r.get("capture_probability", 0) >= 0.8
        )
    ))

    # Predatory lending watcher
    watchers.append(create_watcher(
        pattern_name="predatory_churn",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "predatory_lending" and
            r.get("churn_count", 0) >= 2
        )
    ))

    # TSU unauthorized invoice watcher
    watchers.append(create_watcher(
        pattern_name="unauthorized_invoice",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "unauthorized_invoice" and
            r.get("unauthorized_count", 0) > 0
        )
    ))

    # Trust self-dealing watcher
    watchers.append(create_watcher(
        pattern_name="trust_self_dealing",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "trust_disbursement" and
            r.get("is_self_dealing", False)
        )
    ))

    # Prohibited contribution watcher
    watchers.append(create_watcher(
        pattern_name="prohibited_contribution",
        trigger_condition=lambda r: (
            r.get("receipt_type") == "prohibited_contribution" and
            r.get("is_state_contractor", False)
        )
    ))

    # Activate all
    for w in watchers:
        w["status"] = "active"

    return watchers
