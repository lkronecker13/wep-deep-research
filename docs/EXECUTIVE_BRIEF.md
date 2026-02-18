# Deep Research Service — Executive Brief

## 1. Executive Summary

The Deep Research Service is a production-grade AI system that automates structured, multi-source research using a coordinated team of four specialized AI agents. Built internally at Wepoint, the system transforms a single research question into a comprehensive, verified report — complete with sources, key findings, and a confidence score — in under three minutes and at a cost of less than $0.50 per query.

This project serves a triple purpose: it is an internal productivity tool that accelerates our consultants' research workflows, a live demonstration of the production-grade agentic AI systems we build for clients, and a source of publishable thought leadership on multi-agent architecture. Every component is designed to be measured from day one, with a dedicated evaluation harness that assesses each agent individually using LLM-as-a-Judge methodology — ensuring we can continuously optimize quality and cost.

---

## 2. Project Description: Leading by Example

### The Credibility Challenge

As an AI consulting firm, Wepoint's value proposition depends on demonstrating — not just describing — technical expertise. Clients evaluating AI consulting partners want evidence that the team has shipped real systems, encountered real production challenges, and solved them. The Deep Research Service exists to close that gap.

### Triple Value Proposition

The project generates value across three dimensions simultaneously:

**Internal Tool.** Consultants use the service daily to accelerate research on client domains — cybersecurity trends, financial analysis methodologies, data engineering best practices. What previously required hours of manual search and synthesis now produces a structured, source-cited report in minutes.

**Consulting Showcase.** Every architecture decision in this project — multi-model cost optimization, fault-tolerant parallel execution, real-time streaming, containerized deployment — reflects the same patterns we implement for clients. When a prospect asks "have you built production agentic systems?", we demonstrate our own.

**Content Engine.** Each technical decision — why we chose PydanticAI over LangChain, how we handle partial failures in parallel agent execution, why binary PASS/FAIL evaluations outperform numeric scoring — becomes publishable thought leadership. The project funds its own marketing.

### Evaluation-Driven from Conception

Unlike typical internal tools that are built first and measured later, the Deep Research Service was designed with evaluation as a first-class concern. Before optimizing any component, we can measure its baseline performance. Before claiming improvement, we can prove it with data. This discipline — building measurement into the foundation rather than bolting it on afterward — is what we advocate to clients, and what we practice ourselves.

### Phased Delivery

The project follows a disciplined phased approach: from proof of concept (CLI prototype) through production service (FastAPI with real-time streaming) to the current evaluation-instrumented system. Each phase delivered working software while setting up the foundation for the next — demonstrating the iterative delivery model we recommend to clients.

---

## 3. Technical Value: Multi-Agent Leadership

### Production Agentic AI — Not Prototypes

The AI industry is saturated with agent demos. What sets Wepoint apart is shipping production-grade multi-agent systems with the engineering rigor clients expect: typed data contracts, comprehensive test coverage, CI/CD pipelines, containerized deployment, and observable operations. The Deep Research Service is a concrete proof point.

### Multi-Agent Subsystem

The system coordinates four specialized agents in a structured pipeline, each with a distinct role and model selection optimized for its task:

- **Planning Agent** — Decomposes a research question into a strategic search plan with up to five complementary angles. Uses a reasoning-optimized model for complex analytical decomposition.

- **Gathering Agents** — Execute searches in parallel using a cost-efficient model with built-in web search capability. The system tolerates partial failures — if some searches fail, it continues with available results rather than aborting the entire workflow.

- **Synthesis Agent** — Consolidates all gathered information into a coherent report with key findings, source citations, and acknowledged limitations. Uses the reasoning model for analytical depth.

- **Verification Agent** — Fact-checks the synthesized report for internal consistency, source reliability, and completeness. Produces a confidence score and specific improvement recommendations.

### Multi-Model Cost Optimization

Rather than using a single expensive model for every task, the system strategically assigns models based on each phase's requirements. High-reasoning tasks (planning, synthesis, verification) use Claude Sonnet. High-volume parallel tasks (web gathering) use Gemini Flash at roughly one-tenth the cost per token. This keeps the total cost per research workflow well under $0.50 while maintaining quality where it matters most.

### Evaluation as a Differentiator

The integrated LLM-as-a-Judge evaluation system assesses every agent individually across four quality dimensions: plan quality, source quality, report quality, and verification quality. The evaluation dataset spans 35 questions across seven consulting domains — data, cybersecurity, AI, finance, sales, management, and marketing — with priority tiers for smoke testing through full regression.

All evaluation results are traced through Arize Phoenix, providing a persistent observability layer that connects agent execution traces with quality assessments. This is not a post-hoc testing afterthought — it is a core system capability that enables data-driven optimization.

### Transferable Patterns

Every architectural pattern in this system — agent specialization, parallel execution with fault tolerance, multi-model routing, evaluation-driven development — is directly transferable to client engagements. The service functions as both a working reference architecture and a training ground for our engineering team.

---

## 4. Technical Description: How the System Works

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

**Planning** takes the raw query and produces a structured research plan: an executive summary of the approach, up to five search steps each targeting a different aspect of the topic, and analysis instructions for the synthesis phase. This prevents the common failure mode of agentic search — querying the same angle repeatedly.

**Gathering** launches all search steps concurrently using asyncio task groups. Each agent has access to web search tooling and returns structured findings with source URLs. The system is designed for resilience: if some searches fail (network issues, rate limits), the workflow continues with whatever results succeeded. Only a complete failure of all searches halts the pipeline.

**Synthesis** receives the original query, the research plan, and all gathered results. It produces a structured report with a title, summary, key findings, cited sources, and explicitly acknowledged limitations. The agent is instructed to stay grounded in the provided evidence — no speculation, no fabrication.

**Verification** reviews the synthesized report for internal consistency, source quality, claim support, and completeness. It outputs a binary validity assessment, a confidence score between 0 and 1, a list of specific issues found, and actionable recommendations. This final gate ensures that every report delivered to users has been independently reviewed.

### From Research to Production

The project demonstrates a complete lifecycle from initial research through production deployment, with evaluations embedded at every stage:

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Phase 1 — POC | Complete | CLI workflow with 4-agent pipeline and OpenTelemetry tracing |
| Phase 2 — Service | Complete | FastAPI REST API with real-time Server-Sent Events streaming |
| Phase 2.5 — Evaluations | Complete | LLM-as-a-Judge harness with 35-question dataset and Arize Phoenix |
| Phase 3 — Durability | Planned | DBOS-backed workflow persistence for long-running research |
| Phase 4 — Deployment | Planned | GCP Cloud Run with production observability and cost dashboards |

This phased approach ensures that each increment delivers usable software while building toward a fully production-hardened system.

### Evaluations as a Central Practice

The evaluation system treats each agent as an independently measurable component. Four dedicated evaluators — one per agent — use Claude Sonnet as an LLM judge to assess output quality:

| Evaluator | What It Measures | Key Criteria |
|-----------|-----------------|--------------|
| Plan Quality | Planning agent output | Relevance, diversity of angles, non-redundancy |
| Source Quality | Each gathering agent's results | Source credibility, factual support, multiple perspectives |
| Report Quality | Synthesis agent output | Comprehensiveness, accuracy, structure, acknowledged limitations |
| Verification Quality | Verification agent output | Justified validity, specific issues, actionable recommendations |

All evaluations use binary PASS/FAIL labels rather than numeric scores — a deliberate design choice that produces clearer decision boundaries and higher consistency across evaluation runs. Results are logged to Arize Phoenix Cloud, creating a persistent quality record that connects agent execution traces with their evaluation outcomes.

The evaluation dataset covers seven consulting domains with prioritized tiers — from quick smoke tests (7 questions, under 5 minutes) to full regression suites (35 questions) — enabling teams to choose the appropriate level of validation for any change.

---

## 5. Operational Maturity

The Deep Research Service is engineered for production deployment, not assembled as a prototype:

**Containerization.** A three-stage Docker build (dependency installation, application build, minimal runtime) produces optimized images. The Gunicorn/Uvicorn configuration is tuned for async workloads with request jitter to prevent memory accumulation. Health probes follow Kubernetes conventions — liveness and readiness endpoints are ready for orchestrated deployment.

**CI/CD Pipeline.** Every commit triggers automated formatting, linting, strict type checking, and test execution in parallel. Docker builds are validated on every pull request. Merges to main trigger semantic versioning and automated GitHub releases. No code reaches main without passing the full gate.

**Test Coverage.** An 80% minimum coverage threshold is enforced in the pipeline. The test suite covers the full stack — agent factories, workflow orchestration (including failure modes), API endpoints, SSE streaming, Pydantic model validation, and the evaluation system itself. All tests run without API keys using PydanticAI's TestModel, ensuring the suite is fast, deterministic, and free of external dependencies.

**Code Quality.** Strict mypy type checking, automated formatting with Ruff, and pre-commit hooks enforce consistency. Every function has type annotations. Every data contract uses Pydantic v2 with field-level validation constraints.

**Real-Time Streaming.** The SSE implementation includes heartbeat keepalives, client disconnect detection, bounded queue backpressure, and a 10-minute hard timeout — the kind of production concerns that distinguish deployed systems from demos.

This operational foundation means the system can move to cloud deployment without rewriting infrastructure. The gap between "working locally" and "running in production" is configuration, not engineering.
