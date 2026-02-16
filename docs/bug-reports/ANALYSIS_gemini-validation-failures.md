# Root Cause Analysis: Gemini Validation Failures

**Date**: 2026-02-12
**Status**: Diagnostic Complete - Awaiting User Decision
**Investigation**: Phase 3 Complete

---

## Executive Summary

Gemini 2.5 Flash returns **malformed JSON responses** that fail Pydantic validation, causing the gathering agent to retry. The retry mechanism succeeds 97.5% of the time, but 2.5% of requests exceed the maximum retry limit (1 retry) and fail completely.

**Key Finding**: This is NOT a "Wepoint"-specific issue. The problem affects all queries equally (~35% first-attempt error rate), but the retry mechanism masks most failures.

---

## Statistical Analysis

### Reproduction Test Results (40 runs total)

| Query | Runs | Final Success | First-Attempt Errors | Retry Success Rate | Complete Failures |
|-------|------|---------------|----------------------|-------------------|-------------------|
| **Wepoint** | 20 | 20/20 (100%) | 4/20 (20%) | 100% | 0 |
| **onepoint** | 20 | 19/20 (95%) | 10/20 (50%) | 90% | 1 |
| **Combined** | 40 | 39/40 (97.5%) | 14/40 (35%) | 93% | 1 |

### Key Metrics

- **First-Attempt Error Rate**: 35% (14 validation errors across 40 runs)
- **Retry Success Rate**: 93% (13/14 errors resolved by retry)
- **Final Failure Rate**: 2.5% (1/40 exceeded max retries)
- **Max Retries Configured**: 1 (meaning 2 total attempts)

---

## Root Cause: Invalid JSON from Gemini

### Error Pattern

All validation errors show the same root cause:

```
error_type: ToolRetryError
error_details: 1 validation error
  __root__
    Invalid JSON: exp...  [or]  Invalid JSON: tra...

Pydantic validation:
  {'type': 'json_invalid', 'loc': (), 'msg': 'In...'}
```

**Hypothesis**: Gemini returns JSON with:
- Invalid escape sequences (e.g., `\n` in strings without proper escaping)
- Trailing commas
- Incomplete JSON (truncated responses)
- Markdown wrappers (` ```json ... ``` `)

**Evidence**: Error messages show "Invalid JSON: exp..." (possibly "expected") and "Invalid JSON: tra..." (possibly "trailing").

---

## Why "Wepoint" Appeared to Fail More

### Original Observation
You observed a **75% failure rate** for "Wepoint" queries during full research workflows.

### Reproduction Test Results
Standalone queries show **0% complete failure** for Wepoint and **5% complete failure** for onepoint.

### Likely Explanation

The higher failure rate in production may be due to:

1. **Concurrent Execution**: Full research workflow runs 4+ searches in parallel using `asyncio.TaskGroup`. Concurrent API calls may hit rate limits or return lower-quality responses.

2. **Context Length**: Full research queries include more context (research plan, previous findings), potentially causing longer/more complex JSON responses that are more likely to be malformed.

3. **Query Complexity**: "What is Wepoint?" in production includes multi-step research context, while standalone "Wepoint" query is simpler.

4. **Retry Limit**: Production may have had a stricter retry configuration at the time of observation.

---

## Validation Failure Example

### The One Complete Failure (onepoint run 10)

```
15:41:41 [ERROR] validation_error_before_retry
  error_type=ToolRetryError
  error_details=1 validation error
    Invalid JSON: exp...
  retry_count=1  # Second attempt also failed
  raw_response=ModelResponse(parts=[BuiltinToolCallPart(tool_n...])

15:41:41 [ERROR] pydantic_validation_details
  errors=[{'type': 'json_invalid', 'loc': (), 'msg': 'In...'}]
  retry_count=1

15:41:41 [ERROR] test_failure
  run=10, query=onepoint
  error=Exceeded maximum retries (1) for output validation
  error_type=UnexpectedModelBehavior
```

**Analysis**:
- First attempt failed with JSON validation error
- Retry (second attempt) also failed with JSON validation error
- System raised `UnexpectedModelBehavior` exception
- Research workflow would continue with remaining successful searches (graceful degradation)

---

## Impact Assessment

### Current System Behavior

✅ **What Works**:
- Retry mechanism recovers from 93% of JSON validation errors
- Graceful degradation allows workflow to continue with ≥1 successful search
- Overall success rate of 97.5% in standalone tests

❌ **What Fails**:
- 2.5% of requests completely fail after exhausting retries
- 35% overhead from retry attempts (increased latency and API costs)
- Poor quality when multiple searches fail in parallel workflows

### Production Impact

Assuming 4 searches per research query:
- **Probability all 4 succeed**: (0.975)^4 ≈ 90.4%
- **Probability ≥1 fails**: 1 - 0.904 ≈ 9.6%
- **Probability ≥2 fail**: ~2-3% (estimated)

With graceful degradation, reports are generated even with 1/4 successful searches, but quality suffers.

---

## Decision Matrix

### Option A: Fix Gemini Output

**Approach**: Improve prompt, add response sanitization, increase retry limit.

**Pros**:
- Faster responses (Gemini 2.5 Flash is 2-3x faster than Claude)
- Lower cost per query (~5x cheaper than Claude)
- Maintains current multi-model strategy

**Cons**:
- May not fully resolve issue (Gemini's JSON formatting is unpredictable)
- Requires ongoing maintenance if Gemini behavior changes
- Still has inherent 2-5% failure rate

**Estimated Effort**: Medium (2-3 days)

**Changes Required**:
1. Strengthen prompt with explicit JSON formatting rules
2. Add pre-validation sanitization (strip markdown, fix trailing commas)
3. Increase `max_result_retries` from 1 → 3 (4 total attempts)
4. Add token/length monitoring to detect truncation
5. Implement exponential backoff for retries

---

### Option B: Switch Gathering Agent to Claude

**Approach**: Replace Gemini 2.5 Flash with Claude Sonnet 4.5 for gathering phase.

**Pros**:
- More reliable JSON output (Claude excels at structured data)
- Better instruction following (less prompt engineering needed)
- Consistent with existing planning/synthesis agents (Claude)

**Cons**:
- Slower responses (Claude is ~2-3x slower than Gemini Flash)
- Higher cost (~3-5x more expensive per query)
- Loses speed advantage of multi-model strategy

**Estimated Effort**: Low (1 day)

**Changes Required**:
1. Update `research/agents.py` to use Claude for gathering agent
2. Adjust prompt if needed (Claude may need different instructions)
3. Test and validate with same reproduction script
4. Update cost projections and documentation

---

### Option C: Hybrid Approach (Fallback)

**Approach**: Try Gemini first, fall back to Claude on validation failure.

**Pros**:
- Best of both worlds (speed + reliability)
- Automatically adapts to Gemini quality
- Maintains cost efficiency for successful queries

**Cons**:
- Most complex to implement
- Adds fallback latency on errors
- Requires careful error handling and logging

**Estimated Effort**: High (3-5 days)

**Changes Required**:
1. Implement retry logic with model fallback
2. Track success rates per model (observability)
3. Add circuit breaker if Gemini failure rate exceeds threshold
4. Cost tracking per model used
5. Comprehensive error handling and monitoring

---

## Recommendations

### Short-Term (Next Sprint)

**Recommended**: **Option B - Switch to Claude** for gathering agent.

**Rationale**:
- Lowest implementation risk (1 day vs 3-5 days for hybrid)
- Immediate resolution of validation failures
- Simplifies system (one model for all agents)
- Claude's reliability justifies the cost/speed tradeoff for research quality

### Long-Term (Future Optimization)

After stabilizing with Claude, consider:
1. **Option A** (Gemini improvements) if cost becomes a constraint
2. **Option C** (Hybrid fallback) if Gemini quality improves significantly
3. Monitor Gemini model updates for improved JSON formatting

---

## Next Steps

### User Decision Required

Please choose one of the following paths:

1. **Option A**: Fix Gemini with prompt improvements + sanitization + increased retries
2. **Option B**: Switch gathering agent to Claude Sonnet 4.5 (recommended)
3. **Option C**: Implement hybrid approach with Gemini → Claude fallback

Once you decide, I will:
- Create implementation plan for chosen option
- Update agents and validation logic
- Re-run reproduction tests to verify fix
- Update documentation and cost projections

---

## Appendix: Detailed Test Logs

**Full test output**: `debug_output.log` (215 lines)
**Reproduction script**: `research/debug_wepoint.py`
**Debug instrumentation**: `research/debug_patch.py`

### Sample Validation Errors

```
# Wepoint Run 4 (retry succeeded)
15:34:25 [ERROR] validation_error_before_retry
  error_type=ToolRetryError
  error_details=1 validation error __root__ Invalid JSON: exp...
  retry_count=0

# Wepoint Run 11 (retry succeeded)
15:35:52 [ERROR] validation_error_before_retry
  error_type=ToolRetryError
  error_details=1 validation error __root__ Invalid JSON: exp...
  retry_count=0

# onepoint Run 10 (retry failed - complete failure)
15:41:41 [ERROR] validation_error_before_retry
  error_type=ToolRetryError
  error_details=1 validation error __root__ Invalid JSON: exp...
  retry_count=1  # Failed even after retry
```

### Error Distribution

- **"Invalid JSON: exp..."**: 12/14 errors (86%)
- **"Invalid JSON: tra..."**: 2/14 errors (14%)
- **"Please return text..."**: 0 errors (this was seen in server logs but not reproduction)

---

**Investigation Complete**. Awaiting user decision on implementation path.
