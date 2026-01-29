"""Pydantic models for deep research workflow."""

from pydantic import BaseModel, Field


class SearchStep(BaseModel):
    """A single web search step in the research plan."""

    search_terms: str = Field(
        min_length=1,
        description="Search query terms to execute",
        examples=["quantum computing breakthroughs 2024"],
    )
    purpose: str = Field(
        min_length=1,
        description="Goal or rationale for this search step",
        examples=["Identify recent technical advances in quantum error correction"],
    )


class ResearchPlan(BaseModel):
    """Structured research plan with search steps."""

    executive_summary: str = Field(
        description="High-level overview of research strategy and approach",
        examples=[
            "Research quantum computing by exploring recent breakthroughs, practical applications, and current limitations"
        ],
    )
    web_search_steps: list[SearchStep] = Field(
        min_length=1,
        max_length=5,
        description="1-5 targeted web searches to execute in parallel",
        examples=[
            [
                {
                    "search_terms": "quantum computing breakthroughs 2024",
                    "purpose": "Identify recent technical advances",
                },
                {
                    "search_terms": "quantum computing applications industry",
                    "purpose": "Find practical use cases",
                },
            ]
        ],
    )
    analysis_instructions: str = Field(
        description="Guidance for synthesis agent on how to analyze and structure findings",
        examples=[
            "Focus on recent developments, emphasize practical applications, note technical limitations and challenges"
        ],
    )


class SearchResult(BaseModel):
    """Results from a web search query."""

    query: str = Field(
        description="The search query that was executed",
        examples=["quantum computing breakthroughs 2024"],
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Key facts and insights discovered from this search",
        examples=[
            [
                "Google achieved quantum error correction breakthrough in 2024",
                "IBM announced 127-qubit quantum processor with improved coherence times",
            ]
        ],
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of web sources where findings were discovered",
        examples=[["https://www.nature.com/articles/quantum-2024", "https://research.ibm.com/quantum"]],
    )


class ResearchReport(BaseModel):
    """Final synthesized research report."""

    title: str = Field(
        description="Concise title summarizing the research topic",
        examples=["Recent Advances in Quantum Computing: 2024 Analysis"],
    )
    summary: str = Field(
        description="Executive summary synthesizing all findings into a coherent narrative",
        examples=[
            "Quantum computing achieved significant breakthroughs in 2024, with major advances in error correction and qubit scalability..."
        ],
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Bullet-point list of the most important discoveries and insights",
        examples=[
            [
                "Error correction techniques reduced qubit error rates by 50%",
                "Commercial applications now viable in drug discovery and cryptography",
                "Hardware costs remain a barrier to widespread adoption",
            ]
        ],
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Complete list of URLs cited in the report",
        examples=[
            [
                "https://www.nature.com/articles/quantum-2024",
                "https://research.ibm.com/quantum",
                "https://quantumcomputing.com/industry-report",
            ]
        ],
    )
    limitations: str = Field(
        default="",
        description="Acknowledged gaps, uncertainties, or constraints in the research",
        examples=["Limited data on long-term stability; most sources focus on recent developments only"],
    )


class ValidationResult(BaseModel):
    """Quality validation of research report."""

    is_valid: bool = Field(
        description="Whether the research report meets quality standards",
        examples=[True],
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score from 0.0 (lowest) to 1.0 (highest) based on completeness, accuracy, and source quality",
        examples=[0.85],
    )
    issues_found: list[str] = Field(
        default_factory=list,
        description="List of quality issues or concerns identified during validation",
        examples=[["Limited geographic diversity in sources", "Some claims lack direct citations"]],
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggested improvements or additional research directions",
        examples=[["Add more peer-reviewed sources", "Expand analysis of emerging competitors"]],
    )


class PhaseTimings(BaseModel):
    """Timing metrics for each research phase."""

    planning_ms: int = Field(
        ge=0,
        description="Time spent creating research plan (milliseconds)",
        examples=[3500],
    )
    gathering_ms: int = Field(
        ge=0,
        description="Time spent executing web searches in parallel (milliseconds)",
        examples=[12000],
    )
    synthesis_ms: int = Field(
        ge=0,
        description="Time spent generating research report (milliseconds)",
        examples=[8000],
    )
    verification_ms: int = Field(
        ge=0,
        description="Time spent validating report quality (milliseconds)",
        examples=[2500],
    )
    total_ms: int = Field(
        ge=0,
        description="Total workflow execution time (milliseconds)",
        examples=[26000],
    )


class ResearchResult(BaseModel):
    """Complete result from a research workflow run."""

    query: str = Field(
        min_length=1,
        description="Original research question that was submitted",
        examples=["What are the latest developments in quantum computing?"],
    )
    plan: ResearchPlan = Field(
        description="Structured research plan created by planning agent",
    )
    search_results: list[SearchResult] = Field(
        description="Raw search results from all executed web searches",
    )
    report: ResearchReport = Field(
        description="Final synthesized research report",
    )
    validation: ValidationResult = Field(
        description="Quality validation results from verification agent",
    )
    timings: PhaseTimings = Field(
        description="Performance metrics for each workflow phase",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are the latest developments in quantum computing?",
                    "plan": {
                        "executive_summary": "Research quantum computing by exploring recent breakthroughs, practical applications, and current limitations",
                        "web_search_steps": [
                            {
                                "search_terms": "quantum computing breakthroughs 2024",
                                "purpose": "Identify recent technical advances",
                            },
                            {
                                "search_terms": "quantum computing applications industry",
                                "purpose": "Find practical use cases",
                            },
                        ],
                        "analysis_instructions": "Focus on recent developments, emphasize practical applications, note technical limitations and challenges",
                    },
                    "search_results": [
                        {
                            "query": "quantum computing breakthroughs 2024",
                            "findings": [
                                "Google achieved quantum error correction breakthrough in 2024",
                                "IBM announced 127-qubit quantum processor with improved coherence times",
                            ],
                            "sources": [
                                "https://www.nature.com/articles/quantum-2024",
                                "https://research.ibm.com/quantum",
                            ],
                        }
                    ],
                    "report": {
                        "title": "Recent Advances in Quantum Computing: 2024 Analysis",
                        "summary": "Quantum computing achieved significant breakthroughs in 2024, with major advances in error correction and qubit scalability...",
                        "key_findings": [
                            "Error correction techniques reduced qubit error rates by 50%",
                            "Commercial applications now viable in drug discovery and cryptography",
                            "Hardware costs remain a barrier to widespread adoption",
                        ],
                        "sources": [
                            "https://www.nature.com/articles/quantum-2024",
                            "https://research.ibm.com/quantum",
                            "https://quantumcomputing.com/industry-report",
                        ],
                        "limitations": "Limited data on long-term stability; most sources focus on recent developments only",
                    },
                    "validation": {
                        "is_valid": True,
                        "confidence_score": 0.85,
                        "issues_found": ["Limited geographic diversity in sources"],
                        "recommendations": [
                            "Add more peer-reviewed sources",
                            "Expand analysis of emerging competitors",
                        ],
                    },
                    "timings": {
                        "planning_ms": 3500,
                        "gathering_ms": 12000,
                        "synthesis_ms": 8000,
                        "verification_ms": 2500,
                        "total_ms": 26000,
                    },
                }
            ]
        }
    }
