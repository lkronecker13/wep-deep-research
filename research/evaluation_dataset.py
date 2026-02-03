"""Synthetic evaluation dataset for deep research system validation.

This dataset provides 100 categorized research questions designed to evaluate
the performance and capabilities of the 4-agent deep research system across
diverse domains and difficulty levels.
"""

from __future__ import annotations

import random
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ResearchCategory(str, Enum):
    """Research question categories for dataset organization."""

    TECHNICAL = "technical"
    BUSINESS = "business"
    SCIENTIFIC = "scientific"
    HISTORICAL = "historical"
    COMPARATIVE = "comparative"
    EMERGING = "emerging"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"


class EvaluationQuestion(BaseModel):
    """A single evaluation research question with metadata.

    Each question represents a benchmark scenario for assessing the
    research system's ability to plan, gather, synthesize, and verify
    information across different domains and difficulty levels.
    """

    id: str = Field(description="Unique identifier (e.g., 'tech_001')")
    query: str = Field(description="Research question")
    category: ResearchCategory = Field(description="Question category")
    difficulty: str = Field(description="Difficulty level: easy, medium, hard")
    expected_sources: int = Field(description="Approximate expected source count")
    notes: str = Field(default="", description="Optional notes about the question")


class EvaluationDataset(BaseModel):
    """Complete evaluation dataset with helper methods.

    Provides a curated collection of 100 research questions spanning 8 categories,
    designed to benchmark the deep research system's capabilities across diverse
    scenarios including technical documentation, business analysis, scientific
    research, and historical investigation.
    """

    version: str = Field(default="1.0.0", description="Dataset version")
    questions: list[EvaluationQuestion] = Field(default_factory=list, description="Evaluation questions")

    def by_category(self, category: ResearchCategory) -> list[EvaluationQuestion]:
        """Get all evaluation questions for a specific category."""
        return [q for q in self.questions if q.category == category]

    def sample(self, size: int = 10) -> list[EvaluationQuestion]:
        """Randomly sample N evaluation questions from the dataset."""
        return random.sample(self.questions, min(size, len(self.questions)))


def get_evaluation_dataset() -> EvaluationDataset:
    """Get the complete evaluation dataset with 100+ categorized questions.

    This dataset serves as a benchmark for assessing the deep research system's
    capabilities across diverse domains and difficulty levels.

    Returns:
        EvaluationDataset: Dataset containing all evaluation questions across 8 categories
    """
    questions = [
        # Technical (AI/ML, software) - 20 questions
        EvaluationQuestion(
            id="tech_001",
            query="What is PydanticAI and how does it differ from LangChain?",
            category=ResearchCategory.TECHNICAL,
            difficulty="easy",
            expected_sources=5,
            notes="Test understanding of modern AI frameworks",
        ),
        EvaluationQuestion(
            id="tech_002",
            query="Explain the architecture and benefits of retrieval-augmented generation (RAG) systems",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="tech_003",
            query="What are the latest advancements in transformer model architectures as of 2025?",
            category=ResearchCategory.TECHNICAL,
            difficulty="hard",
            expected_sources=10,
            notes="Requires recent information",
        ),
        EvaluationQuestion(
            id="tech_004",
            query="How does fine-tuning differ from prompt engineering for LLM customization?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="tech_005",
            query="What are the key techniques for reducing hallucinations in large language models?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="tech_006",
            query="Explain vector databases and their role in semantic search applications",
            category=ResearchCategory.TECHNICAL,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="tech_007",
            query="What is the difference between Docker and Kubernetes in container orchestration?",
            category=ResearchCategory.TECHNICAL,
            difficulty="easy",
            expected_sources=4,
        ),
        EvaluationQuestion(
            id="tech_008",
            query="How do graph neural networks differ from traditional neural networks?",
            category=ResearchCategory.TECHNICAL,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="tech_009",
            query="What are the main architectural patterns for microservices communication?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="tech_010",
            query="Explain zero-shot, few-shot, and chain-of-thought prompting techniques",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="tech_011",
            query="What are the security considerations for deploying AI models in production?",
            category=ResearchCategory.TECHNICAL,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="tech_012",
            query="How does federated learning enable privacy-preserving machine learning?",
            category=ResearchCategory.TECHNICAL,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="tech_013",
            query="What is the role of attention mechanisms in modern neural architectures?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="tech_014",
            query="Explain the concept of model quantization and its impact on inference speed",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="tech_015",
            query="What are the latest techniques for efficient long-context processing in LLMs?",
            category=ResearchCategory.TECHNICAL,
            difficulty="hard",
            expected_sources=8,
            notes="Requires 2025 information",
        ),
        EvaluationQuestion(
            id="tech_016",
            query="How do continuous integration and continuous deployment (CI/CD) pipelines work?",
            category=ResearchCategory.TECHNICAL,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="tech_017",
            query="What are the key differences between SQL and NoSQL databases?",
            category=ResearchCategory.TECHNICAL,
            difficulty="easy",
            expected_sources=4,
        ),
        EvaluationQuestion(
            id="tech_018",
            query="Explain the concept of event-driven architecture and its use cases",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="tech_019",
            query="What are multimodal AI models and what capabilities do they enable?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="tech_020",
            query="How do recommendation systems use collaborative filtering and content-based approaches?",
            category=ResearchCategory.TECHNICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        # Business (markets, strategy) - 20 questions
        EvaluationQuestion(
            id="biz_001",
            query="What are the key factors driving the adoption of AI in small businesses?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="biz_002",
            query="How has remote work affected commercial real estate markets since 2020?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="biz_003",
            query="What are the main competitive strategies for SaaS companies in 2025?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="biz_004",
            query="Explain the subscription economy and its impact on traditional retail",
            category=ResearchCategory.BUSINESS,
            difficulty="easy",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="biz_005",
            query="What are the economic implications of the gig economy on labor markets?",
            category=ResearchCategory.BUSINESS,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="biz_006",
            query="How do venture capital firms evaluate early-stage startups?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="biz_007",
            query="What are the key metrics for measuring SaaS business health and growth?",
            category=ResearchCategory.BUSINESS,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="biz_008",
            query="How has e-commerce disrupted traditional retail supply chains?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="biz_009",
            query="What are the main challenges facing the electric vehicle market in 2025?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="biz_010",
            query="Explain the concept of platform business models and network effects",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="biz_011",
            query="What are the primary factors influencing cryptocurrency market volatility?",
            category=ResearchCategory.BUSINESS,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="biz_012",
            query="How do companies use customer lifetime value (CLV) for strategic decisions?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="biz_013",
            query="What are the key considerations for pricing strategies in B2B SaaS?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="biz_014",
            query="How has AI automation affected job markets across different industries?",
            category=ResearchCategory.BUSINESS,
            difficulty="hard",
            expected_sources=11,
        ),
        EvaluationQuestion(
            id="biz_015",
            query="What are the main drivers of success for marketplace businesses?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="biz_016",
            query="Explain the concept of blue ocean strategy versus red ocean competition",
            category=ResearchCategory.BUSINESS,
            difficulty="easy",
            expected_sources=4,
        ),
        EvaluationQuestion(
            id="biz_017",
            query="What are the economic impacts of carbon pricing policies on industries?",
            category=ResearchCategory.BUSINESS,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="biz_018",
            query="How do companies measure and optimize customer acquisition cost (CAC)?",
            category=ResearchCategory.BUSINESS,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="biz_019",
            query="What are the key trends in direct-to-consumer (D2C) brand strategies?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="biz_020",
            query="How has fintech disrupted traditional banking services?",
            category=ResearchCategory.BUSINESS,
            difficulty="medium",
            expected_sources=9,
        ),
        # Scientific (research studies) - 15 questions
        EvaluationQuestion(
            id="sci_001",
            query="What are the latest findings on CRISPR gene editing safety and efficacy?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="sci_002",
            query="Explain the current scientific understanding of long COVID symptoms and treatments",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=12,
        ),
        EvaluationQuestion(
            id="sci_003",
            query="What are the main theories explaining the accelerated expansion of the universe?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="sci_004",
            query="How do mRNA vaccines work and what makes them different from traditional vaccines?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="sci_005",
            query="What are the latest developments in quantum computing hardware?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=11,
        ),
        EvaluationQuestion(
            id="sci_006",
            query="Explain the role of the gut microbiome in human health and disease",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="sci_007",
            query="What are the current theories on the origin of consciousness?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="sci_008",
            query="How does neuroplasticity enable the brain to adapt and reorganize?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="sci_009",
            query="What are the main approaches to developing fusion energy power plants?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="sci_010",
            query="Explain the evidence for and against the simulation hypothesis",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="sci_011",
            query="What are the latest discoveries about exoplanets in habitable zones?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="sci_012",
            query="How do CRISPR-based diagnostics work for disease detection?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="sci_013",
            query="What are the main mechanisms behind aging at the cellular level?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="sci_014",
            query="Explain the current state of research on artificial photosynthesis",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="sci_015",
            query="What are the key findings from recent studies on ocean acidification impacts?",
            category=ResearchCategory.SCIENTIFIC,
            difficulty="medium",
            expected_sources=9,
        ),
        # Historical (past events) - 10 questions
        EvaluationQuestion(
            id="hist_001",
            query="What were the key events leading to the fall of the Berlin Wall in 1989?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="hist_002",
            query="How did the Manhattan Project develop the first atomic bomb?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="hist_003",
            query="What factors led to the 2008 financial crisis?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="hist_004",
            query="Explain the key milestones in the history of the internet from ARPANET to today",
            category=ResearchCategory.HISTORICAL,
            difficulty="easy",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="hist_005",
            query="What were the main causes and consequences of the Industrial Revolution?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="hist_006",
            query="How did the printing press change society in Renaissance Europe?",
            category=ResearchCategory.HISTORICAL,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="hist_007",
            query="What were the key technological innovations during the Space Race?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="hist_008",
            query="How did the green revolution transform global agriculture?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="hist_009",
            query="What were the main factors that led to the dot-com bubble and its burst?",
            category=ResearchCategory.HISTORICAL,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="hist_010",
            query="How did the invention of the transistor revolutionize electronics?",
            category=ResearchCategory.HISTORICAL,
            difficulty="easy",
            expected_sources=5,
        ),
        # Comparative (X vs Y) - 15 questions
        EvaluationQuestion(
            id="comp_001",
            query="Compare and contrast supervised learning versus unsupervised learning in machine learning",
            category=ResearchCategory.COMPARATIVE,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="comp_002",
            query="What are the key differences between agile and waterfall project management methodologies?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="easy",
            expected_sources=4,
        ),
        EvaluationQuestion(
            id="comp_003",
            query="Compare the capabilities and limitations of GPT-4 versus Claude 3",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="comp_004",
            query="How do solar and wind energy compare in terms of efficiency and scalability?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="comp_005",
            query="What are the differences between centralized and decentralized blockchain architectures?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="comp_006",
            query="Compare the economic systems of capitalism and socialism",
            category=ResearchCategory.COMPARATIVE,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="comp_007",
            query="How do relational and graph databases differ in structure and use cases?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="comp_008",
            query="Compare inductive versus deductive reasoning in scientific research",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="comp_009",
            query="What are the key differences between React, Vue, and Angular frameworks?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="comp_010",
            query="Compare public cloud versus private cloud infrastructure for enterprises",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="comp_011",
            query="How do electric vehicles compare to hydrogen fuel cell vehicles?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="comp_012",
            query="Compare traditional education versus online learning effectiveness",
            category=ResearchCategory.COMPARATIVE,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="comp_013",
            query="What are the differences between B2B and B2C marketing strategies?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="easy",
            expected_sources=5,
        ),
        EvaluationQuestion(
            id="comp_014",
            query="Compare the approaches of interpretable AI versus black-box models",
            category=ResearchCategory.COMPARATIVE,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="comp_015",
            query="How do monolithic versus microservices architectures compare in complexity and scalability?",
            category=ResearchCategory.COMPARATIVE,
            difficulty="medium",
            expected_sources=6,
        ),
        # Emerging (new trends) - 10 questions
        EvaluationQuestion(
            id="emrg_001",
            query="What are the latest trends in generative AI for code development?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=8,
            notes="Requires 2025 information",
        ),
        EvaluationQuestion(
            id="emrg_002",
            query="How is edge computing transforming IoT applications?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="emrg_003",
            query="What are the emerging applications of brain-computer interfaces?",
            category=ResearchCategory.EMERGING,
            difficulty="hard",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="emrg_004",
            query="How is synthetic biology being used to create new materials and medicines?",
            category=ResearchCategory.EMERGING,
            difficulty="hard",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="emrg_005",
            query="What are the latest developments in autonomous vehicle technology?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=9,
        ),
        EvaluationQuestion(
            id="emrg_006",
            query="How is Web3 technology changing digital ownership and identity?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="emrg_007",
            query="What are the emerging trends in personalized medicine and genomics?",
            category=ResearchCategory.EMERGING,
            difficulty="hard",
            expected_sources=10,
        ),
        EvaluationQuestion(
            id="emrg_008",
            query="How is augmented reality being integrated into enterprise workflows?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="emrg_009",
            query="What are the latest trends in sustainable fashion and circular economy?",
            category=ResearchCategory.EMERGING,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="emrg_010",
            query="How is AI being used to accelerate drug discovery processes?",
            category=ResearchCategory.EMERGING,
            difficulty="hard",
            expected_sources=9,
        ),
        # Synthesis (multi-domain) - 5 questions
        EvaluationQuestion(
            id="synth_001",
            query="How can AI and biotechnology combine to address climate change challenges?",
            category=ResearchCategory.SYNTHESIS,
            difficulty="hard",
            expected_sources=12,
        ),
        EvaluationQuestion(
            id="synth_002",
            query="What are the ethical, technical, and societal implications of widespread AI adoption?",
            category=ResearchCategory.SYNTHESIS,
            difficulty="hard",
            expected_sources=15,
        ),
        EvaluationQuestion(
            id="synth_003",
            query="How do economic incentives, policy frameworks, and technology intersect in renewable energy adoption?",
            category=ResearchCategory.SYNTHESIS,
            difficulty="hard",
            expected_sources=13,
        ),
        EvaluationQuestion(
            id="synth_004",
            query="What are the interconnections between urbanization, public health, and environmental sustainability?",
            category=ResearchCategory.SYNTHESIS,
            difficulty="hard",
            expected_sources=14,
        ),
        EvaluationQuestion(
            id="synth_005",
            query="How do psychology, technology design, and business strategy combine in building habit-forming products?",
            category=ResearchCategory.SYNTHESIS,
            difficulty="hard",
            expected_sources=11,
        ),
        # Validation (fact-checking) - 5 questions
        EvaluationQuestion(
            id="val_001",
            query="Is quantum computing currently capable of breaking RSA encryption?",
            category=ResearchCategory.VALIDATION,
            difficulty="medium",
            expected_sources=7,
        ),
        EvaluationQuestion(
            id="val_002",
            query="Do humans only use 10% of their brain capacity?",
            category=ResearchCategory.VALIDATION,
            difficulty="easy",
            expected_sources=4,
            notes="Common myth to debunk",
        ),
        EvaluationQuestion(
            id="val_003",
            query="Has artificial general intelligence (AGI) been achieved as of 2025?",
            category=ResearchCategory.VALIDATION,
            difficulty="easy",
            expected_sources=6,
        ),
        EvaluationQuestion(
            id="val_004",
            query="Are electric vehicles truly zero-emission when considering full lifecycle?",
            category=ResearchCategory.VALIDATION,
            difficulty="medium",
            expected_sources=8,
        ),
        EvaluationQuestion(
            id="val_005",
            query="Can blockchain technology eliminate all forms of financial fraud?",
            category=ResearchCategory.VALIDATION,
            difficulty="medium",
            expected_sources=7,
        ),
    ]

    return EvaluationDataset(version="1.0.0", questions=questions)


def export_dataset_to_json(output_path: str | Path = "research/evaluation_dataset.json") -> Path:
    """Export the complete evaluation dataset to a JSON file.

    Creates a pretty-printed JSON file containing all evaluation questions with metadata.
    The output directory is created if it doesn't exist.

    Args:
        output_path: Destination path for JSON export. Can be relative or absolute.
            Default: research/evaluation_dataset.json

    Returns:
        Path: Absolute path to the exported file

    Raises:
        ValueError: If path is outside allowed directories
        OSError: If unable to create output directory or write file

    Example:
        >>> export_dataset_to_json()  # Uses default path
        >>> export_dataset_to_json("data/questions.json")  # Custom path
    """
    from pathlib import Path

    dataset = get_evaluation_dataset()
    output_file = Path(output_path).resolve()  # Resolve to absolute path

    # Validate path is within project or research directory (security)
    # Allow /tmp for testing purposes
    allowed_dirs = [
        Path.cwd().resolve(),
        (Path.cwd() / "research").resolve(),
        Path("/tmp").resolve(),
        Path("/private/var/folders").resolve(),  # macOS tmp
    ]

    if not any(output_file.is_relative_to(d) for d in allowed_dirs):
        raise ValueError(f"Output path must be within project directory. Got: {output_file}")

    # Ensure directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Export with pretty formatting
    output_file.write_text(dataset.model_dump_json(indent=2))

    print(f"Dataset exported to: {output_file}")
    print(f"   Total questions: {len(dataset.questions)}")
    print(f"   Categories: {len(set(q.category for q in dataset.questions))}")

    return output_file


if __name__ == "__main__":
    """CLI entry point for exporting dataset."""
    import sys

    try:
        output_path = sys.argv[1] if len(sys.argv) > 1 else "research/evaluation_dataset.json"
        export_dataset_to_json(output_path)
    except ValueError as e:
        print(f"Error: Invalid path - {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: File system error - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error - {e}", file=sys.stderr)
        sys.exit(1)
