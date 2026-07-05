"""20 synthetic researcher profiles for benchmarking the decision agent and
scorer (as opposed to benchmark_pipeline.py, which only benchmarks the
extraction/discovery agent).

Coverage is deliberate on two axes:
  - Topic: 2 profiles per CCF category used in ccfddl_conferences.py's
    CATEGORY_TRANSLATION table (see src/agents/ccfddl_conferences.py),
    so decision-agent accuracy can be analyzed per research area.
  - Location: spread from near-Europe to far continents, so the distance
    scoring axis gets real variation to analyze (not just "researcher is
    always in Magdeburg").

No groundtruth/correct answers are attached here — this is just the input
side. The scoring rubric is a separate, later task.
"""

from __future__ import annotations

PROFILES: list[dict] = [
    # ── Artificial Intelligence ──────────────────────────────────────────────
    {
        "address": "Otto-von-Guericke-Universität, Magdeburg, Germany",
        "research_title": "AI Agents for Scientific Workflows",
        "research_context": (
            "We build a multi-agent system that automates discovery and ranking "
            "of academic conferences for researchers, combining LLM-based "
            "decision-making with web scraping and structured scoring."
        ),
    },
    {
        "address": "Stanford University, Stanford, CA, USA",
        "research_title": "Large Language Model Alignment",
        "research_context": (
            "My work focuses on reinforcement learning from human feedback and "
            "reducing hallucination in instruction-tuned language models."
        ),
    },
    # ── Network and System Security ──────────────────────────────────────────
    {
        "address": "ETH Zurich, Switzerland",
        "research_title": "Network Security and Cryptography",
        "research_context": (
            "I work on secure communication protocols, zero-knowledge proofs, "
            "and privacy-preserving computation in distributed systems."
        ),
    },
    {
        "address": "National University of Singapore, Singapore",
        "research_title": "Adversarial Machine Learning Security",
        "research_context": (
            "I study attacks and defenses against machine learning models "
            "deployed in production, including model extraction and poisoning."
        ),
    },
    # ── Database/Data Mining/Information Retrieval ───────────────────────────
    {
        "address": "Humboldt University of Berlin, Germany",
        "research_title": "Knowledge Graph Construction from Unstructured Text",
        "research_context": (
            "My research automates knowledge graph population using entity "
            "linking and relation extraction over large scientific corpora."
        ),
    },
    {
        "address": "University of Tokyo, Japan",
        "research_title": "Large-Scale Vector Search and Retrieval",
        "research_context": (
            "I develop approximate nearest neighbor indexing methods for "
            "billion-scale embedding retrieval used in recommendation systems."
        ),
    },
    # ── Graphics ──────────────────────────────────────────────────────────────
    {
        "address": "Technical University of Munich, Germany",
        "research_title": "Neural Rendering and 3D Reconstruction",
        "research_context": (
            "My research focuses on neural radiance fields and differentiable "
            "rendering for photorealistic 3D scene reconstruction."
        ),
    },
    {
        "address": "University of Sydney, Australia",
        "research_title": "Real-Time Physically-Based Animation",
        "research_context": (
            "I work on real-time cloth and fluid simulation techniques for "
            "interactive graphics applications and games."
        ),
    },
    # ── Computer Architecture/Parallel Programming/Storage Technology ───────
    {
        "address": "TU Delft, Netherlands",
        "research_title": "Energy-Efficient GPU Accelerator Design",
        "research_context": (
            "My work designs low-power accelerator architectures for deep "
            "learning inference at the edge, focusing on memory bandwidth "
            "bottlenecks."
        ),
    },
    {
        "address": "Tsinghua University, Beijing, China",
        "research_title": "Distributed Storage Systems for AI Training",
        "research_context": (
            "I build high-throughput distributed file systems optimized for "
            "large-scale machine learning training workloads."
        ),
    },
    # ── Software Engineering/Operating System/Programming Language Design ──
    {
        "address": "TU Wien, Vienna, Austria",
        "research_title": "Automated Program Repair",
        "research_context": (
            "My research uses large language models to automatically detect "
            "and fix software bugs, with formal verification of patches."
        ),
    },
    {
        "address": "University of Toronto, Canada",
        "research_title": "Type Systems for Concurrent Programming Languages",
        "research_context": (
            "I design static type systems that prevent data races and "
            "deadlocks at compile time in concurrent and distributed programs."
        ),
    },
    # ── Computer-Human Interaction ────────────────────────────────────────────
    {
        "address": "IT University of Copenhagen, Denmark",
        "research_title": "Accessible Interfaces for Assistive Technology",
        "research_context": (
            "My work designs and evaluates accessible user interfaces for "
            "people with visual and motor impairments, using participatory "
            "design methods."
        ),
    },
    {
        "address": "KAIST, Daejeon, South Korea",
        "research_title": "Human-AI Collaborative Interfaces",
        "research_context": (
            "I study how users build trust and calibrate reliance on AI "
            "assistants through interface design and explainability cues."
        ),
    },
    # ── Computing Theory ──────────────────────────────────────────────────────
    {
        "address": "University of Oxford, United Kingdom",
        "research_title": "Computational Complexity of Approximation Algorithms",
        "research_context": (
            "My research proves hardness-of-approximation results for "
            "combinatorial optimization problems using the PCP theorem."
        ),
    },
    {
        "address": "University of Sao Paulo, Brazil",
        "research_title": "Formal Verification of Cryptographic Protocols",
        "research_context": (
            "I develop machine-checked proofs of security properties for "
            "cryptographic protocols using formal methods and proof assistants."
        ),
    },
    # ── Network System ────────────────────────────────────────────────────────
    {
        "address": "Sorbonne University, Paris, France",
        "research_title": "Low-Latency Networking for Edge Computing",
        "research_context": (
            "My work optimizes network protocols for latency-sensitive edge "
            "computing applications, including 5G and satellite links."
        ),
    },
    {
        "address": "Indian Institute of Technology Bombay, Mumbai, India",
        "research_title": "Software-Defined Networking and Traffic Engineering",
        "research_context": (
            "I research programmable network control planes for dynamic "
            "traffic engineering in large-scale data center networks."
        ),
    },
    # ── Interdiscipline/Mixture/Emerging ──────────────────────────────────────
    {
        "address": "Universitat Pompeu Fabra, Barcelona, Spain",
        "research_title": "AI for Climate Modeling",
        "research_context": (
            "My interdisciplinary research applies deep learning to improve "
            "the resolution and accuracy of regional climate simulations."
        ),
    },
    {
        "address": "University of Cape Town, South Africa",
        "research_title": "Machine Learning for Public Health Surveillance",
        "research_context": (
            "I combine epidemiology and machine learning to build early "
            "warning systems for infectious disease outbreaks in low-resource "
            "settings."
        ),
    },
]
