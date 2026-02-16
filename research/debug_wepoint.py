"""Minimal reproduction script for Wepoint validation bug.

This script tests the gathering agent with "Wepoint" and "onepoint" queries
to reproduce and quantify the validation failure rate. Runs 20 tests for each
query and captures detailed logs for analysis.

Usage:
    python research/debug_wepoint.py 2>&1 | tee debug_output.log

Expected Results:
    - Wepoint: ~25% success rate (5/20 passing)
    - onepoint: 100% success rate (20/20 passing)
"""

from __future__ import annotations

import asyncio

# Apply debug patch BEFORE importing agents
import research.debug_patch  # noqa: F401
from research.agents import get_gathering_agent
from src.logging import configure_structlog, get_logger

configure_structlog(testing=True)
log = get_logger("debug.wepoint")


async def test_query(query: str, runs: int = 20) -> dict:
    """Test a query N times and track success/failure.

    Args:
        query: Search query to test
        runs: Number of test runs (default: 20)

    Returns:
        Dictionary with success/failure counts and error details
    """
    agent = get_gathering_agent()
    results = {"success": 0, "failure": 0, "errors": []}

    for i in range(runs):
        try:
            result = await agent.run(query)
            results["success"] += 1
            findings_count = len(result.output.findings) if result.output.findings else 0
            log.info(
                "test_success",
                run=i + 1,
                query=query,
                findings_count=findings_count,
            )
        except Exception as e:
            results["failure"] += 1
            error_info = {"run": i + 1, "error": str(e), "type": type(e).__name__}
            results["errors"].append(error_info)
            log.error("test_failure", run=i + 1, query=query, error=str(e), error_type=type(e).__name__)

    success_rate = results["success"] / runs * 100
    log.info(
        "test_summary",
        query=query,
        success_rate=f"{success_rate:.1f}%",
        successes=results["success"],
        failures=results["failure"],
    )

    return results


async def main() -> None:
    """Run reproduction tests for both Wepoint and onepoint queries."""
    print("\n" + "=" * 60)
    print("GEMINI VALIDATION BUG REPRODUCTION TEST")
    print("=" * 60)

    print("\n=== Testing 'Wepoint' (expected 25% success) ===")
    wepoint_results = await test_query("Wepoint", runs=20)

    print("\n=== Testing 'onepoint' (expected 100% success) ===")
    onepoint_results = await test_query("onepoint", runs=20)

    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)
    wepoint_rate = wepoint_results["success"] / 20 * 100
    onepoint_rate = onepoint_results["success"] / 20 * 100

    print(f"Wepoint:  {wepoint_results['success']}/20 ({wepoint_rate:.0f}% success)")
    print(f"onepoint: {onepoint_results['success']}/20 ({onepoint_rate:.0f}% success)")

    if wepoint_results["errors"]:
        print("\nFirst Wepoint error:")
        print(f"  Run: {wepoint_results['errors'][0]['run']}")
        print(f"  Type: {wepoint_results['errors'][0]['type']}")
        print(f"  Error: {wepoint_results['errors'][0]['error'][:200]}...")

    print("\n" + "=" * 60)
    print("Raw logs saved to debug_output.log")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
