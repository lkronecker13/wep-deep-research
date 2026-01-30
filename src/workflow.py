"""Production research workflow with 4-phase pipeline."""

import asyncio
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic_ai import Agent

from src.agents import (
    get_gathering_agent,
    get_plan_agent,
    get_synthesis_agent,
    get_verification_agent,
)
from src.exceptions import (
    GatheringError,
    PlanningError,
    SynthesisError,
    VerificationError,
)
from src.logging import bind_context_vars, get_logger
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    ValidationResult,
)

log = get_logger("src.workflow")


async def run_research_workflow(
    query: str,
    *,
    plan_agent: Agent[Any, ResearchPlan] | None = None,
    gathering_agent: Agent[Any, SearchResult] | None = None,
    synthesis_agent: Agent[Any, ResearchReport] | None = None,
    verification_agent: Agent[Any, ValidationResult] | None = None,
) -> ResearchResult:
    """Execute 4-phase deep research workflow.

    Args:
        query: Research question to investigate.
        plan_agent: Override default planning agent (for testing).
        gathering_agent: Override default gathering agent (for testing).
        synthesis_agent: Override default synthesis agent (for testing).
        verification_agent: Override default verification agent (for testing).

    Returns:
        ResearchResult with all phases' outputs and timing metrics.

    Raises:
        PlanningError: When plan creation fails.
        GatheringError: When ALL search attempts fail.
        SynthesisError: When report synthesis fails.
        VerificationError: When report verification fails.
    """
    correlation_id = str(uuid4())[:8]
    bind_context_vars(correlation_id=correlation_id, query=query)

    # Resolve agents (use defaults if not injected)
    _plan_agent = plan_agent or get_plan_agent()
    _gathering_agent = gathering_agent or get_gathering_agent()
    _synthesis_agent = synthesis_agent or get_synthesis_agent()
    _verification_agent = verification_agent or get_verification_agent()

    workflow_start = perf_counter()
    log.info("workflow.started", query=query)

    # Phase 1: Planning
    phase_start = perf_counter()
    try:
        plan_result = await _plan_agent.run(query)
        plan = plan_result.output
    except Exception as e:
        log.error("workflow.planning.failed", error=str(e))
        raise PlanningError(topic=query, reason=str(e)) from e
    planning_ms = int((perf_counter() - phase_start) * 1000)
    log.info("workflow.planning.completed", duration_ms=planning_ms, step_count=len(plan.web_search_steps))

    # Phase 2: Gathering (parallel, tolerates partial failures)
    phase_start = perf_counter()
    results: list[SearchResult] = []
    errors: list[Exception] = []

    async def _gather_one(search_terms: str) -> None:
        try:
            result = await _gathering_agent.run(search_terms)
            results.append(result.output)
        except Exception as e:
            log.warning("workflow.gathering.search_failed", search_terms=search_terms, error=str(e))
            errors.append(e)

    async with asyncio.TaskGroup() as tg:
        for step in plan.web_search_steps:
            tg.create_task(_gather_one(step.search_terms))

    if not results:
        raise GatheringError(attempted=len(plan.web_search_steps), failed=len(errors))

    gathering_ms = int((perf_counter() - phase_start) * 1000)
    log.info("workflow.gathering.completed", duration_ms=gathering_ms, succeeded=len(results), failed=len(errors))

    # Phase 3: Synthesis
    phase_start = perf_counter()
    search_results_json = "[" + ", ".join(r.model_dump_json() for r in results) + "]"
    synthesis_prompt = (
        f"Original query: {query}\n"
        f"Research plan: {plan.model_dump_json()}\n"
        f"Search results: {search_results_json}\n\n"
        "Create a comprehensive research report based on these materials."
    )
    try:
        report_result = await _synthesis_agent.run(synthesis_prompt)
        report = report_result.output
    except Exception as e:
        log.error("workflow.synthesis.failed", error=str(e))
        raise SynthesisError(reason=str(e)) from e
    synthesis_ms = int((perf_counter() - phase_start) * 1000)
    log.info("workflow.synthesis.completed", duration_ms=synthesis_ms, title=report.title)

    # Phase 4: Verification
    phase_start = perf_counter()
    validation_prompt = (
        f"Validate this research report:\n{report.model_dump_json()}\n\n"
        "Check for quality, consistency, and reliability."
    )
    try:
        validation_result = await _verification_agent.run(validation_prompt)
        validation = validation_result.output
    except Exception as e:
        log.error("workflow.verification.failed", error=str(e))
        raise VerificationError(reason=str(e)) from e
    verification_ms = int((perf_counter() - phase_start) * 1000)
    log.info("workflow.verification.completed", duration_ms=verification_ms, is_valid=validation.is_valid)

    total_ms = int((perf_counter() - workflow_start) * 1000)
    log.info("workflow.completed", total_ms=total_ms)

    return ResearchResult(
        query=query,
        plan=plan,
        search_results=results,
        report=report,
        validation=validation,
        timings=PhaseTimings(
            planning_ms=planning_ms,
            gathering_ms=gathering_ms,
            synthesis_ms=synthesis_ms,
            verification_ms=verification_ms,
            total_ms=total_ms,
        ),
    )
