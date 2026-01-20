# Phase 1: Deep Research POC Implementation Plan

## Goal
Prove deep research agent value with 4-phase workflow (Planning → Gathering → Synthesis → Verification) using PydanticAI.

## Current State
- `research/` folder exists (only has `EDA.ipynb`)
- `src/logging.py` exists (reusable)
- Dev tooling ready (`just validate-branch`)
- No PydanticAI dependencies yet

---

## Files to Create

```
research/
├── __init__.py              # Package marker
├── run_research.py          # CLI entry point + workflow orchestration
├── agents.py                # All 4 PydanticAI agents
├── models.py                # Pydantic models for structured outputs
└── outputs/                 # JSON results directory (gitignored)
```

**Total: ~260 lines of Python**

---

## Implementation Steps

### 1. Add Dependencies
**File**: `pyproject.toml`

Add to `[project.dependencies]`:
```toml
"pydantic-ai[anthropic,google]>=0.2.0",
```

Then run: `uv sync`

### 2. Create `research/models.py` (~60 lines)

```python
from pydantic import BaseModel
from typing import Annotated
from annotated_types import MaxLen

class SearchStep(BaseModel):
    search_terms: str
    purpose: str

class ResearchPlan(BaseModel):
    executive_summary: str
    web_search_steps: Annotated[list[SearchStep], MaxLen(5)]
    analysis_instructions: str

class SearchResult(BaseModel):
    query: str
    findings: list[str]
    sources: list[str]

class ResearchReport(BaseModel):
    title: str
    summary: str
    key_findings: list[str]
    sources: list[str]
    limitations: str

class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float  # 0.0 - 1.0
    issues_found: list[str]
    recommendations: list[str]
```

### 3. Create `research/agents.py` (~80 lines)

```python
from pydantic_ai import Agent
from pydantic_ai.builtin_tools import WebSearchTool
from research.models import ResearchPlan, SearchResult, ResearchReport, ValidationResult

plan_agent = Agent(
    'anthropic:claude-sonnet-4-5',
    instructions="""You are a research planning expert. Given a query, create a
    structured research plan with up to 5 web search steps...""",
    output_type=ResearchPlan,
    name='plan_agent',
)

gathering_agent = Agent(
    'google-gla:gemini-2.5-flash',
    instructions="""You are a research gatherer. Execute the search and extract
    key findings with sources...""",
    builtin_tools=[WebSearchTool()],
    output_type=SearchResult,
    name='gathering_agent',
)

synthesis_agent = Agent(
    'anthropic:claude-sonnet-4-5',
    instructions="""You are a research synthesizer. Combine search results into
    a coherent report...""",
    output_type=ResearchReport,
    name='synthesis_agent',
)

verification_agent = Agent(
    'anthropic:claude-sonnet-4-5',
    instructions="""You are a research validator. Verify the report quality,
    check for contradictions, assess source reliability...""",
    output_type=ValidationResult,
    name='verification_agent',
)
```

### 4. Create `research/run_research.py` (~120 lines)

```python
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from research.agents import plan_agent, gathering_agent, synthesis_agent, verification_agent

async def run_research(query: str) -> dict:
    print(f"Starting research: {query}\n")

    # Phase 1: Planning
    print("Phase 1: Creating research plan...")
    plan_result = await plan_agent.run(query)
    plan = plan_result.data
    print(f"  Created {len(plan.web_search_steps)} search steps\n")

    # Phase 2: Gathering (parallel)
    print("Phase 2: Gathering information...")
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(gathering_agent.run(step.search_terms))
            for step in plan.web_search_steps
        ]
    results = [task.result().data for task in tasks]
    print(f"  Completed {len(results)} searches\n")

    # Phase 3: Synthesis
    print("Phase 3: Synthesizing report...")
    synthesis_prompt = f"""
    Original query: {query}
    Research plan: {plan.model_dump_json()}
    Search results: {json.dumps([r.model_dump() for r in results])}
    """
    report_result = await synthesis_agent.run(synthesis_prompt)
    report = report_result.data
    print(f"  Report: {report.title}\n")

    # Phase 4: Verification
    print("Phase 4: Verifying report...")
    validation_result = await verification_agent.run(report.model_dump_json())
    validation = validation_result.data
    print(f"  Valid: {validation.is_valid}, Confidence: {validation.confidence_score}\n")

    return {
        "query": query,
        "plan": plan.model_dump(),
        "search_results": [r.model_dump() for r in results],
        "report": report.model_dump(),
        "validation": validation.model_dump(),
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m research.run_research 'your query'")
        sys.exit(1)

    query = sys.argv[1]
    result = asyncio.run(run_research(query))

    # Save output
    outputs_dir = Path(__file__).parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = outputs_dir / f"research_{timestamp}.json"
    output_file.write_text(json.dumps(result, indent=2))
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
```

### 5. Create `research/__init__.py`

```python
"""Deep Research POC - Phase 1"""
```

### 6. Add outputs/ to .gitignore

Append to `.gitignore`:
```
# Research outputs
research/outputs/
```

---

## Environment Setup

```bash
# Required API keys (set in .env or export)
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."  # For Gemini
```

---

## Verification

### Run the POC
```bash
python -m research.run_research "What are the latest developments in quantum computing?"
```

### Expected Output
1. Console shows 4-phase progress
2. JSON file created in `research/outputs/`
3. JSON contains: query, plan, search_results, report, validation

### Success Criteria
- [ ] CLI completes end-to-end 4-phase workflow
- [ ] JSON output contains all 5 sections
- [ ] Parallel execution of searches works
- [ ] Typical query completes in <2 minutes
- [ ] Validation phase provides meaningful quality assessment

---

## Notes

- **No tests required** for Phase 1 (POC/exploration phase)
- **No `just validate-branch`** needed (research/ is excluded)
- Agent prompts will need iteration based on output quality
- This code becomes the foundation for Phase 2 (will be copied to src/)
