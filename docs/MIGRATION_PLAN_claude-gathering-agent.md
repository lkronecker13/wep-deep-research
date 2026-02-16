# Migration Plan: Gathering Agent to Claude Sonnet 4.5

**Status**: Planned (not implemented)
**Target Date**: Q2 2026 (after Gemini fixes are validated)
**Rationale**: Long-term reliability and consistency

## Background

After fixing Gemini validation issues in Phase 1, we plan to migrate the gathering agent to Claude Sonnet 4.5 for improved reliability and consistency with other agents (planning, synthesis, verification all use Claude).

The current multi-model strategy uses:
- **Gemini 2.5 Flash** for gathering (speed/cost optimization)
- **Claude Sonnet 4.5** for planning, synthesis, verification (reliability/quality)

This migration would unify all agents on Claude Sonnet 4.5.

## Benefits

- **Reliability**: Claude excels at structured JSON output (fewer validation errors)
- **Consistency**: All 4 agents use same model (simpler debugging, unified behavior)
- **Instruction Following**: Claude requires less prompt engineering for complex tasks
- **Maintainability**: Single model reduces cognitive overhead
- **Quality**: Better understanding of research context and nuance

## Tradeoffs

- **Speed**: Claude is ~2-3x slower than Gemini Flash (~15s vs ~6s per search)
- **Cost**: Claude is ~3-5x more expensive per request
- **Total Latency**: With 4 parallel searches, expect +10-20s per research query
- **Reduced Cost Optimization**: Lose cost advantage of using cheaper model for high-volume gathering

## Current State (Phase 1 with Gemini)

| Metric | Value |
|--------|-------|
| Model | Gemini 2.5 Flash |
| First-attempt error rate | ~35% |
| Retry limit | 3 retries (4 total attempts) |
| Complete failure rate | <0.1% |
| Average search latency | ~6 seconds |
| Cost per search | Low (Gemini pricing) |

## Target State (Phase 2 with Claude)

| Metric | Value |
|--------|-------|
| Model | Claude Sonnet 4.5 |
| First-attempt error rate | <1% (expected) |
| Retry limit | 1 retry (2 total attempts) |
| Complete failure rate | <0.01% (expected) |
| Average search latency | ~15 seconds |
| Cost per search | 3-5x higher |

## Implementation Steps

### 1. Update Agent Configuration

**File**: `research/agents.py`

```python
@lru_cache(maxsize=1)
def get_gathering_agent() -> Agent[None, SearchResult]:
    """Get or create the gathering agent (cached)."""
    return Agent(
        CLAUDE_MODEL,  # Changed from GEMINI_MODEL
        instructions="""You are a research gatherer. Execute the search and extract
        key findings with sources.

        Your task:
        - Use the web search tool to find relevant information
        - Extract key facts, statistics, and insights
        - Identify credible sources
        - Focus on accuracy and relevance
        - Avoid speculation or unsupported claims

        Return structured findings with source URLs.""",
        builtin_tools=[WebSearchTool()],
        max_result_retries=1,  # Reduced from 3 (Claude rarely needs retries)
        output_type=SearchResult,
        name="gathering_agent",
    )
```

**Changes**:
- Model: `GEMINI_MODEL` → `CLAUDE_MODEL`
- Retry limit: `max_result_retries=3` → `max_result_retries=1`
- Instructions: Remove explicit JSON formatting rules (Claude doesn't need them)

### 2. Test Thoroughly

**Validation Tests**:
1. Run reproduction script with Claude configuration
2. Execute 40+ research queries to measure:
   - Validation error rate (target: <1%)
   - Average latency per search (measure impact)
   - Total workflow duration (acceptable threshold: <30s added)
   - Search quality (findings count, source diversity)

**Comparison Metrics**:
| Metric | Gemini (Phase 1) | Claude (Phase 2) | Delta |
|--------|------------------|------------------|-------|
| Validation errors | ~35% first-attempt | <1% (expected) | -34% |
| Retry success rate | ~93% | >99% (expected) | +6% |
| Complete failures | <0.1% | <0.01% (expected) | -0.09% |
| Avg search latency | ~6s | ~15s (expected) | +9s |
| Total workflow time | ~30s | ~40-50s (expected) | +10-20s |

### 3. Update Documentation

**Files to update**:
- `README.md` - Update multi-model strategy description
- `docs/ARCHITECTURE_DECISIONS.md` - Document model selection rationale
- `docs/PHASE1_IMPLEMENTATION.md` - Add Phase 2 migration notes

**Cost projections**:
- Calculate monthly cost increase based on expected query volume
- Update budget documentation with new cost estimates

### 4. Deploy with Monitoring

**Pre-deployment checklist**:
- [ ] Staging environment tests pass
- [ ] Load testing confirms latency acceptable
- [ ] Cost projections approved
- [ ] Rollback plan tested

**Post-deployment monitoring**:
- Track validation error rate (alert if >1%)
- Monitor P95/P99 latency (alert if >60s)
- Watch cost metrics (alert if >120% projected)
- Compare quality metrics (findings/sources count)

## Success Criteria

- ✅ Validation error rate <1% (from ~35%)
- ✅ Complete failure rate <0.01% (from <0.1%)
- ✅ Total workflow latency increase <30s (acceptable threshold)
- ✅ Cost increase within approved budget
- ✅ No regression in search quality (findings/sources comparable or better)
- ✅ 7-day production stability (no rollback needed)

## Risk Mitigation

### Risk 1: Unacceptable Latency
**Impact**: User experience degraded by slow research queries
**Mitigation**:
- Measure latency in staging before production
- Set hard threshold (<30s added latency)
- Optimize prompt if needed to reduce token count
- Consider hybrid approach (Gemini for simple queries, Claude for complex)

### Risk 2: Cost Overruns
**Impact**: Budget exceeded, unsustainable pricing
**Mitigation**:
- Calculate projected monthly costs before deployment
- Set up cost alerts in GCP
- Monitor daily spend for first week
- Consider usage-based tier limits

### Risk 3: Quality Regression
**Impact**: Claude produces worse search results than Gemini
**Mitigation**:
- A/B test 50 queries (Gemini vs Claude)
- Compare findings count, source diversity, relevance
- User acceptance testing with sample queries
- Rollback if quality metrics degrade >10%

## Rollback Plan

If Claude migration causes issues:

### Immediate Rollback (< 5 minutes)
```bash
# Revert agents.py to Gemini configuration
git revert <commit-hash>
git push origin main

# Redeploy previous version
just deploy
```

### Conditions for Rollback
- Validation error rate >5% (expected <1%)
- Complete failure rate >1% (expected <0.01%)
- P95 latency >90s (threshold 60s)
- Cost >150% of projections
- User complaints about quality/speed

### Post-Rollback Analysis
1. Preserve Claude test results for analysis
2. Re-enable diagnostic logging
3. Run A/B comparison tests
4. Document specific failure modes
5. Decide on hybrid approach (Option C: Gemini → Claude fallback)

## Alternative Approaches

### Option A: Full Claude Migration (This Plan)
- **Pros**: Maximum reliability, consistency
- **Cons**: Highest cost/latency impact

### Option B: Keep Gemini Forever
- **Pros**: Maintains speed/cost advantages
- **Cons**: 35% first-attempt errors, ongoing maintenance

### Option C: Hybrid Fallback (Gemini → Claude)
- **Pros**: Best of both worlds (speed + reliability fallback)
- **Cons**: Complex implementation, two models to maintain
- **Implementation**: Catch Gemini validation errors, retry with Claude

### Recommendation
Proceed with **Option A** (Full Claude Migration) if Phase 1 validation shows:
- Gemini still has >30% first-attempt error rate
- Production failures >0.1% despite 3 retries
- Quality concerns (truncated results, poor sources)

Consider **Option C** (Hybrid) if:
- Latency/cost impact of Claude unacceptable
- Gemini quality is acceptable but reliability gaps remain

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Pre-implementation** | 2 weeks | Gather Phase 1 production data, finalize cost projections |
| **Development** | 1 week | Update agents.py, write tests, update docs |
| **Staging validation** | 1 week | Run 100+ test queries, measure latency/cost/quality |
| **Production rollout** | 1 week | Gradual rollout with monitoring |
| **Post-deployment monitoring** | 2 weeks | Track success criteria, adjust if needed |

**Total**: ~7 weeks from start to stable production

## Decision Point

**Execute Phase 2 migration if:**
- Phase 1 (Gemini with fixes) shows continued reliability issues
- Production data shows >0.1% complete failures
- Quality concerns outweigh cost/latency benefits of Gemini
- Team capacity available for migration work

**Defer Phase 2 migration if:**
- Phase 1 successfully reduces failures to <0.1%
- Gemini quality meets user expectations
- Cost/latency constraints prioritize Gemini retention
- No urgent reliability issues reported

**Decision owner**: Engineering lead + Product owner
**Decision deadline**: 30 days after Phase 1 production deployment
