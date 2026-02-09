"""Production evaluation dataset for tech consulting firm regression testing.

Defines 35 evaluation questions across 7 consulting domains (5 per domain)
with priority levels for smoke testing and full regression runs.

Priority Distribution:
- P0 (blocker):  7 questions (1 per domain) - Smoke tests
- P1 (critical): 7 questions (1 per domain) - Core business scenarios
- P2 (high):    14 questions (2 per domain) - Standard regression
- P3 (medium):   7 questions (1 per domain) - Advanced/edge cases
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from research.evaluation.schemas import TestPriority


class ConsultingDomain(str, Enum):
    """Production domains for tech consulting firm."""

    DATA = "data"  # Data engineering, analytics, warehousing
    CYBERSECURITY = "cybersecurity"  # Security, compliance, threat detection
    AI = "ai"  # ML, LLMs, AI strategy
    FINANCE = "finance"  # Financial analysis, forecasting, reporting
    SALES = "sales"  # Sales strategy, CRM, pipeline
    MANAGEMENT = "management"  # Leadership, operations, strategy
    MARKETING = "marketing"  # Digital marketing, campaigns, analytics


class ProductionEvalQuestion(BaseModel):
    """Evaluation question for production regression testing."""

    id: str = Field(min_length=1, max_length=50, description="Unique question identifier")
    query: str = Field(min_length=10, max_length=500, description="Research question")
    domain: ConsultingDomain = Field(description="Consulting domain category")
    priority: TestPriority = Field(description="Test priority (P0=blocker, P1=critical, etc.)")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    description: str = Field(default="", description="Optional context about the test case")


# Production dataset with 35 questions (5 per domain)
_PRODUCTION_QUESTIONS: list[ProductionEvalQuestion] = [
    # ============================================================
    # DATA DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="data_001",
        query="What is the difference between Snowflake and Databricks for data warehousing?",
        domain=ConsultingDomain.DATA,
        priority=TestPriority.P0,
        tags=["smoke", "architecture", "cloud-data"],
        description="Smoke test: Basic cloud data platform comparison",
    ),
    ProductionEvalQuestion(
        id="data_002",
        query="What are best practices for implementing CDC (Change Data Capture) in modern data pipelines?",
        domain=ConsultingDomain.DATA,
        priority=TestPriority.P1,
        tags=["regression", "data-engineering", "real-time"],
        description="Core: Real-time data integration patterns",
    ),
    ProductionEvalQuestion(
        id="data_003",
        query="How should organizations choose between dbt Cloud and custom Airflow DAGs for data transformation?",
        domain=ConsultingDomain.DATA,
        priority=TestPriority.P2,
        tags=["regression", "tooling", "orchestration"],
        description="Standard: Data transformation tool selection",
    ),
    ProductionEvalQuestion(
        id="data_004",
        query="What are the performance optimization strategies for large-scale data joins in BigQuery?",
        domain=ConsultingDomain.DATA,
        priority=TestPriority.P2,
        tags=["regression", "performance", "bigquery"],
        description="Standard: Cloud DW performance tuning",
    ),
    ProductionEvalQuestion(
        id="data_005",
        query="How do data mesh principles change the traditional centralized data warehouse approach?",
        domain=ConsultingDomain.DATA,
        priority=TestPriority.P3,
        tags=["regression", "architecture", "emerging"],
        description="Advanced: Emerging data architecture paradigms",
    ),
    # ============================================================
    # CYBERSECURITY DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="cyber_001",
        query="What are the OWASP Top 10 security vulnerabilities and how should organizations address them?",
        domain=ConsultingDomain.CYBERSECURITY,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "compliance"],
        description="Smoke test: Core web security knowledge",
    ),
    ProductionEvalQuestion(
        id="cyber_002",
        query="What security controls should be implemented for LLM applications handling sensitive data?",
        domain=ConsultingDomain.CYBERSECURITY,
        priority=TestPriority.P1,
        tags=["regression", "ai-security", "emerging"],
        description="Core: AI application security requirements",
    ),
    ProductionEvalQuestion(
        id="cyber_003",
        query="How do zero-trust architecture principles apply to cloud-native applications?",
        domain=ConsultingDomain.CYBERSECURITY,
        priority=TestPriority.P2,
        tags=["regression", "cloud-security", "architecture"],
        description="Standard: Modern security architecture",
    ),
    ProductionEvalQuestion(
        id="cyber_004",
        query="What are the compliance requirements and technical controls for SOC 2 Type II certification?",
        domain=ConsultingDomain.CYBERSECURITY,
        priority=TestPriority.P2,
        tags=["regression", "compliance", "audit"],
        description="Standard: Compliance framework implementation",
    ),
    ProductionEvalQuestion(
        id="cyber_005",
        query="How can organizations detect and prevent supply chain attacks in their software dependencies?",
        domain=ConsultingDomain.CYBERSECURITY,
        priority=TestPriority.P3,
        tags=["regression", "supply-chain", "threat-detection"],
        description="Advanced: Supply chain security",
    ),
    # ============================================================
    # AI DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="ai_001",
        query="What is RAG (Retrieval Augmented Generation) and when should it be used versus fine-tuning?",
        domain=ConsultingDomain.AI,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "llm"],
        description="Smoke test: Core LLM architecture patterns",
    ),
    ProductionEvalQuestion(
        id="ai_002",
        query="How do you evaluate and compare different LLM providers for production applications?",
        domain=ConsultingDomain.AI,
        priority=TestPriority.P1,
        tags=["regression", "evaluation", "production"],
        description="Core: LLM provider selection criteria",
    ),
    ProductionEvalQuestion(
        id="ai_003",
        query="What are the architectural patterns for building multi-agent AI systems?",
        domain=ConsultingDomain.AI,
        priority=TestPriority.P2,
        tags=["regression", "architecture", "agents"],
        description="Standard: Multi-agent system design",
    ),
    ProductionEvalQuestion(
        id="ai_004",
        query="What are the key considerations for deploying ML models in production environments?",
        domain=ConsultingDomain.AI,
        priority=TestPriority.P2,
        tags=["regression", "mlops", "deployment"],
        description="Standard: MLOps best practices",
    ),
    ProductionEvalQuestion(
        id="ai_005",
        query="What strategies exist for reducing hallucinations in LLM-powered enterprise applications?",
        domain=ConsultingDomain.AI,
        priority=TestPriority.P3,
        tags=["regression", "quality", "reliability"],
        description="Advanced: LLM reliability engineering",
    ),
    # ============================================================
    # FINANCE DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="finance_001",
        query="What are the key financial metrics for evaluating SaaS company performance?",
        domain=ConsultingDomain.FINANCE,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "saas"],
        description="Smoke test: Core SaaS financial metrics",
    ),
    ProductionEvalQuestion(
        id="finance_002",
        query="How should CFOs evaluate the ROI of AI and automation investments?",
        domain=ConsultingDomain.FINANCE,
        priority=TestPriority.P1,
        tags=["regression", "roi", "ai-investment"],
        description="Core: Technology investment analysis",
    ),
    ProductionEvalQuestion(
        id="finance_003",
        query="What are best practices for financial forecasting in high-growth tech companies?",
        domain=ConsultingDomain.FINANCE,
        priority=TestPriority.P2,
        tags=["regression", "forecasting", "planning"],
        description="Standard: FP&A for tech companies",
    ),
    ProductionEvalQuestion(
        id="finance_004",
        query="How does ASC 606 revenue recognition apply to multi-year SaaS contracts?",
        domain=ConsultingDomain.FINANCE,
        priority=TestPriority.P2,
        tags=["regression", "compliance", "accounting"],
        description="Standard: Revenue recognition compliance",
    ),
    ProductionEvalQuestion(
        id="finance_005",
        query="What financial controls and processes are needed for SOX compliance in tech startups?",
        domain=ConsultingDomain.FINANCE,
        priority=TestPriority.P3,
        tags=["regression", "compliance", "controls"],
        description="Advanced: Financial compliance readiness",
    ),
    # ============================================================
    # SALES DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="sales_001",
        query="What are the stages of a typical B2B SaaS sales pipeline?",
        domain=ConsultingDomain.SALES,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "pipeline"],
        description="Smoke test: Core sales process knowledge",
    ),
    ProductionEvalQuestion(
        id="sales_002",
        query="How can sales teams use AI-powered tools to improve pipeline conversion rates?",
        domain=ConsultingDomain.SALES,
        priority=TestPriority.P1,
        tags=["regression", "ai-sales", "optimization"],
        description="Core: AI-enhanced sales operations",
    ),
    ProductionEvalQuestion(
        id="sales_003",
        query="What CRM implementation strategies work best for enterprise sales organizations?",
        domain=ConsultingDomain.SALES,
        priority=TestPriority.P2,
        tags=["regression", "crm", "implementation"],
        description="Standard: CRM deployment best practices",
    ),
    ProductionEvalQuestion(
        id="sales_004",
        query="How do product-led growth and sales-led growth strategies differ for B2B SaaS?",
        domain=ConsultingDomain.SALES,
        priority=TestPriority.P2,
        tags=["regression", "strategy", "growth"],
        description="Standard: Go-to-market strategy comparison",
    ),
    ProductionEvalQuestion(
        id="sales_005",
        query="What metrics should sales leaders track to diagnose pipeline health issues?",
        domain=ConsultingDomain.SALES,
        priority=TestPriority.P3,
        tags=["regression", "analytics", "metrics"],
        description="Advanced: Sales analytics and diagnostics",
    ),
    # ============================================================
    # MANAGEMENT DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="mgmt_001",
        query="What are the key elements of OKRs (Objectives and Key Results) for tech companies?",
        domain=ConsultingDomain.MANAGEMENT,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "planning"],
        description="Smoke test: Core goal-setting framework",
    ),
    ProductionEvalQuestion(
        id="mgmt_002",
        query="How should tech companies structure their engineering teams for maximum productivity?",
        domain=ConsultingDomain.MANAGEMENT,
        priority=TestPriority.P1,
        tags=["regression", "org-design", "engineering"],
        description="Core: Engineering organization design",
    ),
    ProductionEvalQuestion(
        id="mgmt_003",
        query="What are effective strategies for managing remote and hybrid development teams?",
        domain=ConsultingDomain.MANAGEMENT,
        priority=TestPriority.P2,
        tags=["regression", "remote-work", "culture"],
        description="Standard: Distributed team management",
    ),
    ProductionEvalQuestion(
        id="mgmt_004",
        query="How do companies transition from project-based to product-based operating models?",
        domain=ConsultingDomain.MANAGEMENT,
        priority=TestPriority.P2,
        tags=["regression", "transformation", "product"],
        description="Standard: Operating model transformation",
    ),
    ProductionEvalQuestion(
        id="mgmt_005",
        query="What frameworks exist for making effective technology architecture decisions?",
        domain=ConsultingDomain.MANAGEMENT,
        priority=TestPriority.P3,
        tags=["regression", "architecture", "decision-making"],
        description="Advanced: Technical decision frameworks",
    ),
    # ============================================================
    # MARKETING DOMAIN (5 questions)
    # ============================================================
    ProductionEvalQuestion(
        id="mktg_001",
        query="What are the key stages of a B2B marketing funnel?",
        domain=ConsultingDomain.MARKETING,
        priority=TestPriority.P0,
        tags=["smoke", "fundamentals", "funnel"],
        description="Smoke test: Core marketing funnel knowledge",
    ),
    ProductionEvalQuestion(
        id="mktg_002",
        query="How are companies using AI for content marketing and SEO optimization?",
        domain=ConsultingDomain.MARKETING,
        priority=TestPriority.P1,
        tags=["regression", "ai-marketing", "content"],
        description="Core: AI-powered marketing strategies",
    ),
    ProductionEvalQuestion(
        id="mktg_003",
        query="What attribution models work best for multi-touch B2B marketing campaigns?",
        domain=ConsultingDomain.MARKETING,
        priority=TestPriority.P2,
        tags=["regression", "analytics", "attribution"],
        description="Standard: Marketing measurement and attribution",
    ),
    ProductionEvalQuestion(
        id="mktg_004",
        query="How should companies structure their marketing technology stack in 2025?",
        domain=ConsultingDomain.MARKETING,
        priority=TestPriority.P2,
        tags=["regression", "martech", "tooling"],
        description="Standard: Martech stack architecture",
    ),
    ProductionEvalQuestion(
        id="mktg_005",
        query="What are effective strategies for account-based marketing in enterprise tech sales?",
        domain=ConsultingDomain.MARKETING,
        priority=TestPriority.P3,
        tags=["regression", "abm", "enterprise"],
        description="Advanced: ABM program design",
    ),
]


def get_production_dataset() -> list[ProductionEvalQuestion]:
    """Get the full production evaluation dataset.

    Returns:
        List of 35 evaluation questions across 7 domains (5 per domain).
    """
    return _PRODUCTION_QUESTIONS.copy()


def get_smoke_test_subset() -> list[ProductionEvalQuestion]:
    """Get P0 priority questions for quick smoke testing.

    Returns:
        List of 7 smoke test questions (1 per domain).
    """
    return [q for q in _PRODUCTION_QUESTIONS if q.priority == TestPriority.P0]


def get_critical_subset() -> list[ProductionEvalQuestion]:
    """Get P0 and P1 priority questions for critical regression checks.

    Returns:
        List of 14 high-priority questions (2 per domain).
    """
    return [q for q in _PRODUCTION_QUESTIONS if q.priority in (TestPriority.P0, TestPriority.P1)]


def get_domain_questions(domain: ConsultingDomain) -> list[ProductionEvalQuestion]:
    """Filter questions by consulting domain.

    Args:
        domain: The consulting domain to filter by.

    Returns:
        List of 5 questions for the specified domain.
    """
    return [q for q in _PRODUCTION_QUESTIONS if q.domain == domain]


def get_questions_by_tag(tag: str) -> list[ProductionEvalQuestion]:
    """Filter questions by tag.

    Args:
        tag: The tag to filter by (case-insensitive).

    Returns:
        List of questions containing the specified tag.
    """
    tag_lower = tag.lower()
    return [q for q in _PRODUCTION_QUESTIONS if tag_lower in [t.lower() for t in q.tags]]


def get_questions_by_priority(priority: TestPriority) -> list[ProductionEvalQuestion]:
    """Filter questions by priority level.

    Args:
        priority: The TestPriority to filter by.

    Returns:
        List of questions with the specified priority.
    """
    return [q for q in _PRODUCTION_QUESTIONS if q.priority == priority]
