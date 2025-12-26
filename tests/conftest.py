"""Pytest configuration and fixtures for TexasProof tests."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_contract():
    """Sample OLS contract for testing."""
    return {
        "name": "Test Contractor Inc",
        "amount_usd": 50_000_000,
        "contract_type": "emergency/no-bid",
        "cost_per_unit_usd": 1500,
        "market_rate_usd": 500,
        "year": 2023
    }


@pytest.fixture
def sample_donation():
    """Sample PAC donation for testing."""
    return {
        "donor": "Test Donor",
        "amount": 500_000,
        "pac_name": "Test PAC",
        "date": "2024-06-15"
    }


@pytest.fixture
def sample_loan():
    """Sample loan for testing."""
    return {
        "id": "LOAN-001",
        "property_id": "PROP-001",
        "amount_usd": 150_000,
        "interest_rate": 12,
        "down_payment_percent": 5,
        "loan_type": "seller_financed",
        "status": "active"
    }


@pytest.fixture
def sample_invoice():
    """Sample invoice for testing."""
    return {
        "id": "INV-001",
        "entity": "Texas Southern University",
        "vendor": "Test Vendor",
        "amount_usd": 50_000,
        "po_number": "",
        "authorization_status": "unauthorized"
    }


@pytest.fixture
def sample_receipts():
    """Sample receipts for testing."""
    return [
        {"receipt_type": "ingest", "ts": "2024-01-01T12:00:00Z", "tenant_id": "texasproof"},
        {"receipt_type": "ols_contractor", "ts": "2024-01-01T12:01:00Z", "tenant_id": "texasproof", "fraud_probability": 0.8},
        {"receipt_type": "pac_influence", "ts": "2024-01-01T12:02:00Z", "tenant_id": "texasproof", "capture_probability": 0.7},
        {"receipt_type": "wound", "wound_type": "high_risk", "ts": "2024-01-01T12:03:00Z", "tenant_id": "texasproof"},
        {"receipt_type": "wound", "wound_type": "high_risk", "ts": "2024-01-02T12:00:00Z", "tenant_id": "texasproof"},
    ]
