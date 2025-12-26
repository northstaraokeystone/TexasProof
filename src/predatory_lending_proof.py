"""
Predatory Lending Detection (Colony Ridge Pattern).

Detects Colony Ridge-style predatory lending and property churning:
Seller-financed loan → High foreclosure rate → Property resale → Repeat

Key metrics:
- 30% foreclosure rate (15x national average of 2%)
- Properties churned 2-4+ times in 3 years
- Seller-financed loans to vulnerable populations
"""

from typing import Any
from datetime import datetime, timedelta

from .core import (
    emit_receipt,
    dual_hash,
    TENANT_ID,
    PREDATORY_FORECLOSURE_MULTIPLIER,
    CHURNING_PERIOD_YEARS,
    CHURNING_MIN_SALES,
    COLONY_RIDGE_FORECLOSURE_RATE,
    NATIONAL_FORECLOSURE_RATE,
)


def ingest_loan(loan: dict) -> dict:
    """
    Ingest loan record, emit loan_ingest_receipt.

    Args:
        loan: Loan record dict

    Returns:
        Enriched loan with analysis flags
    """
    # Analyze loan terms for predatory indicators
    interest_rate = loan.get("interest_rate", 0)
    down_payment = loan.get("down_payment_percent", 0)
    loan_type = loan.get("loan_type", "").lower()

    predatory_flags = []
    if interest_rate > 10:
        predatory_flags.append("high_interest")
    if down_payment < 10:
        predatory_flags.append("low_down_payment")
    if "seller" in loan_type:
        predatory_flags.append("seller_financed")

    enriched = {
        **loan,
        "predatory_flags": predatory_flags,
        "flag_count": len(predatory_flags),
        "ingested": True
    }

    emit_receipt("ingest", {
        "tenant_id": TENANT_ID,
        "source_type": "loan_record",
        "property_id": loan.get("property_id", "unknown"),
        "amount_usd": loan.get("amount_usd", 0),
        "predatory_flag_count": len(predatory_flags),
        "payload_hash": dual_hash(str(loan))
    })

    return enriched


def detect_churning(property_id: str, transactions: list) -> dict:
    """
    Detect 2+ sales in 3 years = churning.

    Args:
        property_id: Property identifier
        transactions: List of transaction dicts for this property

    Returns:
        Churn receipt dict
    """
    # Filter transactions for this property
    prop_transactions = [t for t in transactions if t.get("property_id") == property_id]

    if len(prop_transactions) < 2:
        return {
            "property_id": property_id,
            "is_churning": False,
            "sale_count": len(prop_transactions),
            "churn_period_years": 0
        }

    # Sort by date
    def parse_date(t):
        date_str = t.get("date", "2020-01-01")
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime(2020, 1, 1)

    sorted_trans = sorted(prop_transactions, key=parse_date)

    # Find time span
    first_date = parse_date(sorted_trans[0])
    last_date = parse_date(sorted_trans[-1])
    span_years = (last_date - first_date).days / 365.25

    # Check churning criteria
    is_churning = (
        len(sorted_trans) >= CHURNING_MIN_SALES and
        span_years <= CHURNING_PERIOD_YEARS
    )

    result = {
        "property_id": property_id,
        "is_churning": is_churning,
        "sale_count": len(sorted_trans),
        "churn_period_years": round(span_years, 2),
        "sales_per_year": len(sorted_trans) / max(span_years, 0.1),
        "transactions": sorted_trans
    }

    if is_churning:
        emit_receipt("churn_detected", {
            "tenant_id": TENANT_ID,
            "property_id": property_id,
            "sale_count": len(sorted_trans),
            "churn_period_years": round(span_years, 2)
        })

    return result


def calculate_foreclosure_rate(loans: list) -> float:
    """
    Calculate portfolio foreclosure rate. >15% = predatory threshold.

    Args:
        loans: List of loan dicts with status field

    Returns:
        Foreclosure rate 0-1
    """
    if not loans:
        return 0.0

    foreclosed = sum(1 for loan in loans if loan.get("status", "").lower() in [
        "foreclosed", "foreclosure", "default", "repossessed"
    ])

    return foreclosed / len(loans)


def detect_predatory_pattern(loans: list, demographics: dict) -> dict:
    """
    Correlate loan terms with targeted demographics.

    Args:
        loans: List of loan dicts
        demographics: Dict with demographic info

    Returns:
        Predatory pattern analysis
    """
    # Analyze loan term distribution
    high_interest_count = sum(1 for l in loans if l.get("interest_rate", 0) > 10)
    seller_financed_count = sum(1 for l in loans if "seller" in l.get("loan_type", "").lower())
    low_down_count = sum(1 for l in loans if l.get("down_payment_percent", 100) < 10)

    # Calculate rates
    total = len(loans) if loans else 1
    high_interest_rate = high_interest_count / total
    seller_financed_rate = seller_financed_count / total
    low_down_rate = low_down_count / total

    # Demographic targeting score
    target_score = 0.0
    if demographics.get("median_income", 100000) < 40000:
        target_score += 0.3
    if demographics.get("immigrant_percent", 0) > 30:
        target_score += 0.3
    if demographics.get("credit_score_median", 700) < 600:
        target_score += 0.2
    if demographics.get("education_below_hs_percent", 0) > 25:
        target_score += 0.2

    # Predatory score
    predatory_score = (
        high_interest_rate * 0.3 +
        seller_financed_rate * 0.3 +
        low_down_rate * 0.2 +
        target_score * 0.2
    )

    return {
        "high_interest_rate": high_interest_rate,
        "seller_financed_rate": seller_financed_rate,
        "low_down_rate": low_down_rate,
        "demographic_target_score": target_score,
        "predatory_score": min(1.0, predatory_score),
        "is_predatory_pattern": predatory_score > 0.5
    }


def emit_lending_receipt(findings: dict) -> dict:
    """
    Emit predatory_lending_receipt.

    Args:
        findings: Detection findings dict

    Returns:
        Predatory lending receipt
    """
    return emit_receipt("predatory_lending", {
        "tenant_id": TENANT_ID,
        "property_id": findings.get("property_id", "unknown"),
        "churn_count": findings.get("churn_count", 0),
        "churn_period_years": findings.get("churn_period_years", 0),
        "foreclosure_rate": findings.get("foreclosure_rate", 0),
        "national_average_rate": NATIONAL_FORECLOSURE_RATE,
        "multiplier": findings.get("multiplier", 1.0),
        "predatory_probability": findings.get("predatory_probability", 0.0)
    })


def analyze_lending_portfolio(
    loans: list,
    transactions: list,
    demographics: dict = None
) -> dict:
    """
    Full predatory lending analysis.

    Args:
        loans: List of loan records
        transactions: List of property transactions
        demographics: Optional demographic data

    Returns:
        Analysis results with receipts
    """
    demographics = demographics or {}

    results = {
        "total_loans": len(loans),
        "total_transactions": len(transactions),
        "churning_properties": [],
        "high_risk_loans": [],
        "portfolio_metrics": {},
        "receipts": []
    }

    # Calculate portfolio foreclosure rate
    foreclosure_rate = calculate_foreclosure_rate(loans)
    multiplier = foreclosure_rate / NATIONAL_FORECLOSURE_RATE if NATIONAL_FORECLOSURE_RATE > 0 else 1

    results["portfolio_metrics"] = {
        "foreclosure_rate": foreclosure_rate,
        "national_average": NATIONAL_FORECLOSURE_RATE,
        "multiplier": multiplier,
        "exceeds_predatory_threshold": multiplier >= PREDATORY_FORECLOSURE_MULTIPLIER
    }

    # Detect churning by property
    property_ids = set(t.get("property_id") for t in transactions)
    for prop_id in property_ids:
        if prop_id:
            churn_result = detect_churning(prop_id, transactions)
            if churn_result["is_churning"]:
                results["churning_properties"].append(churn_result)

    # Analyze predatory pattern
    pattern = detect_predatory_pattern(loans, demographics)
    results["predatory_pattern"] = pattern

    # Generate receipts for churning properties
    for prop in results["churning_properties"]:
        receipt = emit_lending_receipt({
            "property_id": prop["property_id"],
            "churn_count": prop["sale_count"],
            "churn_period_years": prop["churn_period_years"],
            "foreclosure_rate": foreclosure_rate,
            "multiplier": multiplier,
            "predatory_probability": 0.9 if multiplier >= PREDATORY_FORECLOSURE_MULTIPLIER else 0.5
        })
        results["receipts"].append(receipt)

    return results


def generate_synthetic_lending_data(
    n_properties: int,
    n_loans: int,
    churn_rate: float = 0.3,
    predatory_rate: float = 0.3
) -> tuple:
    """
    Generate synthetic lending data for simulation.

    Returns:
        Tuple of (loans, transactions)
    """
    import random

    loans = []
    transactions = []

    for i in range(n_properties):
        prop_id = f"PROP-{i:06d}"
        is_churned = random.random() < churn_rate
        is_predatory = random.random() < predatory_rate

        # Generate transactions for this property
        n_sales = random.randint(3, 5) if is_churned else random.randint(1, 2)
        base_year = 2020

        for j in range(n_sales):
            transactions.append({
                "property_id": prop_id,
                "transaction_type": "sale",
                "amount_usd": random.uniform(50000, 200000),
                "date": f"{base_year + (j * (3 // n_sales))}:{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "is_synthetic_churn": is_churned
            })

    for i in range(n_loans):
        is_predatory = random.random() < predatory_rate

        if is_predatory:
            loan = {
                "id": f"LOAN-{i:06d}",
                "property_id": f"PROP-{random.randint(0, n_properties-1):06d}",
                "amount_usd": random.uniform(50000, 200000),
                "interest_rate": random.uniform(10, 15),
                "down_payment_percent": random.uniform(2, 8),
                "loan_type": "seller_financed",
                "status": random.choice(["active", "foreclosed", "foreclosed", "active"]),  # Higher foreclosure
                "is_synthetic_predatory": True
            }
        else:
            loan = {
                "id": f"LOAN-{i:06d}",
                "property_id": f"PROP-{random.randint(0, n_properties-1):06d}",
                "amount_usd": random.uniform(100000, 400000),
                "interest_rate": random.uniform(4, 7),
                "down_payment_percent": random.uniform(10, 25),
                "loan_type": random.choice(["conventional", "fha", "va"]),
                "status": random.choice(["active", "active", "active", "paid_off", "foreclosed"]),
                "is_synthetic_predatory": False
            }

        loans.append(loan)

    return loans, transactions
