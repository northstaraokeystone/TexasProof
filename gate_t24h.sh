#!/bin/bash
# gate_t24h.sh - T+24h Gate: MVP
# RUN THIS OR KILL PROJECT

set -e

echo "=== GATE T+24h: MVP ==="
echo ""

# Run pytest
echo "Running tests..."
if python -m pytest tests/ -q --tb=short; then
    echo "✓ Tests pass"
else
    echo "✗ FAIL: tests failed"
    exit 1
fi

# Check emit_receipt in src files
if grep -rq "emit_receipt" src/*.py; then
    echo "✓ src/*.py files have emit_receipt"
else
    echo "✗ FAIL: no emit_receipt in src"
    exit 1
fi

# Check assertions in tests
if grep -rq "assert" tests/*.py; then
    echo "✓ tests/*.py files have assertions"
else
    echo "✗ FAIL: no assertions in tests"
    exit 1
fi

# Check fraud detection modules exist
for module in ols_contractor_proof pac_influence_proof predatory_lending_proof tsu_probe_proof lottery_proof; do
    if [ -f "src/${module}.py" ]; then
        echo "✓ src/${module}.py exists"
    else
        echo "✗ FAIL: src/${module}.py missing"
        exit 1
    fi
done

# Check watcher and genesis modules
if [ -f "src/watcher.py" ] && [ -f "src/genesis.py" ]; then
    echo "✓ Self-spawn modules exist"
else
    echo "✗ FAIL: watcher.py or genesis.py missing"
    exit 1
fi

# Check simulation modules
if [ -f "src/sim.py" ] && [ -f "src/scenarios.py" ]; then
    echo "✓ Simulation modules exist"
else
    echo "✗ FAIL: sim.py or scenarios.py missing"
    exit 1
fi

# Run 100-cycle smoke test
echo "Running 100-cycle smoke test..."
if python -c "from src.sim import run_simulation, SimConfig; r = run_simulation(SimConfig(n_cycles=100)); print(f'Smoke test: {len(r.violations)} violations, all_passed: {r.all_passed}')" 2>/dev/null; then
    echo "✓ 100-cycle smoke test passes"
else
    echo "✗ FAIL: smoke test failed"
    exit 1
fi

echo ""
echo "=== PASS: T+24h gate ==="
