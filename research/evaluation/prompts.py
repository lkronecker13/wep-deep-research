"""LLM-as-a-Judge prompt templates for Agent Evaluation.

Defines evaluation prompt structures using discrete labels per LLM evaluation best practices.
- Clear decision boundaries help LLMs make consistent judgments.
- Binary labels reduce ambiguity compared to numeric scores.
- Higher inter-rater reliability is observed with discrete labels.
- Structured output formats ensure consistent parsing of LLM responses.
"""
# ===============================================
# Planning Agent Evaluation Prompt
# ===============================================

PLAN_QUALITY_PROMPT = """You are an expert AI agent evaluator. You are evaluating the quality of a research plan created by an AI planning agent.

## Original Query
{query}

## Research Plan
Executive Summary: {executive_summary}
Web Search Steps: {web_search_steps}
Analysis Instructions: {analysis_instructions}

## Evaluation Criteria
Evaluate whether the research plan effectively addresses the original query based on the following criteria:
1. Are the search steps and analysis instructions relevant to the query?
2. Do the search steps cover diverse and important aspects of the topic?
3. Are the search steps non-overlapping and non-redundant?
4. Is the executive summary accurately descriptive of the plan's content and approach?
5. Are the Analysis Instructions clear and actionable for synthesizing findings?

## Decision Rule
- PASS: Must pass criteria 1 and 2 (required), plus at least two of criteria 3, 4, or 5
- FAIL: Fails any required criterion (1 or 2) OR fails more than one optional criterion

## Instructions
First, evaluate each criterion and provide brief reasoning with evidence.
Then, provide your final label.

**Reasoning:** [Evaluate each criterion with brief evidence]
**Label:** PASS or FAIL

"""
# ===============================================
# Gathering Agent Evaluation Prompt
# ===============================================

SOURCE_QUALITY_PROMPT = """You are an expert AI agent evaluator. You are evaluating the quality of sources and information gathered by an AI research gathering agent.

## Search Query
{search_query}

## Gathered Findings
Findings: {findings}
Sources: {sources}

## Evaluation Criteria
Evaluate whether the gathered findings and sources effectively address the search query based on the following criteria:
1. Are the findings relevant and accurate with respect to the search query?
2. Are the sources credible and authoritative (not spam, not unreliable sites)?
3. Is the information factual and well-supported by evidence from the sources?
4. Are multiple perspectives considered, avoiding bias or one-sided views?

## Decision Rule
- PASS: Must pass criteria 1, 2, and 3 (required), criterion 4 is recommended but not required
- FAIL: Fails any required criterion (1, 2, or 3)

## Instructions
First, evaluate each criterion and provide brief reasoning with evidence.
Then, provide your final label.

**Reasoning:** [Evaluate each criterion with brief evidence]
**Label:** PASS or FAIL

"""
# ===============================================
# Synthesis Agent Evaluation Prompt
# ===============================================

REPORT_QUALITY_PROMPT = """You are an expert AI agent evaluator. You are evaluating the quality of a research report synthesized by an AI synthesis agent.

## Original Query
{query}

## Research Report
Title: {title}
Summary: {summary}
Key Findings: {key_findings}
Sources: {sources}
Limitations: {limitations}

## Evaluation Criteria
Evaluate whether the research report effectively addresses the original query based on the following criteria:
1. Does the report comprehensively address the research query?
2. Are the key findings accurate, relevant, and well-supported by the cited sources?
3. Is the report well-structured, clear, and coherent?
4. Are limitations and gaps in the research appropriately acknowledged?
5. Does the summary accurately reflect the content of the report?

## Decision Rule
- PASS: Must pass criteria 1, 2, and 3 (required), plus at least one of criteria 4 or 5
- FAIL: Fails any required criterion (1, 2, or 3) OR fails both criteria 4 and 5

## Instructions
First, evaluate each criterion and provide brief reasoning with evidence.
Then, provide your final label.

**Reasoning:** [Evaluate each criterion with brief evidence]
**Label:** PASS or FAIL

"""

# ===============================================
# Verification Agent Evaluation Prompt
# ===============================================
# The verification agent outputs a `confidence_score` (0.0-1.0) as part of its
# validation result. This evaluator assesses whether the confidence score is
# appropriate given the findings and evidence (criterion 2). The evaluator still
# uses discrete PASS/FAIL labels per LLM evaluation best practices.

VERIFICATION_QUALITY_PROMPT = """You are an expert AI agent evaluator. You are evaluating the quality of a verification performed by an AI verification agent.

## Original Research Report (Being Verified)
Title: {report_title}
Summary: {report_summary}
Key Findings: {report_key_findings}
Sources: {report_sources}
Limitations: {report_limitations}

## Verification Result
Is Valid: {is_valid}
Confidence Score: {confidence_score}
Issues Found: {issues_found}
Recommendations: {recommendations}

## Evaluation Criteria
Evaluate whether the verification result effectively assesses the quality of the research report based on the following criteria:
1. Is the validity determination justified based on the issues found?
2. Is the confidence score appropriate given the findings and evidence?
3. Are the issues found specific, relevant, and significant? (not false positives)
4. Are the recommendations actionable, relevant, and likely to improve the report quality?

## Decision Rule
- PASS: Must pass criteria 1 and 3 (required), plus at least one of criteria 2 or 4
- FAIL: Fails any required criterion (1 or 3) OR fails both criteria 2 and 4

## Instructions
First, evaluate each criterion and provide brief reasoning with evidence.
Then, provide your final label.

**Reasoning:** [Evaluate each criterion with brief evidence]
**Label:** PASS or FAIL

"""
