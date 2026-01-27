"""Pydantic models for deep research workflow."""

from pydantic import BaseModel, Field


class SearchStep(BaseModel):
    """A single web search step in the research plan."""

    search_terms: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class ResearchPlan(BaseModel):
    """Structured research plan with search steps."""

    executive_summary: str
    web_search_steps: list[SearchStep] = Field(min_length=1, max_length=5)
    analysis_instructions: str


class SearchResult(BaseModel):
    """Results from a web search query."""

    query: str
    findings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    """Final synthesized research report."""

    title: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    limitations: str = Field(default="")


class ValidationResult(BaseModel):
    """Quality validation of research report."""

    is_valid: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    issues_found: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PhaseTimings(BaseModel):
    """Timing metrics for each research phase."""

    planning_ms: int = Field(ge=0)
    gathering_ms: int = Field(ge=0)
    synthesis_ms: int = Field(ge=0)
    verification_ms: int = Field(ge=0)
    total_ms: int = Field(ge=0)


class ResearchResult(BaseModel):
    """Complete result from a research workflow run."""

    query: str = Field(min_length=1)
    plan: ResearchPlan
    search_results: list[SearchResult]
    report: ResearchReport
    validation: ValidationResult
    timings: PhaseTimings
