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

MAX_CONFERENCES = 20  # limit to keep test duration reasonable


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
            )
            conferences.append(conf)
        except Exception:
            continue

    return conferences


def run_for_profile(profile: UserPreferences, conferences: list[Conference], idx: int) -> dict:
    console.print(Panel(
        f"[bold]Profile {idx} — {profile.research_title}[/bold]\n"
        f"Location: {profile.address}\n"
        f"Context:  {profile.research_context}",
        expand=False,
    ))

    # ── Decision agent ───────────────────────────────────────────────────────
    console.print("\n[yellow][1/2] Running decision agent...[/yellow]")
    accepted, rejected = run_decision_agent(
        conferences, profile, OLLAMA_MODEL, OLLAMA_URL
    )
    console.print(f"  [✓] Accepted: [green]{len(accepted)}[/green]  |  Rejected: [red]{len(rejected)}[/red]")

    if not accepted:
        console.print("[red]  No conferences passed the decision agent.[/red]\n")
        return {"profile": profile.research_title, "accepted": 0, "results": []}

    # ── Scorer ───────────────────────────────────────────────────────────────
    console.print("\n[yellow][2/2] Scoring accepted conferences...[/yellow]")
    scored = run_scorer(accepted, profile, OLLAMA_MODEL, OLLAMA_URL)
    console.print(f"  [✓] Scored {len(scored)} conference(s).")

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
        "location": profile.address,
        "accepted": len(accepted),
        "rejected": len(rejected),
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


def main():
    console.print(Panel(
        f"[bold cyan]Pipeline Test[/bold cyan]\n"
        f"Model: [yellow]{OLLAMA_MODEL}[/yellow]  |  Ollama: [yellow]{OLLAMA_URL}[/yellow]\n"
        f"Data:  [yellow]{DATA_FILE.name}[/yellow]",
        expand=False,
    ))

    # ── Load data ────────────────────────────────────────────────────────────
    all_conferences = load_conferences(DATA_FILE)
    console.print(f"\n[*] Loaded [bold]{len(all_conferences)}[/bold] conferences from {DATA_FILE.name}.")
    conferences = all_conferences[:MAX_CONFERENCES]
    console.print(f"[*] Testing with first [bold]{len(conferences)}[/bold] entries.")
    console.print(f"[*] Running [bold]{len(TEST_PROFILES)}[/bold] research profile(s).\n")

    all_results = []
    for idx, profile in enumerate(TEST_PROFILES, 1):
        console.rule(f"[bold cyan]Profile {idx} / {len(TEST_PROFILES)}[/bold cyan]")
        result = run_for_profile(profile, conferences, idx)
        if result:
            all_results.append(result)

    # ── Export JSON ──────────────────────────────────────────────────────────
    output = {
        "run_at": datetime.now().isoformat(),
        "model": OLLAMA_MODEL,
        "conferences_tested": len(conferences),
        "profiles": all_results,
    }
    RESULTS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    console.rule()
    console.print(f"\n[✓] Full results saved to [bold]{RESULTS_FILE.name}[/bold]")


if __name__ == "__main__":
    main()
