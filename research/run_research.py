"""CLI entry point and workflow orchestration for deep research POC."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from research.agents import (
    get_gathering_agent,
    get_plan_agent,
    get_synthesis_agent,
    get_verification_agent,
)


async def run_research(query: str) -> dict[str, object]:
    """
    Execute 4-phase deep research workflow.

    Phase 1: Planning - Create structured research plan
    Phase 2: Gathering - Execute searches in parallel
    Phase 3: Synthesis - Combine results into coherent report
    Phase 4: Verification - Validate report quality

    Args:
        query: Research question to investigate

    Returns:
        Complete research results including plan, search results, report, and validation
    """
    print(f"Starting research: {query}\n")

    # Initialize agents
    plan_agent = get_plan_agent()
    gathering_agent = get_gathering_agent()
    synthesis_agent = get_synthesis_agent()
    verification_agent = get_verification_agent()

    # Phase 1: Planning
    print("Phase 1: Creating research plan...")
    plan_result = await plan_agent.run(query)
    plan = plan_result.output
    print(f"  Created {len(plan.web_search_steps)} search steps\n")

    # Phase 2: Gathering (parallel execution)
    print("Phase 2: Gathering information...")
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(gathering_agent.run(step.search_terms)) for step in plan.web_search_steps]
    results = [task.result().output for task in tasks]
    print(f"  Completed {len(results)} searches\n")

    # Phase 3: Synthesis
    print("Phase 3: Synthesizing report...")
    synthesis_prompt = f"""
    Original query: {query}
    Research plan: {plan.model_dump_json()}
    Search results: {json.dumps([r.model_dump() for r in results])}

    Create a comprehensive research report based on these materials.
    """
    report_result = await synthesis_agent.run(synthesis_prompt)
    report = report_result.output
    print(f"  Report: {report.title}\n")

    # Phase 4: Verification
    print("Phase 4: Verifying report...")
    validation_prompt = f"""
    Validate this research report:
    {report.model_dump_json()}

    Check for quality, consistency, and reliability.
    """
    validation_result = await verification_agent.run(validation_prompt)
    validation = validation_result.output
    print(f"  Valid: {validation.is_valid}, Confidence: {validation.confidence_score:.2f}\n")

    return {
        "query": query,
        "plan": plan.model_dump(),
        "search_results": [r.model_dump() for r in results],
        "report": report.model_dump(),
        "validation": validation.model_dump(),
    }


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m research.run_research 'your query'")
        sys.exit(1)

    query = sys.argv[1]
    result = asyncio.run(run_research(query))

    # Save output
    outputs_dir = Path(__file__).parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = outputs_dir / f"research_{timestamp}.json"
    output_file.write_text(json.dumps(result, indent=2))
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
