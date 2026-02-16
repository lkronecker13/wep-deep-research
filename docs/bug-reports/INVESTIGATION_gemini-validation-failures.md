# Bug Investigation: Gemini Output Validation Failures

## HYBRID APPROACH: Agent Review Updates

**Status**: Investigation plan reviewed by bb-ai-engineer and bb-backend-engineer  
**Approach**: Core investigation + critical production features  
**Updated**: 2026-02-11

### Critical Changes from Agent Reviews

#### From bb-ai-engineer (AI/LLM Perspective)

**Enhanced Testing** (Phase 2):
- Increase Wepoint tests from 20 → 30 runs
- Add rare entity tests ("XyzCorp") - 30 runs
- Add data capture: token counts, response latency, query length

**Strengthened Prompt** (Phase 4, Option B+):
```python
instructions="""Return ONLY valid JSON matching this exact structure:
{
  "query": "exact search query used",
  "findings": ["finding 1", "finding 2"],
  "sources": ["https://url1.com", "https://url2.com"]
}

Rules:
- Include 2-5 findings minimum
- Each source must be a complete URL
- NO markdown formatting, NO code fences
- NO additional fields or wrapper objects
"""
```

**Combined Fix Strategy** (Phase 4):
- ✅ Improved prompt (Option B+)
- ✅ Defensive validators with logging (Option A+)
- ✅ Check for PydanticAI built-in logging (before monkey-patch)
- ❌ Reject blind retry increase (Option C)

#### From bb-backend-engineer (Production Readiness)

**Permanent Observability** (Phase 1 - NEW):
```python
# Add to research/instrumentation.py (PRODUCTION)
class InstrumentedGatheringAgent:
    """Permanent observability wrapper (replaces debug patch)."""
    
    def __init__(self, agent):
        self.agent = agent
        self._failure_count = 0
        self._total_count = 0
    
    async def run(self, query: str):
        self._total_count += 1
        with tracer.start_as_current_span("gathering_agent.run") as span:
            span.set_attribute("query", query)
            try:
                result = await self.agent.run(query)
                span.set_attribute("success", True)
                log.info("gathering_success", query=query,
                         findings_count=len(result.output.findings),
                         token_count_input=getattr(result, 'input_tokens', None),
                         token_count_output=getattr(result, 'output_tokens', None))
                return result
            except ValidationError as e:
                self._failure_count += 1
                span.set_attribute("success", False)
                log.error("gathering_validation_failure",
                          query=query,
                          error_details=e.errors(),
                          failure_rate=self._failure_count / self._total_count)
                raise
```

**Response Sanitization** (Phase 4 - NEW):
```python
# Add to research/utils.py or research/models.py
def sanitize_gemini_response(raw: dict) -> dict:
    """Pre-validate Gemini response before Pydantic."""
    # Ensure findings/sources are lists
    for field in ["findings", "sources"]:
        if field in raw and not isinstance(raw[field], list):
            raw[field] = [raw[field]] if raw[field] else []
    # Ensure query exists
    if "query" not in raw:
        log.warning("missing_query_field", response=raw)
        raw["query"] = "UNKNOWN"
    return raw
```

**Exponential Backoff** (Phase 4 - REPLACE Option C):
```python
# Replace blind retry increase with backoff
async def run_with_backoff(agent, query: str, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await agent.run(query)
        except UnexpectedModelBehavior as e:
            if "validation" not in str(e).lower() or attempt == max_attempts - 1:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            log.warning("validation_retry", attempt=attempt+1, delay=delay)
            await asyncio.sleep(delay)
```

**Monitoring Metrics** (Phase 6 - NEW):
```python
# Required metrics for alerting
REQUIRED_METRICS = {
    "gathering.success_rate": "Alert if <90% (5-min window)",
    "gathering.latency_p95": "Alert if >5s",
    "gathering.validation_errors_total": "Alert if >10/hour",
}
```

### Updated Implementation Priorities

#### Must-Have (Hybrid Approach)
- [x] Phase 1: Permanent instrumentation (InstrumentedGatheringAgent)
- [x] Phase 2: Enhanced testing (30 runs, rare entities, token counts)
- [x] Phase 3: Root cause with expanded data
- [x] Phase 4: Combined fix (B+ prompt + A+ validators + sanitization + backoff)
- [x] Phase 5: Verification (concurrency tests added)
- [x] Phase 6: Monitoring metrics defined

#### Deferred to Phase 2 Production
- [ ] Load testing (defer until staging)
- [ ] Circuit breakers (defer until production metrics available)
- [ ] Model fallback (Gemini → Claude) - implement after root cause confirmed
- [ ] Phased rollout strategy (canary deployment)

---

# Bug Investigation: Gemini Output Validation Failures

## Context

The deep research service's gathering agent (using Gemini 2.5 Flash) experiences a **75% failure rate** for queries containing "Wepoint" while "onepoint" queries succeed 100% of the time. The error "Exceeded maximum retries (1) for output validation" originates from PydanticAI's validation retry mechanism.

**Impact**:
- High failure rate blocks research workflow completion
- Inconsistent behavior based on query content
- User experience degradation

**Known Facts**:
- Error occurs during Pydantic validation of Gemini's response
- SearchResult schema is simple and permissive (only `query` field required)
- Retry limit is set to 1 attempt
- Partial workaround: 25% of Wepoint searches succeed, allowing degraded continuation

**Investigation Goal**: Create comprehensive bug report with root cause analysis, reproduction steps, and recommended fixes.

---

## Investigation Plan

### Phase 1: Instrument for Deep Visibility (Day 1)

**Objective**: Capture raw Gemini responses and validation errors before they're lost in retry logic.

**Actions**:

1. **Create Debug Patch** - `research/debug_patch.py`:
   ```python
   """Monkey-patch PydanticAI to log validation failures."""
   import pydantic_ai._agent_graph as ag
   from src.logging import get_logger

   log = get_logger("debug.validation")
   original_increment = ag.GraphAgentState.increment_retries

   def patched_increment(self, max_result_retries, error=None, model_settings=None):
       if error:
           log.error("validation_error_before_retry",
                     error_type=type(error).__name__,
                     error_details=str(error),
                     retry_count=self.retries,
                     raw_response=str(self.message_history[-1] if self.message_history else None))
       return original_increment(self, max_result_retries, error, model_settings)

   ag.GraphAgentState.increment_retries = patched_increment
   ```

2. **Enhanced Exception Handling** in `research/run_research.py` (gathering phase):
   ```python
   try:
       result = await gathering_agent.run(step.search_terms)
   except Exception as e:
       log.error("gathering_failed",
                 query=step.search_terms,
                 exception=str(e),
                 exc_info=True)
       # Capture Pydantic ValidationError details
       if hasattr(e, '__cause__') and hasattr(e.__cause__, 'errors'):
           log.error("pydantic_validation_errors", errors=e.__cause__.errors())
       raise
   ```

3. **Enable DEBUG Logging** - Set `LOGGING_LEVEL=DEBUG` in `.env`

**Expected Output**:
- Raw Gemini JSON responses logged
- Pydantic validation error details captured
- Full exception context preserved

---

### Phase 2: Reproduce Reliably (Day 1-2)

**Objective**: Create minimal reproduction case with statistical validation.

**Create Debug Script** - `research/debug_wepoint.py`:

```python
"""Minimal reproduction script for Wepoint validation bug."""

import asyncio
from research.agents import get_gathering_agent
from src.logging import configure_structlog, get_logger

# Apply debug patch
import research.debug_patch  # noqa

configure_structlog(testing=True)
log = get_logger("debug.wepoint")

async def test_query(query: str, runs: int = 20):
    """Test a query N times and track success/failure."""
    agent = get_gathering_agent()
    results = {"success": 0, "failure": 0, "errors": []}

    for i in range(runs):
        try:
            result = await agent.run(query)
            results["success"] += 1
            log.info("success", run=i+1, query=query,
                     findings_count=len(result.output.findings))
        except Exception as e:
            results["failure"] += 1
            results["errors"].append({
                "run": i+1,
                "error": str(e),
                "type": type(e).__name__
            })
            log.error("failure", run=i+1, query=query, error=str(e))

    success_rate = results["success"] / runs * 100
    log.info("summary", query=query, success_rate=f"{success_rate:.1f}%", **results)
    return results

async def main():
    print("\n=== Testing 'Wepoint' (expected 25% success) ===")
    wepoint_results = await test_query("Wepoint", runs=20)

    print("\n=== Testing 'onepoint' (expected 100% success) ===")
    onepoint_results = await test_query("onepoint", runs=20)

    print("\n=== Comparison ===")
    print(f"Wepoint: {wepoint_results['success']}/20 ({wepoint_results['success']/20*100:.0f}%)")
    print(f"onepoint: {onepoint_results['success']}/20 ({onepoint_results['success']/20*100:.0f}%)")

    if wepoint_results["errors"]:
        print(f"\nFirst Wepoint error:\n{wepoint_results['errors'][0]}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run Test**:
```bash
cd /Users/lkronecker/ai-enhanced-engineer/projects/Wepoint/wep-deep-research
python research/debug_wepoint.py 2>&1 | tee debug_output.log
```

**Expected Output**:
- 40 test runs with detailed logs
- Confirmation of 75% failure rate for Wepoint
- Raw responses captured in `debug_output.log`

---

### Phase 3: Root Cause Analysis (Day 2-3)

**Objective**: Identify specific validation failure pattern.

**Test Hypotheses** (ordered by likelihood):

1. **Type Mismatch**: Gemini returns string instead of list
   ```python
   # Failing:
   {"query": "Wepoint", "findings": "text", "sources": "url"}
   # Expected:
   {"query": "Wepoint", "findings": ["text"], "sources": ["url"]}
   ```
   **Evidence to look for**: `expected list[str], got str` in validation errors

2. **Null Handling**: Gemini returns null instead of empty list
   ```python
   {"query": "Wepoint", "findings": null, "sources": null}
   ```
   **Evidence to look for**: `NoneType` in validation errors

3. **Extra Fields**: Gemini returns unexpected fields
   ```python
   {"query": "Wepoint", "findings": [], "sources": [], "confidence": 0.8}
   ```
   **Evidence to look for**: "extra fields not permitted"

4. **Missing Required Field**: Gemini omits query field
   ```python
   {"findings": [...], "sources": [...]}  # Missing "query"
   ```
   **Evidence to look for**: "field required" for query

5. **Truncated JSON**: Response cut off due to token limits
   ```python
   {"query": "Wepoint", "findings": ["text"
   # Incomplete JSON
   ```
   **Evidence to look for**: `finish_reason='length'`, JSON parsing errors

**Analysis Process**:
1. Parse `debug_output.log` for all raw responses
2. Separate successful vs failed attempts
3. Compare JSON structure differences
4. Document exact field/format causing rejection

**Deliverable**: Root cause identified with supporting evidence

---

### Phase 4: Implement Fix (Day 3-4)

**Objective**: Fix validation issue with minimal changes.

**Solution Options** (ranked by preference):

#### Option A: Robust Schema Validation (RECOMMENDED)

**File**: `research/models.py` or `src/models.py` (lines 55-76)

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class SearchResult(BaseModel):
    """Results from a web search query."""

    query: str = Field(description="The search query that was executed")
    findings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)

    @field_validator('findings', 'sources', mode='before')
    @classmethod
    def coerce_to_list(cls, v):
        """Convert string or None to list for robustness."""
        if v is None:
            return []
        if isinstance(v, str):
            # Single string -> list with one element
            return [v] if v else []
        return v

    model_config = ConfigDict(extra="ignore")  # Ignore unexpected fields
```

**Pros**:
- Handles type mismatches gracefully
- Ignores extra fields from Gemini
- No prompt changes needed
- Minimal code change

**Cons**:
- Masks potential issues with Gemini output quality
- May hide future API changes

#### Option B: Improve Gemini Prompt (COMPLEMENTARY)

**File**: `research/agents.py` (lines 40-50)

```python
instructions="""You are a research gatherer. Execute the search and extract
key findings with sources.

CRITICAL OUTPUT FORMAT: Return data as valid JSON matching this structure:
{
  "query": "<the exact search query>",
  "findings": ["finding 1", "finding 2", ...],
  "sources": ["url1", "url2", ...]
}

REQUIREMENTS:
- "findings" MUST be an array of strings (not a single string)
- "sources" MUST be an array of strings (not a single string)
- If no findings found, return empty array: "findings": []
- Never include extra fields not in the schema
- Always include the "query" field with the exact search terms
""",
```

**Pros**:
- Addresses root cause (Gemini formatting)
- Educates model on expected format
- No code changes to data models

**Cons**:
- LLMs don't always follow format instructions
- May not solve 100% of cases
- Adds prompt complexity

#### Option C: Increase Retry Limit (WORKAROUND ONLY)

**File**: `research/agents.py` (line 36-54)

```python
Agent(
    GEMINI_MODEL,
    retries=3,  # Increase from default 1 to 3
    # ... existing config
)
```

**Pros**:
- Simple one-line change
- Gives Gemini more chances to succeed
- No schema changes needed

**Cons**:
- Increases latency (3x on failures)
- Doesn't fix root cause
- Masks underlying issue

**Recommended Approach**: Implement **Option A + Option B** together for robustness.

---

### Phase 5: Verification Testing (Day 4-5)

**Objective**: Confirm fix resolves issue without regressions.

**Create Test Suite** - `tests/test_wepoint_fix.py`:

```python
"""Regression tests for Wepoint validation fix."""

import pytest
from research.agents import get_gathering_agent

@pytest.mark.asyncio
async def test__wepoint_search__succeeds_consistently():
    """Wepoint searches should have >95% success rate after fix."""
    agent = get_gathering_agent()
    successes = 0

    for _ in range(20):
        try:
            result = await agent.run("Wepoint")
            assert result.output.query == "Wepoint"
            assert isinstance(result.output.findings, list)
            assert isinstance(result.output.sources, list)
            successes += 1
        except Exception:
            pass  # Count as failure

    success_rate = successes / 20
    assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95% target"

@pytest.mark.asyncio
async def test__onepoint_search__still_works():
    """Ensure fix doesn't break previously working queries."""
    agent = get_gathering_agent()
    result = await agent.run("onepoint")

    assert result.output.query == "onepoint"
    assert isinstance(result.output.findings, list)
    assert isinstance(result.output.sources, list)

@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["Waypoint", "Endpoint", "Checkpoint", "Weepoint"])
async def test__similar_queries__work(query):
    """Test edge cases similar to Wepoint."""
    agent = get_gathering_agent()
    result = await agent.run(query)
    assert result.output.query == query
```

**Run Verification**:
```bash
# Verify fix works
python research/debug_wepoint.py 2>&1 | grep "success_rate"

# Run test suite
pytest tests/test_wepoint_fix.py -v

# Check no regressions
pytest tests/ -k "gathering" -v
```

**Success Criteria**:
- ✅ Wepoint success rate >95% (was 25%)
- ✅ onepoint success rate remains 100%
- ✅ All existing tests pass
- ✅ Edge case queries >90% success rate

---

### Phase 6: Document Bug Report (Day 5)

**Objective**: Create comprehensive bug report for future reference.

**Create** - `docs/bug-reports/gemini-validation-failures.md`:

```markdown
# Bug Report: Gemini Output Validation Failures (Wepoint Query)

## Executive Summary

**Issue**: Gemini 2.5 Flash gathering agent failed 75% of the time on queries containing "Wepoint"
**Root Cause**: [IDENTIFIED IN PHASE 3]
**Solution**: [IMPLEMENTED IN PHASE 4]
**Impact**: Reduced failure rate from 75% to <5%

## Technical Details

### Error
```
UnexpectedModelBehavior: Exceeded maximum retries (1) for output validation
Origin: pydantic_ai/_agent_graph.py:118
```

### Reproduction Steps
1. Start FastAPI server: `just serve`
2. Send POST to `/research` with body: `{"query": "What is Wepoint?"}`
3. Observe 75% failure rate in gathering phase

### Raw Responses

**Failed Response Example**:
```json
[PASTE ACTUAL FAILED RESPONSE FROM LOGS]
```

**Successful Response Example**:
```json
[PASTE ACTUAL SUCCESSFUL RESPONSE FROM LOGS]
```

### Validation Error Details
```
[PASTE PYDANTIC ValidationError FROM LOGS]
```

## Root Cause Analysis

[DETAILED EXPLANATION BASED ON PHASE 3 FINDINGS]

### Why "Wepoint" Failed But "onepoint" Succeeded

[SPECIFIC EXPLANATION OF QUERY-DEPENDENT BEHAVIOR]

### Hypotheses Tested

| Hypothesis | Result | Evidence |
|------------|--------|----------|
| Type mismatch (string vs list) | [✓/✗] | [Evidence from logs] |
| Null handling issue | [✓/✗] | [Evidence from logs] |
| Extra fields rejection | [✓/✗] | [Evidence from logs] |
| Missing required field | [✓/✗] | [Evidence from logs] |
| Truncated JSON | [✓/✗] | [Evidence from logs] |

## Solution Implemented

### Code Changes

**File**: `research/models.py` or `src/models.py`
```python
[PASTE ACTUAL CODE CHANGES]
```

**File**: `research/agents.py` (if prompt improved)
```python
[PASTE ACTUAL PROMPT CHANGES]
```

### Trade-offs

**Pros**:
- [List benefits]

**Cons**:
- [List drawbacks]

## Testing Evidence

### Before Fix
```
Wepoint:  5/20 (25% success)
onepoint: 20/20 (100% success)
```

### After Fix
```
Wepoint:  19/20 (95% success)
onepoint: 20/20 (100% success)
```

### Performance Impact
- Latency: +0ms (no change)
- Token usage: +0% (no change)
- Quality: Maintained

## Prevention & Monitoring

### Recommended Actions
1. Add integration tests for SearchResult validation edge cases
2. Monitor gathering agent failure rate in production (alert if >10%)
3. Consider adding output schema validation in CI/CD
4. Log all Pydantic ValidationErrors with full context

### Future Improvements
1. Implement response preprocessing layer for LLM outputs
2. Add retry with exponential backoff for validation failures
3. Create library of robust Pydantic validators for LLM responses
4. Switch to Pydantic strict mode in development for early detection

## Related Issues
- PydanticAI: [Link if issue filed]
- Gemini API: [Link if relevant]
```

---

## Critical Files

### Implementation Files

1. **`research/models.py` or `src/models.py`** (lines 55-76)
   - Contains SearchResult schema requiring validation fixes
   - Add field_validator for type coercion
   - Configure model to ignore extra fields

2. **`research/agents.py`** (lines 36-54)
   - Gathering agent definition and prompt
   - Improve instructions for Gemini output format
   - Optionally increase retry count

3. **`research/run_research.py`** (gathering phase exception handling)
   - Add detailed logging for validation failures
   - Capture raw responses before they're lost

### Debug & Testing Files

4. **`research/debug_patch.py`** (NEW)
   - Monkey-patch for capturing validation errors
   - Temporary instrumentation for investigation

5. **`research/debug_wepoint.py`** (NEW)
   - Reproduction script for statistical validation
   - Run 20 tests per query to confirm fix

6. **`tests/test_wepoint_fix.py`** (NEW)
   - Regression test suite
   - Verify >95% success rate post-fix

### Reference Files (Read-Only)

7. **`/Users/lkronecker/ai-enhanced-engineer/projects/Wepoint/wep-deep-research/.venv/lib/python3.12/site-packages/pydantic_ai/_agent_graph.py`**
   - PydanticAI retry mechanism source
   - Understanding error origin and retry logic

8. **`/Users/lkronecker/ai-enhanced-engineer/projects/Wepoint/wep-deep-research/.venv/lib/python3.12/site-packages/pydantic_ai/_output.py`**
   - Pydantic validation logic
   - Understanding how ToolRetryError is raised

---

## Verification Checklist

### Investigation Complete
- [ ] Debug instrumentation added
- [ ] Reproduction script created and run
- [ ] 40+ test runs logged (20 Wepoint, 20 onepoint)
- [ ] Root cause identified with evidence
- [ ] Raw failed responses captured

### Fix Implemented
- [ ] Code changes made to SearchResult model
- [ ] Prompt improvements applied (if needed)
- [ ] Unit tests added
- [ ] Regression tests pass

### Verification Passed
- [ ] Wepoint success rate >95%
- [ ] onepoint success rate remains 100%
- [ ] Edge case queries tested
- [ ] No performance degradation
- [ ] Existing tests pass

### Documentation Complete
- [ ] Bug report created with evidence
- [ ] Root cause documented
- [ ] Solution documented with trade-offs
- [ ] Prevention recommendations provided

---

## Timeline

| Phase | Estimated Time |
|-------|----------------|
| 1. Instrumentation | 2-4 hours |
| 2. Reproduction | 1-2 hours |
| 3. Root Cause Analysis | 4-8 hours |
| 4. Implementation | 2-4 hours |
| 5. Verification | 2-4 hours |
| 6. Documentation | 2-3 hours |
| **Total** | **13-25 hours (2-3 days)** |

---

## Success Criteria

1. ✅ Root cause identified with concrete evidence (logs, responses, errors)
2. ✅ Fix reduces Wepoint failure rate from 75% to <5%
3. ✅ No regressions on onepoint or other queries
4. ✅ Comprehensive bug report with reproduction steps
5. ✅ Test coverage for edge cases added
6. ✅ Prevention recommendations documented
