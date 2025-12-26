"""
TSU Probe Detection - Unauthorized Invoice Patterns.

Detects TSU-style unauthorized invoice patterns:
Late audit filing → Unauthorized invoices → Political timing of probe announcement

Key data:
- Hundreds of millions in unauthorized invoices
- FY2023 audit: 10 months late
- FY2024 audit: 4 months late
- Probe ordered by Abbott, November 2025
"""

from typing import Any
from datetime import datetime, timedelta

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
)


def ingest_invoice(invoice: dict) -> dict:
    """
    Ingest invoice, emit invoice_ingest_receipt.

    Args:
        invoice: Invoice record dict

    Returns:
        Enriched invoice with analysis flags
    """
    # Check authorization status
    vendor = invoice.get("vendor", "")
    po_number = invoice.get("po_number", "")
    authorization = invoice.get("authorization_status", "unknown")

    flags = []
    if authorization.lower() in ["unauthorized", "none", "missing"]:
        flags.append("unauthorized")
    if not po_number:
        flags.append("no_po")
    if invoice.get("amount_usd", 0) > 100000 and not po_number:
        flags.append("high_value_no_po")

    enriched = {
        **invoice,
        "authorization_flags": flags,
        "flag_count": len(flags),
        "ingested": True
    }

    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "invoice",
        "entity": invoice.get("entity", "unknown"),
        "vendor": vendor,
        "amount_usd": invoice.get("amount_usd", 0),
        "flag_count": len(flags),
        "payload_hash": dual_hash(str(invoice))
    })

    return enriched


def detect_unauthorized(invoices: list, authorized_vendors: list) -> list:
    """
    Find invoices from non-authorized vendors.

    Args:
        invoices: List of invoice dicts
        authorized_vendors: List of authorized vendor names

    Returns:
        List of unauthorized invoice dicts
    """
    authorized_set = set(v.lower() for v in authorized_vendors)
    unauthorized = []

    for invoice in invoices:
        vendor = invoice.get("vendor", "").lower()
        auth_status = invoice.get("authorization_status", "").lower()

        is_unauthorized = (
            vendor not in authorized_set or
            auth_status in ["unauthorized", "none", "missing", "pending"]
        )

        if is_unauthorized:
            unauthorized.append({
                **invoice,
                "unauthorized_reason": "vendor_not_authorized" if vendor not in authorized_set else "status_unauthorized",
                "detected": True
            })

    return unauthorized


def detect_audit_delay(filings: list, deadlines: list) -> list:
    """
    Find late audit submissions.

    Args:
        filings: List of audit filing dicts with dates
        deadlines: List of deadline dicts with dates

    Returns:
        List of delay_receipts
    """
    delays = []

    # Build deadline lookup
    deadline_map = {d.get("fiscal_year"): d for d in deadlines}

    for filing in filings:
        fy = filing.get("fiscal_year")
        if fy not in deadline_map:
            continue

        deadline = deadline_map[fy]

        # Parse dates
        try:
            filing_date = datetime.fromisoformat(filing.get("filing_date", "2020-01-01"))
            due_date = datetime.fromisoformat(deadline.get("due_date", "2020-01-01"))
        except (ValueError, TypeError):
            continue

        delay_days = (filing_date - due_date).days

        if delay_days > 0:
            delay_months = delay_days / 30

            delay_record = {
                "fiscal_year": fy,
                "entity": filing.get("entity", "unknown"),
                "due_date": deadline.get("due_date"),
                "filing_date": filing.get("filing_date"),
                "delay_days": delay_days,
                "delay_months": round(delay_months, 1)
            }
            delays.append(delay_record)

            emit_receipt("audit_delay", {
                "tenant_id": TENANT_ID,
                "entity": filing.get("entity", "unknown"),
                "fiscal_year": fy,
                "delay_months": round(delay_months, 1)
            })

    return delays


def correlate_probe_timing(
    audit_flags: list,
    probe_date: str,
    political_events: list
) -> dict:
    """
    Detect politically-timed investigations.

    Args:
        audit_flags: List of audit red flags
        probe_date: Date probe was announced
        political_events: List of political event dicts

    Returns:
        Correlation analysis dict
    """
    try:
        probe_dt = datetime.fromisoformat(probe_date)
    except (ValueError, TypeError):
        probe_dt = datetime.now()

    # Find nearby political events
    nearby_events = []
    for event in political_events:
        try:
            event_dt = datetime.fromisoformat(event.get("date", ""))
            days_diff = abs((probe_dt - event_dt).days)
            if days_diff <= 90:  # Within 3 months
                nearby_events.append({
                    **event,
                    "days_from_probe": days_diff
                })
        except (ValueError, TypeError):
            continue

    # Calculate timing score
    timing_score = 0.0

    # More nearby political events = higher timing score
    if len(nearby_events) >= 3:
        timing_score += 0.4
    elif len(nearby_events) >= 1:
        timing_score += 0.2

    # Check for specific patterns
    for event in nearby_events:
        event_type = event.get("event_type", "").lower()
        if "election" in event_type:
            timing_score += 0.2
        if "budget" in event_type:
            timing_score += 0.15
        if "endorsement" in event_type:
            timing_score += 0.15

    # Audit flags present
    if len(audit_flags) >= 5:
        timing_score += 0.1
    elif len(audit_flags) >= 2:
        timing_score += 0.05

    # Invert: if many flags exist, probe is justified (lower political timing score)
    if len(audit_flags) >= 10:
        timing_score *= 0.5

    return {
        "probe_date": probe_date,
        "audit_flags_count": len(audit_flags),
        "nearby_political_events": nearby_events,
        "political_timing_score": min(1.0, timing_score),
        "likely_politically_motivated": timing_score > 0.5
    }


def emit_probe_receipt(findings: dict) -> dict:
    """
    Emit unauthorized_invoice_receipt.

    Args:
        findings: Detection findings dict

    Returns:
        Unauthorized invoice receipt
    """
    return emit_receipt("unauthorized_invoice", {
        "tenant_id": TENANT_ID,
        "entity": findings.get("entity", "unknown"),
        "invoice_count": findings.get("invoice_count", 0),
        "unauthorized_count": findings.get("unauthorized_count", 0),
        "unauthorized_amount_usd": findings.get("unauthorized_amount_usd", 0),
        "audit_delay_months": findings.get("audit_delay_months", 0),
        "probe_political_timing_score": findings.get("probe_political_timing_score", 0),
        "fraud_probability": findings.get("fraud_probability", 0)
    })


def analyze_entity_invoices(
    entity: str,
    invoices: list,
    authorized_vendors: list,
    audit_filings: list,
    audit_deadlines: list,
    political_events: list = None,
    probe_date: str = None
) -> dict:
    """
    Full TSU-style invoice analysis for an entity.

    Args:
        entity: Entity name
        invoices: List of invoices
        authorized_vendors: List of authorized vendors
        audit_filings: List of audit filings
        audit_deadlines: List of audit deadlines
        political_events: Optional list of political events
        probe_date: Optional probe announcement date

    Returns:
        Analysis results with receipts
    """
    political_events = political_events or []

    results = {
        "entity": entity,
        "total_invoices": len(invoices),
        "unauthorized_invoices": [],
        "audit_delays": [],
        "political_timing": None,
        "receipts": []
    }

    # Filter invoices for this entity
    entity_invoices = [i for i in invoices if i.get("entity", "").lower() == entity.lower()]

    # Detect unauthorized invoices
    unauthorized = detect_unauthorized(entity_invoices, authorized_vendors)
    results["unauthorized_invoices"] = unauthorized
    results["unauthorized_count"] = len(unauthorized)
    results["unauthorized_amount_usd"] = sum(i.get("amount_usd", 0) for i in unauthorized)

    # Detect audit delays
    entity_filings = [f for f in audit_filings if f.get("entity", "").lower() == entity.lower()]
    delays = detect_audit_delay(entity_filings, audit_deadlines)
    results["audit_delays"] = delays
    results["max_delay_months"] = max((d.get("delay_months", 0) for d in delays), default=0)

    # Correlate probe timing if applicable
    if probe_date:
        audit_flags = [{"type": "unauthorized", "count": len(unauthorized)}]
        audit_flags.extend([{"type": "delay", "months": d.get("delay_months")} for d in delays])
        timing = correlate_probe_timing(audit_flags, probe_date, political_events)
        results["political_timing"] = timing

    # Calculate fraud probability
    fraud_prob = 0.0
    if results["unauthorized_count"] > 0:
        fraud_prob += min(0.4, results["unauthorized_count"] * 0.02)
    if results["unauthorized_amount_usd"] > 10_000_000:
        fraud_prob += 0.3
    elif results["unauthorized_amount_usd"] > 1_000_000:
        fraud_prob += 0.2
    if results["max_delay_months"] > 6:
        fraud_prob += 0.2
    elif results["max_delay_months"] > 3:
        fraud_prob += 0.1

    results["fraud_probability"] = min(1.0, fraud_prob)

    # Emit receipt
    receipt = emit_probe_receipt({
        "entity": entity,
        "invoice_count": len(entity_invoices),
        "unauthorized_count": results["unauthorized_count"],
        "unauthorized_amount_usd": results["unauthorized_amount_usd"],
        "audit_delay_months": results["max_delay_months"],
        "probe_political_timing_score": results.get("political_timing", {}).get("political_timing_score", 0),
        "fraud_probability": results["fraud_probability"]
    })
    results["receipts"].append(receipt)

    return results


def generate_synthetic_tsu_data(
    n_invoices: int,
    unauthorized_rate: float = 0.2
) -> tuple:
    """
    Generate synthetic TSU-style data.

    Returns:
        Tuple of (invoices, authorized_vendors, audit_filings, deadlines)
    """
    import random

    vendors = [
        "Texas Office Supply", "Campus Maintenance Co", "IT Solutions Inc",
        "Educational Resources LLC", "Facilities Management Group",
        "Shady Consulting LLC", "No-Show Services Inc", "Ghost Vendor Co"
    ]

    authorized = vendors[:5]

    invoices = []
    for i in range(n_invoices):
        is_unauthorized = random.random() < unauthorized_rate

        if is_unauthorized:
            invoice = {
                "id": f"INV-{i:06d}",
                "entity": "Texas Southern University",
                "vendor": random.choice(vendors[5:]),
                "amount_usd": random.uniform(50000, 500000),
                "date": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "po_number": "",
                "authorization_status": random.choice(["unauthorized", "missing", "pending"]),
                "is_synthetic_unauthorized": True
            }
        else:
            invoice = {
                "id": f"INV-{i:06d}",
                "entity": "Texas Southern University",
                "vendor": random.choice(authorized),
                "amount_usd": random.uniform(1000, 50000),
                "date": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "po_number": f"PO-{random.randint(1000,9999)}",
                "authorization_status": "authorized",
                "is_synthetic_unauthorized": False
            }

        invoices.append(invoice)

    audit_filings = [
        {"entity": "Texas Southern University", "fiscal_year": "FY2023", "filing_date": "2024-07-15"},
        {"entity": "Texas Southern University", "fiscal_year": "FY2024", "filing_date": "2025-01-15"}
    ]

    audit_deadlines = [
        {"fiscal_year": "FY2023", "due_date": "2023-09-15"},
        {"fiscal_year": "FY2024", "due_date": "2024-09-15"}
    ]

    return invoices, authorized, audit_filings, audit_deadlines
