"""Tests for predatory lending proof module."""

import pytest
from src.predatory_lending_proof import (
    ingest_loan,
    detect_churning,
    calculate_foreclosure_rate,
    detect_predatory_pattern,
    emit_lending_receipt,
    generate_synthetic_lending_data,
    analyze_lending_portfolio,
)


class TestIngestLoan:
    """Tests for loan ingestion."""

    def test_ingest_loan_basic(self, sample_loan):
        """Test basic loan ingestion."""
        enriched = ingest_loan(sample_loan)

        assert enriched["ingested"] is True
        assert "predatory_flags" in enriched

    def test_ingest_loan_predatory_flags(self, sample_loan):
        """Test predatory flag detection."""
        enriched = ingest_loan(sample_loan)

        # High interest + low down payment + seller financed
        assert len(enriched["predatory_flags"]) >= 2
        assert "high_interest" in enriched["predatory_flags"]


class TestDetectChurning:
    """Tests for churning detection."""

    def test_detect_churning_basic(self):
        """Test basic churning detection."""
        transactions = [
            {"property_id": "PROP-001", "date": "2021-01-15", "transaction_type": "sale"},
            {"property_id": "PROP-001", "date": "2022-06-15", "transaction_type": "sale"},
            {"property_id": "PROP-001", "date": "2023-03-15", "transaction_type": "sale"},
        ]

        result = detect_churning("PROP-001", transactions)

        assert result["is_churning"] is True
        assert result["sale_count"] == 3

    def test_no_churning_single_sale(self):
        """Test no churning with single sale."""
        transactions = [
            {"property_id": "PROP-002", "date": "2022-01-15", "transaction_type": "sale"}
        ]

        result = detect_churning("PROP-002", transactions)

        assert result["is_churning"] is False


class TestCalculateForeclosureRate:
    """Tests for foreclosure rate calculation."""

    def test_calculate_rate_basic(self):
        """Test basic foreclosure rate calculation."""
        loans = [
            {"status": "active"},
            {"status": "active"},
            {"status": "foreclosed"},
            {"status": "foreclosed"},
            {"status": "paid_off"}
        ]

        rate = calculate_foreclosure_rate(loans)

        assert rate == 0.4  # 2/5

    def test_calculate_rate_empty(self):
        """Test foreclosure rate with no loans."""
        rate = calculate_foreclosure_rate([])
        assert rate == 0.0


class TestDetectPredatoryPattern:
    """Tests for predatory pattern detection."""

    def test_detect_pattern_basic(self):
        """Test basic predatory pattern detection."""
        loans = [
            {"interest_rate": 12, "loan_type": "seller_financed", "down_payment_percent": 5},
            {"interest_rate": 14, "loan_type": "seller_financed", "down_payment_percent": 3},
        ]
        demographics = {
            "median_income": 30000,
            "immigrant_percent": 40,
            "credit_score_median": 550
        }

        result = detect_predatory_pattern(loans, demographics)

        assert result["is_predatory_pattern"] is True
        assert result["predatory_score"] > 0.5

    def test_detect_pattern_normal(self):
        """Test pattern detection for normal loans."""
        loans = [
            {"interest_rate": 5, "loan_type": "conventional", "down_payment_percent": 20},
            {"interest_rate": 4.5, "loan_type": "fha", "down_payment_percent": 15},
        ]
        demographics = {}

        result = detect_predatory_pattern(loans, demographics)

        assert result["predatory_score"] < 0.3


class TestGenerateSyntheticData:
    """Tests for synthetic lending data generation."""

    def test_generate_data(self):
        """Test synthetic data generation."""
        loans, transactions = generate_synthetic_lending_data(
            n_properties=100,
            n_loans=100,
            churn_rate=0.3,
            predatory_rate=0.3
        )

        assert len(loans) == 100
        assert len(transactions) > 0

    def test_generate_data_fields(self):
        """Test that generated data has required fields."""
        loans, transactions = generate_synthetic_lending_data(10, 10)

        for loan in loans:
            assert "property_id" in loan
            assert "amount_usd" in loan
            assert "interest_rate" in loan


class TestAnalyzeLendingPortfolio:
    """Tests for portfolio analysis."""

    def test_analyze_portfolio(self):
        """Test portfolio analysis."""
        loans, transactions = generate_synthetic_lending_data(50, 50, churn_rate=0.3)

        results = analyze_lending_portfolio(loans, transactions)

        assert "total_loans" in results
        assert "portfolio_metrics" in results
        assert "churning_properties" in results


class TestEmitLendingReceipt:
    """Tests for lending receipt emission."""

    def test_emit_receipt(self, capsys):
        """Test lending receipt emission."""
        receipt = emit_lending_receipt({
            "property_id": "PROP-001",
            "churn_count": 3,
            "churn_period_years": 2.5,
            "foreclosure_rate": 0.30,
            "multiplier": 15.0,
            "predatory_probability": 0.9
        })

        assert receipt["receipt_type"] == "predatory_lending"
        assert receipt["churn_count"] == 3

        captured = capsys.readouterr()
        assert "predatory_lending" in captured.out
