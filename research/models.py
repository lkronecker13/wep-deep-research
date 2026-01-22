"""Pydantic models for deep research workflow."""

from typing import Annotated

from annotated_types import MaxLen
from pydantic import BaseModel


class SearchStep(BaseModel):
    """A single web search step in the research plan."""

    search_terms: str
    purpose: str


class ResearchPlan(BaseModel):
    """Structured research plan with search steps."""

    executive_summary: str
    web_search_steps: Annotated[list[SearchStep], MaxLen(5)]
    analysis_instructions: str


class SearchResult(BaseModel):
    """Results from a web search query."""

    query: str
    findings: list[str]
    sources: list[str]


class ResearchReport(BaseModel):
    """Final synthesized research report."""

    title: str
    summary: str
    key_findings: list[str]
    sources: list[str]
    limitations: str


class ValidationResult(BaseModel):
    """Quality validation of research report."""

    is_valid: bool
    confidence_score: float  # 0.0 - 1.0
    issues_found: list[str]
    recommendations: list[str]
