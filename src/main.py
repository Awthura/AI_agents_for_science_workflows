"""CLI entry point for the conference recommendation pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .graph import build_graph, make_initial_state
from .schemas.conference import Conference, UserPreferences
from .tools.geocoding import geocode

load_dotenv()
console = Console()

DEFAULT_QUERIES = [
    "machine learning",
    "artificial intelligence",
    "natural language processing",
    "computer vision",
    "data science",
    "deep learning",
]


def collect_user_preferences() -> UserPreferences:
    console.print(Panel("[bold cyan]Conference Recommender[/bold cyan]\nAnswer a few questions to personalise your recommendations.", expand=False))

    address = Prompt.ask("\n[yellow]Your address[/yellow] (home or university)")
    research_title = Prompt.ask("[yellow]Research topic title[/yellow]")
    research_context = Prompt.ask("[yellow]Brief research context[/yellow] (1–3 sentences)")

    coords = geocode(address)
    if not coords:
        console.print("[dim]  Could not geocode address — distance scoring will use neutral values.[/dim]")

    return UserPreferences(
        address=address,
        coordinates=coords,
        research_title=research_title,
        research_context=research_context,
    )


def build_queries(research_title: str, research_context: str) -> list[str]:
    """Derive WikiCFP search queries from the user's research topic."""
    words = (research_title + " " + research_context).lower().split()
    topic_words = [w for w in words if len(w) > 4]
    custom = list(dict.fromkeys(topic_words[:3]))
    return custom + DEFAULT_QUERIES[:max(0, 5 - len(custom))]


def render_results(scored: list[Conference], rejected_count: int) -> None:
    if not scored:
        console.print("\n[bold red]No conferences matched your profile.[/bold red]")
        return

    console.print(f"\n[dim]Rejected {rejected_count} conference(s) as invalid or irrelevant.[/dim]")
    console.print(f"[bold green]Top {min(len(scored), 15)} recommended conferences:[/bold green]\n")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Conference", no_wrap=False)
    table.add_column("Date", width=12)
    table.add_column("Location", width=18)
    table.add_column("CORE", width=5)
    table.add_column("Deadline", width=12)
    table.add_column("Score", width=7, justify="right")

    for i, conf in enumerate(scored[:15], start=1):
        location_str = ""
        if conf.location:
            location_str = f"{conf.location.city}, {conf.location.country}"

        date_str = str(conf.dates.start) if conf.dates.start else ""
        deadline_str = str(conf.dates.submission_deadline) if conf.dates.submission_deadline else ""
        rank_str = conf.core_rank.value if conf.core_rank else "—"
        score_str = f"[bold]{conf.scores.total:.1f}[/bold]" if conf.scores else "—"

        label = f"[bold]{conf.acronym}[/bold] {conf.name}" if conf.acronym else conf.name

        table.add_row(str(i), label, date_str, location_str, rank_str, deadline_str, score_str)

    console.print(table)

    if scored and scored[0].scores:
        top = scored[0]
        console.print(
            f"\n[bold]Best match:[/bold] {top.name}\n"
            f"  Relevancy: {top.scores.relevancy:.0f}  |  "
            f"Distance: {top.scores.distance:.0f}  |  "
            f"Prestige: {top.scores.prestige:.0f}  |  "
            f"Total: {top.scores.total:.1f}"
        )
        if top.decision and top.decision.reason:
            console.print(f"  Reason: [italic]{top.decision.reason}[/italic]")


def main() -> None:
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    console.print(f"[dim]Model: {model}  |  Ollama: {ollama_url}[/dim]")

    user_prefs = collect_user_preferences()
    queries = build_queries(user_prefs.research_title, user_prefs.research_context)

    console.print(f"\n[dim]Search queries: {queries}[/dim]")
    console.print("[yellow]Running pipeline…[/yellow]")

    graph = build_graph()
    initial = make_initial_state(
        user_preferences=user_prefs,
        scrape_queries=queries,
        model_name=model,
        ollama_base_url=ollama_url,
    )

    result = graph.invoke(initial)

    scored = [Conference.model_validate(c) for c in result["scored_conferences"]]
    rejected_count = len(result["rejected_conferences"])
    render_results(scored, rejected_count)


if __name__ == "__main__":
    main()
