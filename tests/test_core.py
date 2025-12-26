"""Tests for core module."""

import pytest
import json
from src.core import (
    dual_hash,
    emit_receipt,
    merkle,
    StopRuleException,
    TENANT_ID,
    SCENARIO_NAMES,
    stoprule_detection_rate,
    stoprule_consecutive_failures,
    validate_receipt,
)


class TestDualHash:
    """Tests for dual_hash function."""

    def test_dual_hash_string(self):
        """Test hashing a string."""
        result = dual_hash("test")
        assert ":" in result
        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA256 hex length
        assert len(parts[1]) == 64  # BLAKE3 hex length

    def test_dual_hash_bytes(self):
        """Test hashing bytes."""
        result = dual_hash(b"test")
        assert ":" in result

    def test_dual_hash_deterministic(self):
        """Test that hashing is deterministic."""
        result1 = dual_hash("test")
        result2 = dual_hash("test")
        assert result1 == result2

    def test_dual_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        result1 = dual_hash("test1")
        result2 = dual_hash("test2")
        assert result1 != result2


class TestEmitReceipt:
    """Tests for emit_receipt function."""

    def test_emit_receipt_basic(self, capsys):
        """Test basic receipt emission."""
        receipt = emit_receipt("test", {"data": "value"}, output=True)

        assert receipt["receipt_type"] == "test"
        assert "ts" in receipt
        assert "payload_hash" in receipt
        assert receipt["tenant_id"] == TENANT_ID

        # Check stdout
        captured = capsys.readouterr()
        assert "test" in captured.out

    def test_emit_receipt_no_output(self, capsys):
        """Test receipt emission without stdout."""
        receipt = emit_receipt("test", {"data": "value"}, output=False)

        assert receipt["receipt_type"] == "test"

        # Check no stdout
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_emit_receipt_custom_tenant(self):
        """Test receipt with custom tenant_id."""
        receipt = emit_receipt("test", {"tenant_id": "custom"}, output=False)
        assert receipt["tenant_id"] == "custom"


class TestMerkle:
    """Tests for merkle function."""

    def test_merkle_empty(self):
        """Test merkle root of empty list."""
        result = merkle([])
        assert ":" in result  # Should still be a dual hash

    def test_merkle_single(self):
        """Test merkle root of single item."""
        result = merkle([{"data": "test"}])
        assert ":" in result

    def test_merkle_multiple(self):
        """Test merkle root of multiple items."""
        items = [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}]
        result = merkle(items)
        assert ":" in result

    def test_merkle_deterministic(self):
        """Test that merkle root is deterministic."""
        items = [{"a": 1}, {"b": 2}]
        result1 = merkle(items)
        result2 = merkle(items)
        assert result1 == result2

    def test_merkle_odd_count(self):
        """Test merkle root with odd number of items."""
        items = [{"a": 1}, {"b": 2}, {"c": 3}]
        result = merkle(items)
        assert ":" in result


class TestStopRuleException:
    """Tests for StopRuleException."""

    def test_stoprule_exception_basic(self):
        """Test basic StopRuleException."""
        with pytest.raises(StopRuleException) as excinfo:
            raise StopRuleException("Test error", metric="test", action="halt")

        assert "Test error" in str(excinfo.value)
        assert excinfo.value.metric == "test"
        assert excinfo.value.action == "halt"

    def test_stoprule_detection_rate(self):
        """Test stoprule for detection rate."""
        # Should not raise for good rate
        stoprule_detection_rate(0.80, threshold=0.70)

        # Should raise for bad rate
        with pytest.raises(StopRuleException):
            stoprule_detection_rate(0.50, threshold=0.70)

    def test_stoprule_consecutive_failures(self):
        """Test stoprule for consecutive failures."""
        # Should not raise for few failures
        stoprule_consecutive_failures(1, max_failures=2)

        # Should raise for too many failures
        with pytest.raises(StopRuleException):
            stoprule_consecutive_failures(3, max_failures=2)


class TestConstants:
    """Tests for constants."""

    def test_tenant_id(self):
        """Test TENANT_ID constant."""
        assert TENANT_ID == "texasproof"

    def test_scenario_names(self):
        """Test SCENARIO_NAMES constant."""
        assert len(SCENARIO_NAMES) == 6
        assert "baseline" in SCENARIO_NAMES
        assert "stress" in SCENARIO_NAMES
        assert "genesis" in SCENARIO_NAMES
        assert "colony_ridge" in SCENARIO_NAMES
        assert "fund_diversion" in SCENARIO_NAMES
        assert "godel" in SCENARIO_NAMES


class TestValidateReceipt:
    """Tests for validate_receipt function."""

    def test_validate_receipt_valid(self):
        """Test validation of valid receipt."""
        receipt = {
            "receipt_type": "test",
            "ts": "2024-01-01T00:00:00Z",
            "tenant_id": "texasproof",
            "payload_hash": "abc:def"
        }
        assert validate_receipt(receipt) is True

    def test_validate_receipt_missing_field(self):
        """Test validation of receipt with missing field."""
        receipt = {
            "receipt_type": "test",
            "ts": "2024-01-01T00:00:00Z"
            # Missing tenant_id and payload_hash
        }
        assert validate_receipt(receipt) is False
