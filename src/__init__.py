"""Deep Research Service - AI-powered research using multi-agent workflows"""

__version__ = "0.1.0"

from src.agents import (
    clear_agent_cache,
    create_gathering_agent,
    create_plan_agent,
    create_synthesis_agent,
    create_verification_agent,
    get_gathering_agent,
    get_plan_agent,
    get_synthesis_agent,
    get_verification_agent,
)
from src.exceptions import (
    GatheringError,
    PlanningError,
    ResearchPipelineError,
    SynthesisError,
    VerificationError,
)
from src.models import (
    PhaseTimings,
    ResearchPlan,
    ResearchReport,
    ResearchResult,
    SearchResult,
    SearchStep,
    ValidationResult,
)
from src.server import get_app
from src.workflow import run_research_workflow

__all__ = [
    # Models
    "SearchStep",
    "ResearchPlan",
    "SearchResult",
    "ResearchReport",
    "ValidationResult",
    "PhaseTimings",
    "ResearchResult",
    # Agent factories
    "create_plan_agent",
    "create_gathering_agent",
    "create_synthesis_agent",
    "create_verification_agent",
    # Agent getters
    "get_plan_agent",
    "get_gathering_agent",
    "get_synthesis_agent",
    "get_verification_agent",
    # Cache management
    "clear_agent_cache",
    # Exceptions
    "ResearchPipelineError",
    "PlanningError",
    "GatheringError",
    "SynthesisError",
    "VerificationError",
    # Workflow
    "run_research_workflow",
    # Server
    "get_app",
]
