"""Tests for OLS contractor proof module."""

import pytest
from src.ols_contractor_proof import (
    ingest_contract,
    detect_emergency_loop,
    score_contract_fraud,
    detect_fund_diversion,
    emit_ols_receipt,
    generate_synthetic_ols_contracts,
    analyze_ols_contractors,
)


class TestIngestContract:
    """Tests for contract ingestion."""

    def test_ingest_contract_basic(self, sample_contract):
        """Test basic contract ingestion."""
        enriched = ingest_contract(sample_contract)

        assert enriched["ingested"] is True
        assert "entropy_score" in enriched
        assert "fraud_probability" in enriched

    def test_ingest_contract_entropy(self, sample_contract):
        """Test entropy calculation on ingestion."""
        enriched = ingest_contract(sample_contract)

        # Emergency/no-bid should have high entropy
        assert enriched["entropy_score"] > 0.5


class TestScoreContractFraud:
    """Tests for fraud scoring."""

    def test_score_emergency_contract(self, sample_contract):
        """Test scoring emergency contract."""
        score = score_contract_fraud(sample_contract, {})
        assert score > 0.5  # Emergency contracts should score high

    def test_score_competitive_contract(self):
        """Test scoring competitive contract."""
        contract = {
            "name": "Good Contractor",
            "amount_usd": 1_000_000,
            "contract_type": "competitive",
            "cost_per_unit_usd": 500,
            "market_rate_usd": 500
        }
        score = score_contract_fraud(contract, {})
        assert score < 0.5  # Competitive contracts should score low

    def test_score_with_donor_network(self, sample_contract):
        """Test scoring with donor network."""
        donor_network = {
            "test contractor inc": {
                "total_usd": 500_000,
                "donations": [{"amount": 500_000}]
            }
        }
        score = score_contract_fraud(sample_contract, donor_network)
        assert score > 0.7  # Donor correlation should increase score


class TestDetectEmergencyLoop:
    """Tests for emergency loop detection."""

    def test_detect_loop_basic(self):
        """Test basic loop detection."""
        contracts = [
            {"name": "Contractor A", "contract_type": "emergency", "date": "2023-01-01"},
            {"name": "Contractor A", "contract_type": "emergency", "date": "2023-06-01"}
        ]
        donations = [
            {"donor": "Contractor A", "amount": 100_000}
        ]

        loops = detect_emergency_loop(contracts, donations)
        assert len(loops) > 0

    def test_no_loop_without_donations(self):
        """Test no loop without donations."""
        contracts = [
            {"name": "Contractor A", "contract_type": "emergency"}
        ]
        donations = []

        loops = detect_emergency_loop(contracts, donations)
        assert len(loops) == 0


class TestDetectFundDiversion:
    """Tests for fund diversion detection."""

    def test_detect_diversion_basic(self):
        """Test basic diversion detection."""
        source_budget = {
            "TDCJ": {
                "original_usd": 500_000_000,
                "actual_usd": 140_400_000,
                "impact": "understaffing"
            }
        }
        dest_spend = {
            "OLS": {
                "original_usd": 100_000_000,
                "actual_usd": 459_600_000
            }
        }

        diversions = detect_fund_diversion(source_budget, dest_spend)
        assert len(diversions) > 0
        assert diversions[0]["source"] == "TDCJ"

    def test_no_diversion_small_amount(self):
        """Test no diversion for small amounts."""
        source_budget = {
            "DPS": {
                "original_usd": 100_000_000,
                "actual_usd": 99_000_000  # Only $1M difference
            }
        }
        dest_spend = {}

        diversions = detect_fund_diversion(source_budget, dest_spend)
        assert len(diversions) == 0


class TestGenerateSyntheticContracts:
    """Tests for synthetic data generation."""

    def test_generate_contracts(self):
        """Test synthetic contract generation."""
        contracts = generate_synthetic_ols_contracts(100, fraud_rate=0.2)

        assert len(contracts) == 100

        # Check fraud rate approximately correct
        fraud_count = sum(1 for c in contracts if c.get("is_synthetic_fraud"))
        assert 10 <= fraud_count <= 30  # ~20% ± 10%

    def test_generate_contracts_fields(self):
        """Test that generated contracts have required fields."""
        contracts = generate_synthetic_ols_contracts(10)

        for c in contracts:
            assert "id" in c
            assert "name" in c
            assert "amount_usd" in c
            assert "contract_type" in c


class TestEmitOlsReceipt:
    """Tests for OLS receipt emission."""

    def test_emit_receipt(self, capsys):
        """Test OLS receipt emission."""
        receipt = emit_ols_receipt({
            "contractor_name": "Test Corp",
            "contract_amount_usd": 50_000_000,
            "contract_type": "emergency",
            "donor_correlation": 0.7,
            "fund_diversion_detected": True,
            "fraud_probability": 0.85
        })

        assert receipt["receipt_type"] == "ols_contractor"
        assert receipt["fraud_probability"] == 0.85

        captured = capsys.readouterr()
        assert "ols_contractor" in captured.out
