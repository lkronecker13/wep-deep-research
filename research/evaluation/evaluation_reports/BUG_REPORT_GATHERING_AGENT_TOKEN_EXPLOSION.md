# Bug Report: Gathering Agent Token Explosion via PydanticAI Retry Loop

**Date:** 2026-02-12
**Severity:** High (Cost & Latency Impact)
**Component:** `research/agents.py` - Gathering Agent (Gemini 2.5 Flash)
**Discovered via:** Arize Phoenix tracing during evaluation run

---

## Summary

The second gathering agent (`gathering_agent_1`) experienced a token explosion during retry loops, consuming **378,900 total tokens** (151,265 prompt + 227,635 completion), costing **$0.19 for a single agent call**, and taking **3 minutes 52 seconds** to complete. The bug is caused by a chain of three interacting issues:

1. Gemini 2.5 Flash returns plain text instead of JSON (no native JSON constraint enforced)
2. A corrupted VertexAI Search redirect URL containing ~77,000 tokens of repeating characters
3. PydanticAI's retry mechanism echoing the full conversation history (including the massive URL) back to the model

---

## Environment

- **PydanticAI version:** 1.44.0
- **Model:** `google-gla:gemini-2.5-flash`
- **Agent config:** `output_type=SearchResult`, `builtin_tools=[WebSearchTool()]`, `retries=3`
- **Evaluation file:** `research/outputs/evaluations/eval_eval_1q_20260212_154253.json`

---

## Reproduction Steps

1. Run a research query via `just eval-query "what is cloud computing?"`
2. The planning agent creates 5 search steps
3. 5 gathering agents run in parallel, each executing a web search via Gemini
4. Observe in Phoenix tracing that `gathering_agent_1` (search: "cloud computing service models IaaS PaaS SaaS explained") takes significantly longer than others

---

## Root Cause Analysis

### Chain of Failure

```
[1] Gemini returns plain text instead of JSON
         |
         v
[2] PydanticAI sends validation error + FULL previous response back to model
         |
         v
[3] Gemini retries, calls google_search again, gets corrupted 77K-char URL
         |
         v
[4] Gemini responds with markdown-fenced JSON (truncated by output token limit?)
         |
         v
[5] PydanticAI validation fails again, sends 149K tokens back for retry #2
         |
         v
[6] Gemini finally returns valid JSON (using conversation knowledge, no new search)
         |
         v
[7] Total: 3 LLM calls, ~$0.19, 3m52s for ONE gathering agent
```

### Root Cause #1: No Native JSON Constraint on Gemini 2.5 Flash with Builtin Tools

**This is the fundamental trigger.** When the gathering agent combines `output_type=SearchResult` with `builtin_tools=[WebSearchTool()]`, PydanticAI enters a fallback code path:

**File:** `.venv/Lib/site-packages/pydantic_ai/models/google.py` (lines 261-267)
```python
supports_native_output_with_builtin_tools = GoogleModelProfile.from_profile(
    self.profile
).google_supports_native_output_with_builtin_tools
if model_request_parameters.builtin_tools and model_request_parameters.output_tools:
    if model_request_parameters.output_mode == 'auto':
        output_mode = 'native' if supports_native_output_with_builtin_tools else 'prompted'
```

**File:** `.venv/Lib/site-packages/pydantic_ai/profiles/google.py` (lines 24-31)
```python
is_3_or_newer = 'gemini-3' in model_name
# ...
google_supports_native_output_with_builtin_tools=is_3_or_newer,  # False for gemini-2.5-flash
```

Since `gemini-2.5-flash` is NOT Gemini 3+, `supports_native_output_with_builtin_tools = False`, so `output_mode` becomes `'prompted'`.

Then at lines 503-517:
```python
response_mime_type = None
if model_request_parameters.output_mode == 'native':
    response_mime_type = 'application/json'  # NOT reached
elif model_request_parameters.output_mode == 'prompted' and not tools:
    response_mime_type = 'application/json'  # NOT reached (tools exist!)
```

**Result:** `response_mime_type` stays `None`. The Gemini API config sent is:
```json
"response_mime_type": null,
"response_json_schema": null
```

PydanticAI only adds a text instruction to the system prompt:
```
Always respond with a JSON object that's compatible with this schema: {...}
Don't include any text or Markdown fencing before or after.
```

But Gemini **ignores this prompt-based instruction** on the first call and returns a full markdown text explanation instead of JSON.

### Root Cause #2: Corrupted VertexAI Search Redirect URL

When Gemini's `google_search` tool returns results, the source URLs are VertexAI Search redirect URLs. One of these URLs contained a massively repeating pattern:

```
https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQE2rfGg...
q3r4o5q6w0r2m3v5s0q3r4o5q6w0r2m3v5s0q3r4o5q6w0r2m3v5s0... (repeats for ~77,000 tokens)
```

This appears to be a bug or corruption in the VertexAI Search grounding API. A normal redirect URL is ~200-400 characters; this one was orders of magnitude larger.

### Root Cause #3: PydanticAI Retry Echoes Full Conversation History

PydanticAI's retry mechanism works as follows:

**File:** `.venv/Lib/site-packages/pydantic_ai/_agent_graph.py` (lines 728-735)
```python
except ToolRetryError as e:
    ctx.state.increment_retries(ctx.deps.max_result_retries, ...)
    self._next_node = ModelRequestNode[DepsT, NodeRunEndT](
        _messages.ModelRequest(parts=[e.tool_retry], instructions=instructions)
    )
```

The model's **full previous response** (including all text and grounding metadata with the massive URL) is already in the conversation history. The retry adds a validation error message. On the next call, the **entire conversation** is sent to the model:

| Retry | Approx. Input Tokens | Content |
|-------|---------------------|---------|
| Call 1 | ~500 | System prompt + search query |
| Call 2 | ~77,000 | Call 1 input + plain text response + validation error |
| Call 3 | ~149,000 | Call 2 input + fenced JSON with 77K URL + validation error |

The gathering agent has `retries=3`, allowing up to 3 retries. Each retry compounds the token count.

---

## Verified Token Usage (from Phoenix Span Attributes)

The following data was extracted directly from the `gathering_agent_1_execution` span in Arize Phoenix:

```json
{
  "llm.token_count.total": 378900,
  "llm.token_count.prompt": 151265,
  "llm.token_count.completion": 227635,
  "agent.name": "gathering_agent_1",
  "agent.success": true,
  "agent.completed": true,
  "agent.prompt_length": 55
}
```

**Key observation:** Completion tokens (227,635) exceed prompt tokens (151,265). This is because Gemini **generated** the massive ~77K-token corrupted URL as part of its output on Call 2. The URL was not just echoed -- Gemini produced it as completion tokens, which cost more per token than input.

---

## Observed Behavior (from Phoenix Traces)

### Call 1: Plain Text Response (FAIL)

**LLM Input:** Original search query (~500 tokens)
**LLM Output:** Full markdown explanation of IaaS/PaaS/SaaS (~2,000 tokens, plain text, NOT JSON)
**Validation Error:** `"type": "json_invalid", "msg": "Invalid JSON: expected value at line 1 column 1"`

### Call 2: Markdown-Fenced JSON with Massive URL (FAIL)

**LLM Input:** ~77,000 tokens (includes Call 1's full response + validation error)
**LLM Output:** ~220,000 tokens -- JSON wrapped in ` ```json ``` ` fencing with sources including a ~77K-token corrupted VertexAI redirect URL
**Validation Error:** `"type": "json_invalid"` (likely due to output truncation at Gemini's token limit, resulting in incomplete JSON that `strip_markdown_fences` cannot parse)

### Call 3: Valid JSON with Real URLs (SUCCESS)

**LLM Input:** ~74,000 tokens (includes Call 1 + Call 2 + both errors)
**LLM Output:** ~5,000 tokens -- Valid JSON with **real verifiable URLs** (aws.amazon.com, ibm.com, azure.microsoft.com, etc.)

**Notable:** On the final retry, Gemini did NOT call `google_search` again. It synthesized the answer from the conversation history, producing real URLs instead of VertexAI redirect URLs. This is actually a better result, but at enormous cost.

---

## Impact

| Metric | Normal Agent | Bugged Agent | Delta |
|--------|-------------|--------------|-------|
| LLM Calls | 1 | 3 | +200% |
| Total Tokens | ~1,500 | 378,900 | +25,160% |
| Prompt Tokens | ~500 | 151,265 | +30,153% |
| Completion Tokens | ~1,000 | 227,635 | +22,664% |
| Cost | ~$0.001 | ~$0.19 | +19,000% |
| Latency | ~15s | 3m 52s | +1,447% |

**Completion tokens are the dominant cost factor.** Gemini 2.5 Flash charges more for output tokens than input tokens. The 227K completion tokens (driven by the massive generated URL on Call 2) account for the majority of the $0.19 cost.

**At scale:** If this affects even 20% of gathering agent calls during a full evaluation (35 questions x 5 agents = 175 calls), total eval cost could increase by **$6-7 per run** unnecessarily.

---

## Proposed Mitigations

### M1: Force `output_type` to Use `PromptedOutput` or `NativeOutput` (Quick Fix)

Override the default `output_mode` to bypass the auto-selection that leads to no JSON constraint:

```python
from pydantic_ai.output import PromptedOutput

get_gathering_agent() -> Agent[None, SearchResult]:
    return Agent(
        GEMINI_MODEL,
        instructions="...",
        builtin_tools=[WebSearchTool()],
        output_type=PromptedOutput(SearchResult),  # Force prompted mode explicitly
        name="gathering_agent",
        retries=3,
    )
```

**Note:** This alone may not set `response_mime_type` due to the `and not tools:` condition in PydanticAI. Needs testing.

### M2: Add a History Processor to Truncate Conversation on Retries (Recommended)

PydanticAI supports `history_processors` that run before every model request:

```python
from pydantic_ai.messages import ModelMessage, ModelRequest

def truncate_retry_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Prevent token explosion by limiting conversation history during retries."""
    if len(messages) <= 3:
        return messages
    # Keep first message (system) and last 2 (most recent exchange + retry prompt)
    return [messages[0]] + messages[-2:]

get_gathering_agent() -> Agent[None, SearchResult]:
    return Agent(
        GEMINI_MODEL,
        # ...
        history_processors=[truncate_retry_history],
    )
```

### M3: Add Source URL Validation to `SearchResult` Model

Prevent absurdly long URLs from entering the system:

```python
from pydantic import field_validator

class SearchResult(BaseModel):
    query: str
    findings: list[str]
    sources: list[str]

    @field_validator("sources", mode="before")
    @classmethod
    def truncate_long_urls(cls, v: list[str]) -> list[str]:
        MAX_URL_LENGTH = 2048  # RFC 2616 recommended max
        return [url[:MAX_URL_LENGTH] for url in v]
```

### M4: Set `max_tokens` on Model Settings to Limit Response Size

Prevent Gemini from generating responses that include massive URLs:

```python
from pydantic_ai.settings import ModelSettings

get_gathering_agent() -> Agent[None, SearchResult]:
    return Agent(
        GEMINI_MODEL,
        model_settings=ModelSettings(max_tokens=8000),
        # ...
    )
```

### M5: Reduce `retries` from 3 to 1 (Quick Win)

Fewer retries = less token explosion. The default PydanticAI retry count is 1:

```python
retries=1,  # Instead of retries=3
```

### M6: Upstream - Report to PydanticAI (Long-term)

The interaction between `WebSearchTool()` + `output_type` on Gemini 2.5 Flash results in **no JSON constraint at all** (`response_mime_type=null`). This is arguably a PydanticAI bug: when falling back to 'prompted' mode with tools, it should still attempt to set `response_mime_type` when possible, or at minimum document this limitation prominently.

**GitHub issue to file:** `pydantic/pydantic-ai` - "Gemini 2.5 Flash with WebSearchTool + output_type has no JSON response constraint"

### M7: Upstream - Report Corrupted URL to Google (Long-term)

The ~77K character VertexAI Search redirect URL with repeating `q3r4o5q6w0r2m3v5s0` pattern is clearly a bug in the Gemini grounding API. This should be reported to Google.

---

## Recommended Fix Priority

| Priority | Mitigation | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | M4: max_tokens setting | Trivial | Caps completion tokens (the dominant cost driver) |
| P0 | M2: History processor | Low | Prevents prompt token explosion on retries |
| P0 | M5: Reduce retries to 1 | Trivial | Limits blast radius |
| P1 | M3: URL validation | Low | Prevents corrupted URLs from propagating |
| P2 | M1: Explicit output mode | Medium | Needs testing |
| P2 | M6: PydanticAI upstream issue | Low | Long-term fix |
| P3 | M7: Google grounding API report | Low | External dependency |

---

## Related Observations

### VertexAI Redirect URLs (Separate Issue)

All gathering agents return `vertexaisearch.cloud.google.com/grounding-api-redirect/` URLs as sources instead of real URLs. This is **expected behavior** from Gemini's `google_search` tool - these are temporary redirect URLs that resolve to the actual sources. However:

- They are opaque and unverifiable by our evaluation judges
- The evaluation system's source quality checks flag them as concerning (see `custom_query_gather_2` and `custom_query_gather_4` which FAILED evaluation specifically due to unverifiable redirect URLs)
- The bugged agent's final retry paradoxically produced **better results** with real URLs

This suggests a separate improvement: resolving or replacing VertexAI redirect URLs with actual source URLs in post-processing.

---

## Edge Cases Not Covered

| Scenario | Risk | Relevant Mitigation |
|----------|------|---------------------|
| All 5 gathering agents hit this bug | ~$0.95 total cost | M2 + M4 + M5 |
| `retries=5` instead of 3 | ~600K+ tokens | M5 (reduce retries) |
| Corrupted URL >1MB | Hard failure at input limit | M3 (URL validation) |
| Concurrent evaluation runs (10x) | $19+ wasted cost | All mitigations |

---

## Next Steps

The evaluation suite should be updated to detect and prevent this class of bug automatically. This includes populating token/cost metrics in evaluation results, adding anomaly detection thresholds, correlating evaluation failures with Phoenix trace IDs, and adding test coverage for retry behavior and token explosion scenarios.
