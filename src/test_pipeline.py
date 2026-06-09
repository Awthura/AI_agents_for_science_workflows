"""
End-to-end pipeline test using pre-fetched CCF-Deadlines data.
Skips scraping entirely — loads future_conferences.json directly,
runs the decision agent, scores results, and prints a ranked list.

Usage (from repo root):
    python src/test_pipeline.py
"""

import hashlib
import json
import os
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))

from agents.decision import run_decision_agent
from agents.scorer import run_scorer
from schemas.conference import (
    Conference,
    ConferenceDates,
    ConferenceLocation,
    CoreRank,
    UserPreferences,
)

console = Console()

# ── Config ───────────────────────────────────────────────────────────────────
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DATA_FILE = Path(__file__).parent.parent / "future_conferences.json"
RESULTS_FILE = Path(__file__).parent.parent / "pipeline_results.json"

# ── Test profiles (add or edit to simulate different researchers) ─────────────
TEST_PROFILES = [
    UserPreferences(
        address="Otto-von-Guericke-Universität, Magdeburg, Germany",
        coordinates=None,
        research_title="AI Agents for Scientific Workflows",
        research_context=(
            "We are building a multi-agent system that automates the discovery and "
            "ranking of academic conferences for researchers using LLMs and web scraping."
        ),
    ),
    UserPreferences(
        address="Technical University of Munich, Germany",
        coordinates=None,
        research_title="Computer Vision and Deep Learning",
        research_context=(
            "My research focuses on object detection and image segmentation using "
            "transformer-based models and self-supervised learning techniques."
        ),
    ),
    UserPreferences(
        address="ETH Zurich, Switzerland",
        coordinates=None,
        research_title="Network Security and Cryptography",
        research_context=(
            "I work on secure communication protocols, zero-knowledge proofs, "
            "and privacy-preserving computation in distributed systems."
        ),
    ),
]

MAX_CONFERENCES = 46       # use all available conferences
MIN_RELEVANCY = 30         # drop conferences below this relevancy score
TEST_MODELS = ["llama3.2", "gemma2:9b"]  # models to compare (RQ1/RQ2)

# Keywords per CCF topic category that must overlap with the research profile
# to pass the pre-filter. Empty set = always pass through to LLM.
_TOPIC_KEYWORDS: dict[str, set[str]] = {
    "Artificial Intelligence":                              {"ai", "intelligence", "machine learning", "deep learning", "neural", "agent", "llm", "language model", "nlp", "vision", "knowledge", "reasoning"},
    "Computer-Human Interaction":                           {"human", "interaction", "interface", "user", "hci", "usability", "ux", "accessibility"},
    "Network System":                                       {"network", "distributed", "protocol", "wireless", "cloud", "routing", "communication", "internet"},
    "Network and System Security":                          {"security", "cryptograph", "privacy", "encryption", "cyber", "authentication", "attack", "zero-knowledge", "protocol"},
    "Graphics":                                             {"graphic", "render", "visual", "image", "video", "3d", "vision", "pixel", "animation"},
    "Database/Data Mining/Information Retrieval":           {"database", "data mining", "retrieval", "sql", "query", "information retrieval", "knowledge graph"},
    "Computing Theory":                                     {"algorithm", "theory", "complexity", "computation", "mathematical", "formal", "cryptograph", "proof"},
    "Software Engineering/Operating System/Programming Language Design": {"software", "programming", "operating system", "compiler", "language", "devops", "testing"},
    "Computer Architecture/Parallel Programming/Storage Technology":     {"architecture", "parallel", "hardware", "storage", "processor", "gpu", "memory", "accelerat"},
    "Interdiscipline/Mixture/Emerging":                     set(),  # Too broad — always pass to LLM
}


def _passes_topic_filter(conf: "Conference", profile: "UserPreferences") -> bool:
    """Return False if the conference topic clearly cannot match the research profile."""
    profile_text = (profile.research_title + " " + profile.research_context).lower()
    for topic in conf.topics:
        keywords = _TOPIC_KEYWORDS.get(topic, set())
        if not keywords:  # empty set = always pass
            return True
        if any(kw in profile_text for kw in keywords):
            return True
    return False


def _safe_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def load_conferences(path: Path) -> list[Conference]:
    """Load and convert future_conferences.json into Conference objects."""
    if not path.exists():
        console.print(f"[red][!] Data file not found: {path}[/red]")
        console.print("    Run: python src/fetcher/ccf-deadlines_fetcher.py && python src/agents/ccfddl_conferences.py")
        sys.exit(1)

    raw = json.loads(path.read_text(encoding="utf-8"))
    conferences = []

    for entry in raw.get("conferences", []):
        start = _safe_date(entry.get("start_date", ""))
        if not start:
            continue

        conf_id = hashlib.md5(
            f"{entry.get('name', '').lower()}{start.year}".encode()
        ).hexdigest()[:12]

        city = entry.get("city", "").strip()
        country = entry.get("country", "").strip()
        location = ConferenceLocation(city=city, country=country) if city or country else None

        deadline = _safe_date(entry.get("submission_deadline", ""))

        # Parse CORE rank from ccfddl data
        core_rank = None
        rank_raw = entry.get("core_rank", "")
        if rank_raw:
            rank_map = {"A*": CoreRank.A_STAR, "A": CoreRank.A, "B": CoreRank.B, "C": CoreRank.C}
            core_rank = rank_map.get(str(rank_raw).strip(), CoreRank.UNRANKED)

        try:
            conf = Conference(
                id=conf_id,
                name=entry.get("name", "Unknown"),
                acronym=entry.get("acronym") or None,
                year=start.year,
                url=entry.get("url") or None,
                source_url="ccfddl",
                scraped_at=datetime.now(),
                dates=ConferenceDates(
                    start=start,
                    submission_deadline=deadline,
                ),
                location=location,
                topics=entry.get("topics", []),
                core_rank=core_rank,
            )
            conferences.append(conf)
        except Exception:
            continue

    return conferences


def run_for_profile(profile: UserPreferences, conferences: list[Conference], idx: int, model: str = OLLAMA_MODEL) -> dict:
    console.print(Panel(
        f"[bold]Profile {idx} — {profile.research_title}[/bold]\n"
        f"Model:    {model}\n"
        f"Location: {profile.address}\n"
        f"Context:  {profile.research_context}",
        expand=False,
    ))

    # ── Topic pre-filter (keyword-based, no LLM) ────────────────────────────
    pre_filtered = [c for c in conferences if _passes_topic_filter(c, profile)]
    pre_rejected = len(conferences) - len(pre_filtered)
    console.print(f"\n[*] Topic pre-filter: {len(pre_filtered)} passed, {pre_rejected} rejected (no topic overlap).")

    # ── Decision agent ───────────────────────────────────────────────────────
    console.print("[yellow][1/2] Running decision agent...[/yellow]")
    accepted, rejected, decision_timing = run_decision_agent(
        pre_filtered, profile, model, OLLAMA_URL
    )
    console.print(
        f"  [✓] Accepted: [green]{len(accepted)}[/green]  |  Rejected: [red]{len(rejected)}[/red]  |  "
        f"Avg: {decision_timing['mean_s']}s  Total: {decision_timing['total_s']}s"
    )

    if not accepted:
        console.print("[red]  No conferences passed the decision agent.[/red]\n")
        return {"profile": profile.research_title, "accepted": 0, "results": [],
                "timing": {"decision": decision_timing}}

    # ── Scorer ───────────────────────────────────────────────────────────────
    console.print("\n[yellow][2/2] Scoring accepted conferences...[/yellow]")
    scored, scorer_timing = run_scorer(accepted, profile, model, OLLAMA_URL)

    # Apply minimum relevancy filter
    before_filter = len(scored)
    scored = [c for c in scored if c.scores and c.scores.relevancy >= MIN_RELEVANCY]
    filtered = before_filter - len(scored)
    console.print(
        f"  [✓] Scored {before_filter} conference(s). Filtered out {filtered} with relevancy < {MIN_RELEVANCY}.  "
        f"Avg: {scorer_timing['mean_s']}s  Total: {scorer_timing['total_s']}s"
    )

    # ── Results table ────────────────────────────────────────────────────────
    console.print(f"\n[bold green]Top {len(scored)} Recommendations:[/bold green]\n")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Acronym", width=8)
    table.add_column("Name", min_width=20, no_wrap=False)
    table.add_column("Date", width=12)
    table.add_column("Location", width=20)
    table.add_column("Deadline", width=12)
    table.add_column("Rel", width=5, justify="right")
    table.add_column("Dist", width=5, justify="right")
    table.add_column("Pres", width=5, justify="right")
    table.add_column("Total", width=7, justify="right")

    for i, conf in enumerate(scored, 1):
        location_str = conf.location.city if conf.location else "—"
        date_str = str(conf.dates.start) if conf.dates.start else "—"
        deadline_str = str(conf.dates.submission_deadline) if conf.dates.submission_deadline else "—"
        acronym = f"[bold]{conf.acronym}[/bold]" if conf.acronym else "—"

        if conf.scores:
            table.add_row(
                str(i), acronym, conf.name, date_str, location_str, deadline_str,
                f"{conf.scores.relevancy:.0f}",
                f"{conf.scores.distance:.0f}",
                f"{conf.scores.prestige:.0f}",
                f"[bold]{conf.scores.total:.1f}[/bold]",
            )

    console.print(table)

    if scored and scored[0].decision:
        top = scored[0]
        console.print(
            f"\n[bold]Best match:[/bold] {top.acronym or top.name}\n"
            f"  Reason: [italic]{top.decision.reason}[/italic]\n"
        )

    return {
        "profile": profile.research_title,
        "model": model,
        "location": profile.address,
        "pre_filtered_topic_mismatch": pre_rejected,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "filtered_low_relevancy": before_filter - len(scored),
        "timing": {
            "decision": decision_timing,
            "scorer": scorer_timing,
            "total_s": round(decision_timing["total_s"] + scorer_timing["total_s"], 2),
        },
        "results": [
            {
                "rank": i + 1,
                "name": c.name,
                "acronym": c.acronym,
                "date": str(c.dates.start),
                "deadline": str(c.dates.submission_deadline) if c.dates.submission_deadline else None,
                "location": c.location.city if c.location else None,
                "url": str(c.url) if c.url else None,
                "topics": c.topics,
                "core_rank": c.core_rank.value if c.core_rank else None,
                "scores": c.scores.model_dump() if c.scores else None,
                "reason": c.decision.reason if c.decision else None,
            }
            for i, c in enumerate(scored)
        ],
    }


def _check_ollama() -> None:
    """Fail fast with a clear message if Ollama is not reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        console.print(f"\n[bold red][ERROR] Ollama is not running at {OLLAMA_URL}[/bold red]")
        console.print("  Run:  bash scripts/start_ollama.sh\n")
        sys.exit(1)


def main():
    console.print(Panel(
        f"[bold cyan]Pipeline Test[/bold cyan]\n"
        f"Models: [yellow]{', '.join(TEST_MODELS)}[/yellow]  |  Ollama: [yellow]{OLLAMA_URL}[/yellow]\n"
        f"Data:   [yellow]{DATA_FILE.name}[/yellow]  |  Min relevancy: [yellow]{MIN_RELEVANCY}[/yellow]",
        expand=False,
    ))

    _check_ollama()

    # ── Load data ────────────────────────────────────────────────────────────
    all_conferences = load_conferences(DATA_FILE)
    console.print(f"\n[*] Loaded [bold]{len(all_conferences)}[/bold] conferences from {DATA_FILE.name}.")
    conferences = all_conferences[:MAX_CONFERENCES]
    console.print(f"[*] Testing with first [bold]{len(conferences)}[/bold] entries.")
    console.print(f"[*] Running [bold]{len(TEST_PROFILES)}[/bold] research profile(s).\n")

    all_model_results = []
    for model in TEST_MODELS:
        console.rule(f"[bold blue]Model: {model}[/bold blue]")
        model_results = {"model": model, "profiles": []}

        for idx, profile in enumerate(TEST_PROFILES, 1):
            console.rule(f"[bold cyan]Profile {idx} / {len(TEST_PROFILES)} — {model}[/bold cyan]")
            result = run_for_profile(profile, conferences, idx, model=model)
            if result:
                model_results["profiles"].append(result)

        all_model_results.append(model_results)

    # ── Export JSON ──────────────────────────────────────────────────────────
    output = {
        "run_at": datetime.now().isoformat(),
        "models_tested": TEST_MODELS,
        "conferences_tested": len(conferences),
        "min_relevancy_threshold": MIN_RELEVANCY,
        "results_by_model": all_model_results,
    }
    RESULTS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    console.rule()
    console.print(f"\n[✓] Full results saved to [bold]{RESULTS_FILE.name}[/bold]")


if __name__ == "__main__":
    main()
