#!/usr/bin/env python3
"""
TexasProof CLI - Texas Political Fraud Detection Monte Carlo Simulation.

Usage:
    python cli.py --test              # Emit test receipt
    python cli.py --sim all           # Run all 6 scenarios
    python cli.py --sim baseline      # Run single scenario
    python cli.py --quick             # Quick 100-cycle validation
    python cli.py --dashboard         # Generate dashboards (if all pass)
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import (
    emit_receipt,
    TENANT_ID,
    SCENARIO_NAMES,
    DEFAULT_CYCLES,
    DEFAULT_MONTE_CARLO_RUNS,
    DEFAULT_SEED,
)


def run_test_mode() -> dict:
    """Emit a test receipt to validate CLI functionality."""
    return emit_receipt("cli_test", {
        "tenant_id": TENANT_ID,
        "mode": "test",
        "status": "operational",
        "version": "1.0.0"
    })


def run_simulation(scenario: str, runs: int, seed: int, quick: bool = False) -> dict:
    """Run simulation for specified scenario(s)."""
    from src.sim import run_all_scenarios, run_scenario, SimConfig

    cycles = 100 if quick else DEFAULT_CYCLES
    monte_carlo_runs = 100 if quick else runs

    config = SimConfig(
        n_cycles=cycles,
        n_monte_carlo_runs=monte_carlo_runs,
        random_seed=seed
    )

    if scenario == "all":
        return run_all_scenarios(config)
    else:
        return run_scenario(scenario, config)


def generate_dashboards() -> None:
    """Generate HTML dashboards for fraud detection results."""
    from src.dashboards import generate_all_dashboards
    generate_all_dashboards()


def print_banner() -> None:
    """Print CLI banner."""
    print("TexasProof v1 Simulation", file=sys.stderr)
    print("=" * 24, file=sys.stderr)
    print(file=sys.stderr)


def print_results(results: dict) -> None:
    """Print simulation results to stderr."""
    print("\nRunning 6 mandatory scenarios...\n", file=sys.stderr)

    for name, result in results.get("scenario_results", {}).items():
        status = "✓ PASS" if result.get("passed", False) else "✗ FAIL"
        print(f"SCENARIO: {name.upper()}", file=sys.stderr)

        for key, value in result.items():
            if key != "passed":
                if isinstance(value, float):
                    print(f"  {key}: {value:.2%}", file=sys.stderr)
                else:
                    print(f"  {key}: {value}", file=sys.stderr)

        print(f"  Status: {status}", file=sys.stderr)
        print(file=sys.stderr)

    if results.get("all_passed", False):
        print("ALL SCENARIOS PASSED", file=sys.stderr)
    else:
        print("SOME SCENARIOS FAILED", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="TexasProof - Texas Political Fraud Detection Monte Carlo Simulation"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (emit test receipt)"
    )

    parser.add_argument(
        "--sim",
        choices=["all"] + SCENARIO_NAMES,
        help="Run simulation scenario(s)"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_MONTE_CARLO_RUNS,
        help=f"Number of Monte Carlo runs (default: {DEFAULT_MONTE_CARLO_RUNS})"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick validation (100 cycles)"
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate dashboards after simulation"
    )

    args = parser.parse_args()

    # Test mode
    if args.test:
        run_test_mode()
        return 0

    # Simulation mode
    if args.sim:
        print_banner()
        results = run_simulation(args.sim, args.runs, args.seed, args.quick)
        print_results(results)

        # Generate dashboards if requested and all passed
        if args.dashboard and results.get("all_passed", False):
            print("\nGenerating dashboards...", file=sys.stderr)
            generate_dashboards()

        return 0 if results.get("all_passed", False) else 1

    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
