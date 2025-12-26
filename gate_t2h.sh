#!/bin/bash
# gate_t2h.sh - T+2h Gate: SKELETON
# RUN THIS OR KILL PROJECT

set -e

echo "=== GATE T+2h: SKELETON ==="
echo ""

# Check spec.md exists
if [ -f spec.md ]; then
    echo "✓ spec.md exists"
else
    echo "✗ FAIL: no spec.md"
    exit 1
fi

# Check ledger_schema.json exists
if [ -f ledger_schema.json ]; then
    echo "✓ ledger_schema.json exists"
else
    echo "✗ FAIL: no ledger_schema.json"
    exit 1
fi

# Check texas_fraud_spec.json exists
if [ -f texas_fraud_spec.json ]; then
    echo "✓ texas_fraud_spec.json exists"
else
    echo "✗ FAIL: no texas_fraud_spec.json"
    exit 1
fi

# Check cli.py exists
if [ -f cli.py ]; then
    echo "✓ cli.py exists"
else
    echo "✗ FAIL: no cli.py"
    exit 1
fi

# Check cli.py emits valid receipt
if python cli.py --test 2>&1 | grep -q '"receipt_type"'; then
    echo "✓ cli.py emits valid receipt"
else
    echo "✗ FAIL: cli.py does not emit valid receipt"
    exit 1
fi

# Check core.py has required functions
if grep -q "dual_hash" src/core.py && grep -q "emit_receipt" src/core.py; then
    echo "✓ src/core.py has required functions"
else
    echo "✗ FAIL: src/core.py missing required functions"
    exit 1
fi

# Verify texas_fraud_spec.json has OLS data
if python -c "import json; d = json.load(open('texas_fraud_spec.json')); assert d['fraud_vectors']['operation_lone_star']['total_spent_usd'] >= 11000000000" 2>/dev/null; then
    echo "✓ texas_fraud_spec.json has OLS data (\$11B+)"
else
    echo "✗ FAIL: texas_fraud_spec.json missing OLS data"
    exit 1
fi

echo ""
echo "=== PASS: T+2h gate ==="
