"""CLI entry point and workflow orchestration for deep research POC."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv

from research.agents import (
    get_gathering_agent,
    get_plan_agent,
    get_synthesis_agent,
    get_verification_agent,
)
from src.logging import bind_context_vars, configure_structlog, get_logger

# Load environment variables from .env file
load_dotenv()

# Initialize structured logger (human-readable for POC)
configure_structlog(testing=True)
log = get_logger("research.workflow")


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
    # Generate correlation ID for this research workflow
    correlation_id = str(uuid4())[:8]  # Use short ID for readability
    bind_context_vars(correlation_id=correlation_id, query=query)

    workflow_start = perf_counter()
    log.info("research.workflow.started", query=query)
    print(f"Starting research: {query}")
    print(f"Correlation ID: {correlation_id}\n")

    try:
        # Initialize agents
        plan_agent = get_plan_agent()
        gathering_agent = get_gathering_agent()
        synthesis_agent = get_synthesis_agent()
        verification_agent = get_verification_agent()

        # Phase 1: Planning
        phase_start = perf_counter()
        log.info("research.planning.started")
        print("Phase 1: Creating research plan...")

        try:
            plan_result = await plan_agent.run(query)
            plan = plan_result.output
            duration_ms = int((perf_counter() - phase_start) * 1000)

            log.info(
                "research.planning.completed",
                step_count=len(plan.web_search_steps),
                duration_ms=duration_ms,
                summary_length=len(plan.executive_summary),
            )
            print(f"  Created {len(plan.web_search_steps)} search steps ({duration_ms}ms)")
            print(
                f"  Plan: {plan.executive_summary[:200]}..."
                if len(plan.executive_summary) > 200
                else f"  Plan: {plan.executive_summary}"
            )
            print()
        except Exception as e:
            log.exception("research.planning.failed", error=str(e))
            print(f"  ❌ Planning failed: {e}")
            raise

        # Phase 2: Gathering (parallel execution)
        phase_start = perf_counter()
        log.info("research.gathering.started", search_count=len(plan.web_search_steps))
        print("Phase 2: Gathering information...")

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(gathering_agent.run(step.search_terms)) for step in plan.web_search_steps]
            results = [task.result().output for task in tasks]
            duration_ms = int((perf_counter() - phase_start) * 1000)

            # Log metrics for each search
            total_findings = sum(len(r.findings) for r in results)
            total_sources = sum(len(r.sources) for r in results)

            log.info(
                "research.gathering.completed",
                search_count=len(results),
                findings_count=total_findings,
                sources_count=total_sources,
                duration_ms=duration_ms,
            )
            print(f"  Completed {len(results)} searches ({duration_ms}ms)")
            print(f"  Found {total_findings} findings from {total_sources} sources")
            for i, result in enumerate(results, 1):
                preview = " ".join(result.findings[:2]) if result.findings else "No findings"
                preview = preview[:200] + "..." if len(preview) > 200 else preview
                print(f"    {i}. {preview}")
            print()
        except Exception as e:
            log.exception("research.gathering.failed", error=str(e))
            print(f"  ❌ Gathering failed: {e}")
            raise

        # Phase 3: Synthesis
        phase_start = perf_counter()
        log.info("research.synthesis.started")
        print("Phase 3: Synthesizing report...")

        try:
            synthesis_prompt = f"""
            Original query: {query}
            Research plan: {plan.model_dump_json()}
            Search results: {json.dumps([r.model_dump() for r in results])}

            Create a comprehensive research report based on these materials.
            """
            report_result = await synthesis_agent.run(synthesis_prompt)
            report = report_result.output
            duration_ms = int((perf_counter() - phase_start) * 1000)

            log.info(
                "research.synthesis.completed",
                report_title=report.title,
                key_findings_count=len(report.key_findings),
                sources_count=len(report.sources),
                duration_ms=duration_ms,
            )
            print(f"  Report: {report.title} ({duration_ms}ms)")
            print(f"  {len(report.key_findings)} key findings from {len(report.sources)} sources")
            summary_preview = report.summary[:200] + "..." if len(report.summary) > 200 else report.summary
            print(f"  Summary: {summary_preview}")
            print()
        except Exception as e:
            log.exception("research.synthesis.failed", error=str(e))
            print(f"  ❌ Synthesis failed: {e}")
            raise

        # Phase 4: Verification
        phase_start = perf_counter()
        log.info("research.verification.started")
        print("Phase 4: Verifying report...")

        try:
            validation_prompt = f"""
            Validate this research report:
            {report.model_dump_json()}

            Check for quality, consistency, and reliability.
            """
            validation_result = await verification_agent.run(validation_prompt)
            validation = validation_result.output
            duration_ms = int((perf_counter() - phase_start) * 1000)

            log.info(
                "research.verification.completed",
                is_valid=validation.is_valid,
                confidence_score=validation.confidence_score,
                issues_count=len(validation.issues_found),
                recommendations_count=len(validation.recommendations),
                duration_ms=duration_ms,
            )
            print(f"  Valid: {validation.is_valid}, Confidence: {validation.confidence_score:.2f} ({duration_ms}ms)")
            if validation.issues_found:
                print(f"  Issues: {len(validation.issues_found)} found")
            if validation.recommendations:
                first_rec = (
                    validation.recommendations[0][:200] + "..."
                    if len(validation.recommendations[0]) > 200
                    else validation.recommendations[0]
                )
                print(f"  Recommendation: {first_rec}")
            print()
        except Exception as e:
            log.exception("research.verification.failed", error=str(e))
            print(f"  ❌ Verification failed: {e}")
            raise

        # Calculate total duration and log completion
        total_duration_ms = int((perf_counter() - workflow_start) * 1000)
        log.info(
            "research.workflow.completed",
            total_duration_ms=total_duration_ms,
            phases_completed=4,
        )

        return {
            "query": query,
            "plan": plan.model_dump(),
            "search_results": [r.model_dump() for r in results],
            "report": report.model_dump(),
            "validation": validation.model_dump(),
        }

    except Exception as e:
        total_duration_ms = int((perf_counter() - workflow_start) * 1000)
        log.exception(
            "research.workflow.failed",
            error=str(e),
            total_duration_ms=total_duration_ms,
        )
        raise


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m research.run_research 'your query'")
        sys.exit(1)

    query = sys.argv[1]

    try:
        result = asyncio.run(run_research(query))
    except Exception as e:
        log.exception("research.main.failed", error=str(e))
        print(f"\n❌ Research workflow failed: {e}")
        sys.exit(1)

    # Save outputs
    outputs_dir = Path(__file__).parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    try:
        # 1. Save full research results (all phases)
        full_output_file = outputs_dir / f"research_{timestamp}.json"
        full_output_file.write_text(json.dumps(result, indent=2))
        log.info("research.output.saved", file_type="full_json", path=str(full_output_file))
        print(f"\n✅ Full results saved to: {full_output_file}")

        # 2. Save isolated report as JSON
        report_json_file = outputs_dir / f"report_{timestamp}.json"
        report_json_file.write_text(json.dumps(result["report"], indent=2))
        log.info("research.output.saved", file_type="report_json", path=str(report_json_file))
        print(f"✅ Report JSON saved to: {report_json_file}")

        # 3. Save report as Markdown
        report_md_file = outputs_dir / f"report_{timestamp}.md"
        markdown_content = _format_report_as_markdown(result["report"], query, result["validation"])
        report_md_file.write_text(markdown_content)
        log.info("research.output.saved", file_type="report_markdown", path=str(report_md_file))
        print(f"✅ Report Markdown saved to: {report_md_file}")
    except Exception as e:
        log.exception("research.output.failed", error=str(e))
        print(f"❌ Failed to save outputs: {e}")
        sys.exit(1)


def _format_report_as_markdown(report: dict, query: str, validation: dict) -> str:
    """Format research report as Markdown."""
    md_lines = [
        f"# {report['title']}",
        "",
        f"**Research Query:** {query}",
        "",
        "---",
        "",
        "## Summary",
        "",
        report["summary"],
        "",
        "---",
        "",
        "## Key Findings",
        "",
    ]

    for i, finding in enumerate(report["key_findings"], 1):
        md_lines.append(f"{i}. {finding}")
        md_lines.append("")

    md_lines.extend(
        [
            "---",
            "",
            "## Sources",
            "",
        ]
    )

    for i, source in enumerate(report["sources"], 1):
        md_lines.append(f"{i}. [{source}]({source})")

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## Limitations",
            "",
            report["limitations"],
            "",
            "---",
            "",
            "## Quality Validation",
            "",
            f"- **Valid:** {validation['is_valid']}",
            f"- **Confidence Score:** {validation['confidence_score']:.2f}",
        ]
    )

    if validation.get("issues_found"):
        md_lines.extend(
            [
                "",
                "**Issues Found:**",
                "",
            ]
        )
        for issue in validation["issues_found"]:
            md_lines.append(f"- {issue}")

    if validation.get("recommendations"):
        md_lines.extend(
            [
                "",
                "**Recommendations:**",
                "",
            ]
        )
        for rec in validation["recommendations"]:
            md_lines.append(f"- {rec}")

    return "\n".join(md_lines)


if __name__ == "__main__":
    main()
