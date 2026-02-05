"""Demo mode fixtures for API testing without burning API keys."""

import os
from functools import lru_cache
from typing import AsyncIterator

from src.events import CompleteEvent, PhaseCompleteEvent, PhaseStartEvent
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)


def is_demo_mode_allowed() -> bool:
    """Check if demo mode is allowed in current environment.

    Demo mode is only allowed in development and staging environments
    for security and resource reasons.

    Returns:
        True if demo mode allowed, False otherwise
    """
    environment = os.getenv("ENVIRONMENT", "development")
    return environment in ("development", "staging")


@lru_cache(maxsize=1)
def get_demo_research_result(query: str) -> ResearchResult:
    """Generate cached demo research result for testing.

    Returns hardcoded quantum computing research for any query.
    Cached to avoid repeated Pydantic object construction.

    Args:
        query: User's research question (included in result)

    Returns:
        Complete ResearchResult with realistic mock data
    """
    return ResearchResult(
        query=query,
        plan=ResearchPlan(
            executive_summary="Research quantum computing by exploring recent breakthroughs, practical applications, and current limitations",
            web_search_steps=[
                SearchStep(
                    search_terms="quantum computing breakthroughs 2024",
                    purpose="Identify recent technical advances in quantum error correction",
                ),
                SearchStep(
                    search_terms="quantum computing applications industry",
                    purpose="Find practical use cases and commercial implementations",
                ),
                SearchStep(
                    search_terms="quantum computing limitations challenges",
                    purpose="Understand current technical barriers and constraints",
                ),
            ],
            analysis_instructions="Focus on recent developments, emphasize practical applications, note technical limitations and challenges",
        ),
        search_results=[
            SearchResult(
                query="quantum computing breakthroughs 2024",
                findings=[
                    "Google achieved quantum error correction breakthrough with surface code implementation",
                    "IBM announced 127-qubit quantum processor with improved coherence times exceeding 100 microseconds",
                    "Microsoft demonstrated topological qubits with reduced error rates",
                ],
                sources=[
                    "https://www.nature.com/articles/quantum-2024",
                    "https://research.ibm.com/quantum",
                    "https://www.microsoft.com/research/quantum",
                ],
            ),
            SearchResult(
                query="quantum computing applications industry",
                findings=[
                    "Drug discovery companies using quantum simulation for molecular modeling",
                    "Financial institutions applying quantum algorithms to portfolio optimization",
                    "Cryptography research accelerating post-quantum encryption standards",
                ],
                sources=[
                    "https://www.pharmaceutical-technology.com/quantum",
                    "https://www.jpmorgan.com/quantum-research",
                    "https://www.nist.gov/quantum-cryptography",
                ],
            ),
        ],
        report=ResearchReport(
            title="Recent Advances in Quantum Computing: 2024 Analysis",
            summary="Quantum computing achieved significant breakthroughs in 2024, with major advances in error correction and qubit scalability. Industry applications are emerging in pharmaceuticals, finance, and cryptography, though hardware costs and error rates remain barriers to widespread adoption.",
            key_findings=[
                "Error correction techniques reduced qubit error rates by 50% using surface code implementations",
                "Commercial applications now viable in drug discovery, financial modeling, and cryptography",
                "127-qubit systems demonstrated with coherence times exceeding 100 microseconds",
                "Hardware costs remain a barrier to widespread adoption outside research institutions",
                "Post-quantum cryptography standards accelerating due to quantum threat awareness",
            ],
            sources=[
                "https://www.nature.com/articles/quantum-2024",
                "https://research.ibm.com/quantum",
                "https://www.microsoft.com/research/quantum",
                "https://www.pharmaceutical-technology.com/quantum",
                "https://www.jpmorgan.com/quantum-research",
                "https://www.nist.gov/quantum-cryptography",
            ],
            limitations="Limited data on long-term stability of qubit systems; most sources focus on recent developments from major tech companies",
        ),
        validation=ValidationResult(
            is_valid=True,
            confidence_score=0.85,
            issues_found=[
                "Limited geographic diversity in sources",
                "Primarily industry sources rather than peer-reviewed research",
            ],
            recommendations=[
                "Add more peer-reviewed academic sources",
                "Expand analysis of emerging competitors beyond IBM/Google/Microsoft",
                "Include perspectives from quantum computing startups",
            ],
        ),
        timings=PhaseTimings(
            planning_ms=100,
            gathering_ms=200,
            synthesis_ms=150,
            verification_ms=50,
            total_ms=500,
        ),
    )


async def generate_demo_sse_stream(query: str) -> AsyncIterator[str]:
    """Generate demo SSE event stream with all 4 phases.

    Yields events instantly for rapid testing. Add small delays
    between phases for more realistic UX testing if needed.

    Args:
        query: User's research question

    Yields:
        Formatted SSE event strings
    """
    # Phase 1: Planning
    yield PhaseStartEvent(data={"phase": "planning"}).format()
    yield PhaseCompleteEvent(
        data={
            "phase": "planning",
            "duration_ms": 100,
            "output_summary": {
                "executive_summary": "Research quantum computing by exploring recent breakthroughs, practical applications, and current limitations",
                "search_steps": 3,
            },
        }
    ).format()

    # Phase 2: Gathering
    yield PhaseStartEvent(data={"phase": "gathering"}).format()
    yield PhaseCompleteEvent(
        data={
            "phase": "gathering",
            "duration_ms": 200,
            "output_summary": {
                "searches_completed": 2,
                "total_findings": 6,
            },
        }
    ).format()

    # Phase 3: Synthesis
    yield PhaseStartEvent(data={"phase": "synthesis"}).format()
    yield PhaseCompleteEvent(
        data={
            "phase": "synthesis",
            "duration_ms": 150,
            "output_summary": {
                "title": "Recent Advances in Quantum Computing: 2024 Analysis",
                "key_findings_count": 5,
            },
        }
    ).format()

    # Phase 4: Verification
    yield PhaseStartEvent(data={"phase": "verification"}).format()
    yield PhaseCompleteEvent(
        data={
            "phase": "verification",
            "duration_ms": 50,
            "output_summary": {
                "is_valid": True,
                "confidence_score": 0.85,
            },
        }
    ).format()

    # Final complete event with full result
    result = get_demo_research_result(query)
    yield CompleteEvent(data=result.model_dump()).format()
