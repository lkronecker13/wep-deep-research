"""PydanticAI agents for deep research workflow."""

import os
from functools import lru_cache
from typing import Any

from pydantic_ai import Agent, WebSearchTool

from src.research.models import (
    ResearchPlan,
    ResearchReport,
    SearchResult,
    ValidationResult,
)

DEFAULT_PLAN_MODEL = os.getenv("RESEARCH_PLAN_MODEL", "anthropic:claude-sonnet-4-5")
DEFAULT_GATHERING_MODEL = os.getenv("RESEARCH_GATHERING_MODEL", "google-gla:gemini-2.5-flash")
DEFAULT_SYNTHESIS_MODEL = os.getenv("RESEARCH_SYNTHESIS_MODEL", "anthropic:claude-sonnet-4-5")
DEFAULT_VERIFICATION_MODEL = os.getenv("RESEARCH_VERIFICATION_MODEL", "anthropic:claude-sonnet-4-5")


def create_plan_agent(model: Any = DEFAULT_PLAN_MODEL) -> Agent[None, ResearchPlan]:
    """Uncached factory - use with TestModel for tests."""
    return Agent(
        model,
        instructions="""You are a research planning expert. Given a query, create a
        structured research plan with up to 5 web search steps.
        Your plan should:
        - Break down the query into logical search components
        - Identify different angles to explore the topic
        - Prioritize depth over breadth
        - Provide clear purpose for each search step
        - Include analysis instructions for synthesis phase
        Keep search steps focused and specific.""",
        output_type=ResearchPlan,
        instrument=True,
        name="plan_agent",
    )


@lru_cache(maxsize=1)
def get_plan_agent(model: str = DEFAULT_PLAN_MODEL) -> Agent[None, ResearchPlan]:
    """Cached getter for production."""
    return create_plan_agent(model)


def create_gathering_agent(model: Any = DEFAULT_GATHERING_MODEL) -> Agent[None, SearchResult]:
    """Uncached factory - use with TestModel for tests."""
    return Agent(
        model,
        instructions="""You are a research gatherer. Execute the search and extract
        key findings with sources.
        Your task:
        - Use the web search tool to find relevant information
        - Extract key facts, statistics, and insights
        - Identify credible sources
        - Focus on accuracy and relevance
        - Avoid speculation or unsupported claims
        Return structured findings with source URLs.""",
        builtin_tools=[WebSearchTool()],
        output_type=SearchResult,
        instrument=True,
        name="gathering_agent",
    )


@lru_cache(maxsize=1)
def get_gathering_agent(model: str = DEFAULT_GATHERING_MODEL) -> Agent[None, SearchResult]:
    """Cached getter for production."""
    return create_gathering_agent(model)


def create_synthesis_agent(model: Any = DEFAULT_SYNTHESIS_MODEL) -> Agent[None, ResearchReport]:
    """Uncached factory - use with TestModel for tests."""
    return Agent(
        model,
        instructions="""You are a research synthesizer. Combine search results into
        a coherent report.
        Your report should:
        - Synthesize information from all search results
        - Identify patterns and themes
        - Present clear key findings
        - List all sources used
        - Acknowledge limitations and gaps
        - Be well-structured and readable
        Do not invent information. Stay grounded in the provided search results.""",
        output_type=ResearchReport,
        instrument=True,
        name="synthesis_agent",
    )


@lru_cache(maxsize=1)
def get_synthesis_agent(model: str = DEFAULT_SYNTHESIS_MODEL) -> Agent[None, ResearchReport]:
    """Cached getter for production."""
    return create_synthesis_agent(model)


def create_verification_agent(model: Any = DEFAULT_VERIFICATION_MODEL) -> Agent[None, ValidationResult]:
    """Uncached factory - use with TestModel for tests."""
    return Agent(
        model,
        instructions="""You are a research validator. Verify the report quality,
        check for contradictions, assess source reliability.
        Evaluate:
        - Internal consistency (no contradictions)
        - Source quality and diversity
        - Claim support (all findings backed by sources)
        - Completeness (addresses original query)
        - Balanced perspective (not biased)
        Provide:
        - Overall validity assessment
        - Confidence score (0.0-1.0)
        - Specific issues found
        - Recommendations for improvement
        Be thorough but fair in your assessment.""",
        output_type=ValidationResult,
        instrument=True,
        name="verification_agent",
    )


@lru_cache(maxsize=1)
def get_verification_agent(model: str = DEFAULT_VERIFICATION_MODEL) -> Agent[None, ValidationResult]:
    """Cached getter for production."""
    return create_verification_agent(model)


def clear_agent_cache() -> None:
    """Clear all agent caches."""
    get_plan_agent.cache_clear()
    get_gathering_agent.cache_clear()
    get_synthesis_agent.cache_clear()
    get_verification_agent.cache_clear()
