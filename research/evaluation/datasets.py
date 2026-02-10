"""Production evaluation dataset loaded from JSON.

Loads 35 evaluation questions across 7 consulting domains from
production_questions.json at module import time with Pydantic validation.

Priority Distribution:
- P0: 7 questions (smoke tests)
- P1: 7 questions (critical)
- P2: 14 questions (standard regression)
- P3: 7 questions (advanced scenarios)

Functions maintain backward compatibility:
- get_production_dataset() - All 35 questions
- get_smoke_test_subset() - 7 P0 questions
- get_critical_subset() - 14 P0+P1 questions
- get_domain_questions(domain) - 5 questions per domain
- get_questions_by_tag(tag) - Filter by tag
- get_questions_by_priority(priority) - Filter by priority
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

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


def _load_production_questions() -> list[ProductionEvalQuestion]:
    """Load production questions from JSON file.

    Loads from research/evaluation/production_questions.json and validates
    all questions using Pydantic models.

    Returns:
        List of validated ProductionEvalQuestion objects.

    Raises:
        FileNotFoundError: If production_questions.json is missing.
        json.JSONDecodeError: If JSON is malformed.
        pydantic.ValidationError: If questions fail Pydantic validation.
    """
    # Construct path relative to this file
    json_path = Path(__file__).parent / "production_questions.json"

    # Check file exists (fail fast with clear message)
    if not json_path.exists():
        raise FileNotFoundError(
            f"\nProduction questions JSON not found at: {json_path.resolve()}\n\n"
            "This file must exist for the evaluation system to function.\n"
            "If you are setting up a new environment, ensure the file is present in version control.\n"
            "Expected location: research/evaluation/production_questions.json"
        )

    # Load and parse JSON
    try:
        json_data = json_path.read_text(encoding="utf-8")
        questions_raw = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Failed to parse production_questions.json: {e.msg}",
            e.doc,
            e.pos,
        ) from e

    # Validate with Pydantic (raises ValidationError if invalid)
    questions = [ProductionEvalQuestion(**q) for q in questions_raw]

    return questions


# Production dataset with 35 questions loaded from JSON
_PRODUCTION_QUESTIONS: list[ProductionEvalQuestion] = _load_production_questions()


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
