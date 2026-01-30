"""
Run Evaluations
===============

Evaluation runner for the Data Agent.

Runs test cases, checks for expected values in responses, and reports results.

Usage:
    python -m data_agent.evals.run_evals
    python -m data_agent.evals.run_evals --category basic
    python -m data_agent.evals.run_evals --verbose
"""

import argparse
import sys
import time
from typing import NamedTuple

from data_agent.evals.test_cases import CATEGORIES, TestCase, get_test_cases


class EvalResult(NamedTuple):
    """Result of a single evaluation."""

    test_case: TestCase
    passed: bool
    missing_values: list[str]
    response: str
    duration: float


def run_single_eval(agent, test_case: TestCase, verbose: bool = False) -> EvalResult:
    """Run a single evaluation.

    Args:
        agent: The Data Agent instance.
        test_case: The test case to run.
        verbose: Print detailed output.

    Returns:
        EvalResult with pass/fail status and details.
    """
    start = time.time()

    try:
        response = agent.run(test_case.question)
        text = (response.content or "").lower()
    except Exception as e:
        text = f"Error: {e}"

    duration = time.time() - start

    # Check for expected values (case-insensitive)
    missing = [v for v in test_case.expected_values if v.lower() not in text]

    passed = len(missing) == 0

    return EvalResult(
        test_case=test_case,
        passed=passed,
        missing_values=missing,
        response=text[:500] if not verbose else text,
        duration=duration,
    )


def run_evals(
    category: str | None = None,
    verbose: bool = False,
) -> tuple[int, int]:
    """Run all evaluations.

    Args:
        category: Optional category to filter tests.
        verbose: Print detailed output.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    # Import agent here to avoid startup time if just checking help
    from data_agent.agent import data_agent

    test_cases = get_test_cases(category)

    if not test_cases:
        print(f"No test cases found for category: {category}")
        return 0, 0

    print(f"Running {len(test_cases)} test cases...")
    if category:
        print(f"Category: {category}")
    print()

    passed = 0
    failed = 0
    results: list[EvalResult] = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case.question[:60]}...", end=" ", flush=True)

        result = run_single_eval(data_agent, test_case, verbose)
        results.append(result)

        if result.passed:
            print(f"PASS ({result.duration:.1f}s)")
            passed += 1
        else:
            print(f"FAIL ({result.duration:.1f}s)")
            print(f"  Missing: {result.missing_values}")
            failed += 1

        if verbose and not result.passed:
            print(f"  Response: {result.response[:200]}...")

    # Summary
    print()
    print("=" * 60)
    total = passed + failed
    pct = (passed / total * 100) if total > 0 else 0
    print(f"Results: {passed}/{total} passed ({pct:.1f}%)")

    if failed > 0:
        print()
        print("Failed tests:")
        for result in results:
            if not result.passed:
                print(f"  - {result.test_case.question}")
                print(f"    Missing: {result.missing_values}")

    return passed, failed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Data Agent evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Categories:
  {', '.join(CATEGORIES)}

Examples:
  python -m data_agent.evals.run_evals
  python -m data_agent.evals.run_evals --category basic
  python -m data_agent.evals.run_evals --verbose
""",
    )
    parser.add_argument(
        "--category",
        "-c",
        choices=CATEGORIES,
        help="Run only tests in this category",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    passed, failed = run_evals(category=args.category, verbose=args.verbose)

    # Exit with error if any tests failed
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
