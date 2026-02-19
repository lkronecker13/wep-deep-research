# Deep Research Service: Executive Brief

## Executive Summary

The Deep Research Service is a production-grade AI system that automates structured, multi-source research using a coordinated team of four specialized AI agents. Built internally at Wepoint, the system transforms a single research question into a comprehensive, verified report (sources, key findings, and a confidence score included) in under three minutes and at a cost of less than $0.50 per query.

The system serves as an internal productivity tool for our consultants, a working showcase of the agentic AI systems we build for clients, and a source of publishable content on multi-agent architecture. We instrumented every component with evaluation before tuning any of them. A dedicated LLM-as-a-Judge harness assesses each agent individually, so we can measure quality and cost before and after any change.

---

## Leading by Example

### The Credibility Challenge

Clients evaluating AI consulting partners want to see shipped systems, not slide decks. They want evidence that the team has encountered real production challenges and solved them. The Deep Research Service is that evidence.

### Where the Value Compounds

**Internal Tool.** Consultants use the service to accelerate research on client domains: cybersecurity trends, financial analysis methodologies, data engineering best practices. What previously required hours of manual search and synthesis now produces a structured, source-cited report in minutes.

**Consulting Showcase.** Every architecture decision in this project reflects the same patterns we implement for clients: multi-model cost optimization, fault-tolerant parallel execution, real-time streaming, containerized deployment. When a prospect asks "have you built production agentic systems?", we open a terminal and run ours.

**Content Engine.** The architectural decisions we made along the way are already outlined in internal ADRs: why PydanticAI over LangChain, how we handle partial failures in parallel agent execution, why binary PASS/FAIL evaluations outperform numeric scoring. Each one is a blog post waiting to be published, and we have the production data to back the claims.

### Evaluation-Driven from Conception

We instrumented the system before we tuned it, which means we can prove improvement rather than claim it. When we tell clients to build measurement into the foundation, we can show them how we did it ourselves.

### Phased Delivery

The project moved through clear phases: CLI prototype, then production FastAPI service with real-time streaming, then the current evaluation-instrumented system. Each phase shipped working software while laying groundwork for the next.

---

## Technical Edge

### Beyond Agent Demos

Most agent work in the industry stops at demos. The engineering required to ship (typed data contracts, CI gates, test coverage, containerized deployment, observable operations) is where the real work begins. That is the work this project represents.

### Multi-Agent Subsystem

The system coordinates four specialized agents in a structured pipeline, each with a distinct role and model selection optimized for its task:

- **Planning Agent:** Decomposes a research question into up to five complementary search angles. Uses a reasoning-optimized model because the quality of the plan determines the quality of everything downstream.

- **Gathering Agents:** Execute searches in parallel using a cost-efficient model with built-in web search. The system tolerates partial failures: if two of five searches fail due to rate limits or network issues, the workflow continues with the three that succeeded.

- **Synthesis Agent:** Consolidates all gathered information into a coherent report with key findings, source citations, and acknowledged limitations. Uses the reasoning model for analytical depth.

- **Verification Agent:** Reviews the synthesized report for internal consistency, source reliability, and completeness. This is the gate that catches contradictions, unsupported claims, and gaps. It outputs a confidence score between 0 and 1 alongside specific recommendations.

### Multi-Model Cost Optimization

The system assigns models based on what each phase needs. Planning, synthesis, and verification require strong reasoning, so they use Claude Sonnet. Gathering is high-volume parallel search, so it uses Gemini Flash at roughly one-tenth the cost per token. The result: a full research workflow runs well under $0.50 total.

### Evaluation as a Differentiator

The integrated LLM-as-a-Judge evaluation system assesses every agent individually across four quality dimensions: plan quality, source quality, report quality, and verification quality. The evaluation dataset spans 35 questions across seven consulting domains (data, cybersecurity, AI, finance, sales, management, and marketing) with priority tiers for smoke testing through full regression.

All evaluation results are traced through Arize Phoenix, connecting agent execution traces with their quality assessments in a single observability layer. The evaluation harness ships as part of the system, not as an audit layer added afterward.

### Transferable Patterns

Agent specialization, fault-tolerant parallelism, multi-model routing, evaluation-driven development: we have already applied these on client work or will apply them soon.

---

## The System

### The Four-Phase Pipeline

```
                                    ┌─────────────────────┐
                                    │   Research Query     │
                                    └──────────┬──────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────┐
                              │     Phase 1: PLANNING AGENT    │
                              │     (Claude Sonnet)            │
                              │                                │
                              │  Decomposes query into 1-5     │
                              │  strategic search steps with   │
                              │  distinct angles of inquiry    │
                              └──────────────┬─────────────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      │                      │                      │
                      ▼                      ▼                      ▼
           ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
           │ GATHERING AGENT  │  │ GATHERING AGENT  │  │ GATHERING AGENT  │
           │ (Gemini Flash)   │  │ (Gemini Flash)   │  │ (Gemini Flash)   │
           │                  │  │                  │  │                  │
           │ Parallel web     │  │ Parallel web     │  │ Parallel web     │
           │ search + extract │  │ search + extract │  │ search + extract │
           └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                    │                     │                      │
                    └─────────────────────┼──────────────────────┘
                                          │ (tolerates partial failures)
                                          ▼
                              ┌────────────────────────────────┐
                              │    Phase 3: SYNTHESIS AGENT    │
                              │    (Claude Sonnet)             │
                              │                                │
                              │  Consolidates findings into    │
                              │  coherent report with sources, │
                              │  key findings, and limitations │
                              └──────────────┬─────────────────┘
                                             │
                                             ▼
                              ┌────────────────────────────────┐
                              │  Phase 4: VERIFICATION AGENT   │
                              │  (Claude Sonnet)               │
                              │                                │
                              │  Fact-checks report, assesses  │
                              │  source reliability, assigns   │
                              │  confidence score (0-1)        │
                              └──────────────┬─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────────┐
                                    │   Research Report    │
                                    │   + Confidence Score │
                                    │   + Timing Metrics   │
                                    └─────────────────────┘
```

### How Each Phase Works

**Planning** takes the raw query and produces a structured research plan: an executive summary of the approach, up to five search steps each targeting a different aspect of the topic, and analysis instructions for the synthesis phase. This prevents the common failure mode of agentic search, where the system queries the same angle repeatedly.

**Gathering** launches all search steps concurrently using asyncio task groups. Each agent has access to web search tooling and returns structured findings with source URLs. The system is designed for resilience: if some searches fail (network issues, rate limits), the workflow continues with whatever results succeeded. Only a complete failure of all searches halts the pipeline.

**Synthesis** receives the original query, the research plan, and all gathered results. It produces a structured report with a title, summary, key findings, cited sources, and explicitly acknowledged limitations. The agent is instructed to stay grounded in the provided evidence: no speculation, no fabrication.

**Verification** reviews the synthesized report for internal consistency, source quality, claim support, and completeness. It outputs a binary validity assessment, a confidence score between 0 and 1, a list of specific issues found, and actionable recommendations. This final gate ensures that every report delivered to users has been independently reviewed.

### From Research to Production

The project demonstrates a complete lifecycle from initial research through production deployment, with evaluations embedded at every stage:

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Phase 1: POC | Complete | CLI workflow with 4-agent pipeline and OpenTelemetry tracing |
| Phase 2: Service | Complete | FastAPI REST API with real-time Server-Sent Events streaming |
| Phase 2.5: Evaluations | Complete | LLM-as-a-Judge harness with 35-question dataset and Arize Phoenix |
| Phase 3: Durability | Planned | DBOS-backed workflow persistence for long-running research |
| Phase 4: Deployment | Planned | GCP Cloud Run with production observability and cost dashboards |

Phases 1 through 2.5 are complete and running.

### Evaluations as a Central Practice

The evaluation system treats each agent as an independently measurable component. Four dedicated evaluators (one per agent) use Claude Sonnet as an LLM judge to assess output quality:

| Evaluator | What It Measures | Key Criteria |
|-----------|-----------------|--------------|
| Plan Quality | Planning agent output | Relevance, diversity of angles, non-redundancy |
| Source Quality | Each gathering agent's results | Source credibility, factual support, multiple perspectives |
| Report Quality | Synthesis agent output | Comprehensiveness, accuracy, structure, acknowledged limitations |
| Verification Quality | Verification agent output | Justified validity, specific issues, actionable recommendations |

All evaluations use binary PASS/FAIL labels rather than numeric scores. This produces clearer decision boundaries and higher consistency across evaluation runs. Results are logged to Arize Phoenix Cloud, creating a persistent quality record that connects agent execution traces with their evaluation outcomes.

The evaluation dataset covers seven consulting domains with prioritized tiers, from quick smoke tests (7 questions, under 5 minutes) to full regression suites (35 questions), so teams can pick the right depth of testing for any change.

---

## Production Ready

The operational stack is complete: Docker builds, CI pipeline, test coverage, type enforcement. There is nothing to retrofit before deploying.

**Containerization.** A three-stage Docker build (dependency installation, application build, minimal runtime) produces optimized images. The Gunicorn/Uvicorn configuration is tuned for async workloads with request jitter to prevent memory accumulation. Health probes follow Kubernetes conventions, with liveness and readiness endpoints ready for orchestrated deployment.

**CI/CD Pipeline.** Every commit triggers automated formatting, linting, strict type checking, and test execution in parallel. Docker builds are validated on every pull request. Merges to main trigger semantic versioning and automated GitHub releases. No code reaches main without passing the full gate.

**Test Coverage.** An 80% minimum coverage threshold is enforced in the pipeline. The test suite covers the full stack: agent factories, workflow orchestration (including failure modes), API endpoints, SSE streaming, Pydantic model validation, and the evaluation system itself. All tests run without API keys using PydanticAI's TestModel, ensuring the suite is fast, deterministic, and free of external dependencies.

**Code Quality.** Strict mypy type checking, automated formatting with Ruff, and pre-commit hooks enforce consistency. Every function has type annotations. Every data contract uses Pydantic v2 with field-level validation constraints.

**Real-Time Streaming.** The SSE implementation includes heartbeat keepalives, client disconnect detection, bounded queue backpressure, and a 10-minute hard timeout.

Cloud Run deployment is a two-hour job once GCP credentials are provisioned.

---

## Next Steps

**Deploy internally.** Coordinate with DevOps to provision GCP credentials and deploy the service on Cloud Run. The goal is to get it into consultants' hands. The sooner it is in daily use, the sooner we accumulate real usage data and feedback.

**Define the content pipeline.** Sync with Marketing to identify which architectural decisions and evaluation results translate into publishable content. We have ADRs, evaluation reports, and cost breakdowns already written. The remaining work is selecting the angles and mapping them to a publishing calendar.
