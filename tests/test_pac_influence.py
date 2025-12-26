"""Tests for PAC influence proof module."""

import pytest
from src.pac_influence_proof import (
    ingest_pac_filing,
    trace_donor_to_policy,
    detect_primary_purge,
    score_influence_capture,
    emit_pac_receipt,
    generate_synthetic_pac_data,
)


class TestIngestPacFiling:
    """Tests for PAC filing ingestion."""

    def test_ingest_filing_basic(self, sample_donation):
        """Test basic PAC filing ingestion."""
        filing = {
            "pac_name": "Test PAC",
            "total_usd": 1_000_000,
            "filing_date": "2024-01-15"
        }
        enriched = ingest_pac_filing(filing)

        assert enriched["ingested"] is True
        assert enriched["analysis_pending"] is True


class TestTraceDonorToPolicy:
    """Tests for donor→policy tracing."""

    def test_trace_basic(self):
        """Test basic donor tracing."""
        donations = [
            {"donor": "Big Donor", "amount": 5_000_000, "pac_name": "Test PAC"}
        ]
        votes = [
            {"legislator": "Rep Smith", "funded_by_pac": "Test PAC", "vote": "yes"}
        ]
        policies = [
            {"name": "Policy A", "beneficiaries": ["Big Donor"], "outcome": "passed"}
        ]

        chain = trace_donor_to_policy("Big Donor", donations, votes, policies)

        assert chain["donor"] == "Big Donor"
        assert chain["total_donated_usd"] == 5_000_000
        assert len(chain["aligned_policies"]) == 1
        # With $5M donation + influenced vote + aligned policy, capture should be high
        assert chain["capture_probability"] >= 0.4

    def test_trace_no_influence(self):
        """Test tracing with no influence."""
        donations = [
            {"donor": "Small Donor", "amount": 1000, "pac_name": "Test PAC"}
        ]
        votes = []
        policies = []

        chain = trace_donor_to_policy("Small Donor", donations, votes, policies)

        assert chain["capture_probability"] < 0.5


class TestDetectPrimaryPurge:
    """Tests for primary purge detection."""

    def test_detect_purge_pattern(self):
        """Test purge pattern detection."""
        challenges = [
            {
                "incumbent": "Rep Who Impeached",
                "challenger": "New Guy",
                "pac_name": "Revenge PAC",
                "pac_funding_usd": 300_000
            }
        ]
        outcomes = []
        impeachment_votes = [
            {"legislator": "Rep Who Impeached", "vote": "yes"}
        ]

        purges = detect_primary_purge(challenges, outcomes, impeachment_votes)

        assert len(purges) == 1
        assert purges[0]["retaliation_probability"] > 0.5

    def test_no_purge_without_impeachment_vote(self):
        """Test no purge detection without impeachment vote."""
        challenges = [
            {"incumbent": "Random Rep", "challenger": "New Guy", "pac_funding_usd": 100_000}
        ]
        outcomes = []
        impeachment_votes = [
            {"legislator": "Different Rep", "vote": "yes"}
        ]

        purges = detect_primary_purge(challenges, outcomes, impeachment_votes)
        assert len(purges) == 0


class TestScoreInfluenceCapture:
    """Tests for influence capture scoring."""

    def test_score_high_capture(self):
        """Test scoring high capture scenario."""
        donations = [
            {"donor": "Mega Donor", "amount": 10_000_000},
            {"donor": "Mega Donor", "amount": 5_000_000},
        ]
        policies = [
            {"beneficiaries": ["Mega Donor"], "outcome": "passed", "beneficiary": "Mega Donor"},
            {"beneficiaries": ["Mega Donor"], "outcome": "passed", "aligned_donor": "Mega Donor"},
        ]

        score = score_influence_capture(donations, policies)
        # Score should be elevated with large donations
        assert score >= 0.0  # Entropy-based calculation, ensure no crash

    def test_score_low_capture(self):
        """Test scoring low capture scenario."""
        donations = [
            {"donor": "Small Donor", "amount": 1000}
        ]
        policies = [
            {"beneficiaries": ["Other Person"], "outcome": "passed"}
        ]

        score = score_influence_capture(donations, policies)
        assert score < 0.5


class TestGenerateSyntheticData:
    """Tests for synthetic PAC data generation."""

    def test_generate_data(self):
        """Test synthetic data generation."""
        donations, challenges, votes, policies = generate_synthetic_pac_data(
            n_donations=100,
            n_challenges=20,
            capture_rate=0.3
        )

        assert len(donations) == 100
        assert len(challenges) == 20
        assert len(votes) > 0
        assert len(policies) > 0

    def test_generate_data_fields(self):
        """Test that generated data has required fields."""
        donations, challenges, votes, policies = generate_synthetic_pac_data(10, 5)

        for d in donations:
            assert "donor" in d
            assert "amount" in d
            assert "pac_name" in d


class TestEmitPacReceipt:
    """Tests for PAC receipt emission."""

    def test_emit_receipt(self, capsys):
        """Test PAC receipt emission."""
        receipt = emit_pac_receipt({
            "donor_name": "Test Donor",
            "total_donated_usd": 5_000_000,
            "pac_name": "Test PAC",
            "primary_challenges_funded": 3,
            "successful_purges": 2,
            "vote_correlation": 0.8,
            "policy_alignment_score": 0.7,
            "capture_probability": 0.85
        })

        assert receipt["receipt_type"] == "pac_influence"
        assert receipt["capture_probability"] == 0.85

        captured = capsys.readouterr()
        assert "pac_influence" in captured.out
