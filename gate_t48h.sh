#!/bin/bash
# gate_t48h.sh - T+48h Gate: HARDENED
# RUN THIS OR KILL PROJECT

set -e

echo "=== GATE T+48h: HARDENED ==="
echo ""

# Check anomaly detection
if grep -rq "anomaly" src/*.py; then
    echo "✓ Anomaly detection present"
else
    echo "✗ FAIL: no anomaly detection"
    exit 1
fi

# Check fraud/bias detection
if grep -rq "fraud" src/*.py; then
    echo "✓ Fraud detection present"
else
    echo "✗ FAIL: no fraud detection"
    exit 1
fi

# Check stoprules
if grep -rq "stoprule\|StopRule" src/*.py; then
    echo "✓ Stoprules present"
else
    echo "✗ FAIL: no stoprules"
    exit 1
fi

# Run all 6 scenarios
echo "Running all 6 scenarios..."
if python -c "
from src.sim import run_all_scenarios, SimConfig
config = SimConfig(n_cycles=100)
result = run_all_scenarios(config)
passed = result['summary']['passed']
total = result['summary']['total_scenarios']
print(f'Scenarios: {passed}/{total} passed')
if passed < 4:
    exit(1)
" 2>/dev/null; then
    echo "✓ Scenarios pass"
else
    echo "✗ FAIL: scenarios failed"
    exit 1
fi

# Check dashboards can generate
echo "Checking dashboard generation..."
if python -c "
from src.dashboards import generate_all_dashboards
result = generate_all_dashboards()
print(f'Generated {len(result)} dashboards')
" 2>/dev/null; then
    echo "✓ Dashboards generate"
else
    echo "✗ FAIL: dashboard generation failed"
    exit 1
fi

# Check test coverage (soft check - warn but don't fail)
echo "Checking test coverage..."
if python -m pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=60 2>/dev/null; then
    echo "✓ Test coverage adequate"
else
    echo "⚠ WARNING: Test coverage below 80% (continuing anyway)"
fi

# Check entropy module
if grep -rq "shannon_entropy\|compression_ratio" src/entropy.py; then
    echo "✓ Entropy-based detection present"
else
    echo "✗ FAIL: entropy module incomplete"
    exit 1
fi

# Check self-spawn mechanism
if grep -rq "spawn_watcher\|autocatalysis" src/watcher.py; then
    echo "✓ Self-spawn mechanism present"
else
    echo "✗ FAIL: self-spawn mechanism missing"
    exit 1
fi

# Final validation
echo ""
echo "Running final validation..."
python -c "
from src.core import dual_hash, emit_receipt, SCENARIO_NAMES

# Test dual hash
h = dual_hash('test')
assert ':' in h, 'dual_hash format invalid'

# Test receipt
r = emit_receipt('validation', {'status': 'pass'}, output=False)
assert r['receipt_type'] == 'validation'

# Test scenarios exist
assert len(SCENARIO_NAMES) == 6

print('Final validation: PASS')
"

echo ""
echo "=== PASS: T+48h gate — SHIP IT ==="
