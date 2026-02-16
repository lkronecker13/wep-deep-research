"""PydanticAI agents for deep research workflow."""

import os
from functools import lru_cache

from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.agent import InstrumentationSettings

from research.models import ResearchPlan, ResearchReport, SearchResult, ValidationResult

# Model configuration - centralized for easy updates
CLAUDE_MODEL = "anthropic:claude-sonnet-4-5"
GEMINI_MODEL = "google-gla:gemini-2.5-flash"

# Retry configuration
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))


@lru_cache(maxsize=1)
def get_plan_agent() -> Agent[None, ResearchPlan]:
    """Get or create the planning agent (cached)."""
    return Agent(
        CLAUDE_MODEL,
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
        name="plan_agent",
        instrument=InstrumentationSettings(version=2),
    )


@lru_cache(maxsize=1)
def get_gathering_agent() -> Agent[None, SearchResult]:
    """Get or create the gathering agent (cached)."""
    return Agent(
        GEMINI_MODEL,
        instructions="""You are a research gatherer. Execute the search and extract
        key findings with sources.

        Your task:
        - Use the web search tool to find relevant information
        - Extract key facts, statistics, and insights
        - Identify credible sources
        - Focus on accuracy and relevance
        - Avoid speculation or unsupported claims

        CRITICAL - JSON Output Requirements:
        - Return ONLY valid JSON that parses correctly
        - Each finding must be a complete string (no truncation)
        - Each source must be a valid URL string
        - Do NOT wrap output in markdown code blocks (no ```json markers)
        - Do NOT include trailing commas in arrays or objects
        - Ensure all strings use proper escape sequences (\\n, \\", \\\\)
        - Do NOT truncate output - complete all fields fully
        - If unsure about a finding, omit it rather than returning incomplete data

        Your output MUST include:
        - query: the search query you executed
        - findings: a list of key findings (strings)
        - sources: a list of source URLs (strings)""",
        builtin_tools=[WebSearchTool()],
        retries=GEMINI_MAX_RETRIES,
        output_type=SearchResult,
        name="gathering_agent",
        instrument=InstrumentationSettings(version=2),
    )


@lru_cache(maxsize=1)
def get_synthesis_agent() -> Agent[None, ResearchReport]:
    """Get or create the synthesis agent (cached)."""
    return Agent(
        CLAUDE_MODEL,
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
        name="synthesis_agent",
        instrument=InstrumentationSettings(version=2),
    )


@lru_cache(maxsize=1)
def get_verification_agent() -> Agent[None, ValidationResult]:
    """Get or create the verification agent (cached)."""
    return Agent(
        CLAUDE_MODEL,
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
        name="verification_agent",
        instrument=InstrumentationSettings(version=2),
    )
