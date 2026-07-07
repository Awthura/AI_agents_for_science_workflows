"""Gradio web GUI for the conference recommendation pipeline.

Run from the project root:
    python app.py           # full pipeline (requires Ollama on cluster)
    python app.py --demo    # demo mode with fake data (no Ollama needed)

Accessible at http://localhost:7860 (or http://<zone-ip>:7860 within OVGU network).
"""

from __future__ import annotations

import io
import json
import os
import queue
import sys
import threading
import time
import urllib.request
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

DEMO_MODE = "--demo" in sys.argv

load_dotenv()

# src/ modules use flat imports internally (e.g. `from schemas.conference import
# ...`), not package-relative ones, so src/ itself — not its parent — must be on
# sys.path. Importing via `src.xxx` here as well would load a second, distinct
# copy of each module (e.g. two different `Coordinates` classes with the same
# name), which fails Pydantic's isinstance-based validation despite looking
# identical.
_SRC = Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if not DEMO_MODE:
    from graph import build_graph, make_initial_state  # noqa: E402
    from main import build_queries  # noqa: E402
    from schemas.conference import Conference, UserPreferences  # noqa: E402
    from tools.geocoding import geocode  # noqa: E402

# Selected from the project's own extraction benchmark (src/benchmark/*) plus
# current small models under the project's 8B-parameter research scope.
# gemma4:e4b is the empirically best performer (73/100 vs runner-up llama3.2
# at 59/100) and is what scripts/start_ollama.sh pre-loads by default.
AVAILABLE_MODELS = [
    "gemma4:e4b",
    "llama3.2",
    "phi4-mini",
    "qwen3:4b",
    "granite4:3b",
    "deepseek-r1:7b",
]
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def _get_loaded_models(ollama_url: str) -> set[str]:
    """Query Ollama's /api/ps for currently loaded models — used to show a
    green ready-indicator in the model dropdown. Returns an empty set (no
    indicator shown) if Ollama isn't reachable, rather than raising."""
    try:
        req = urllib.request.Request(f"{ollama_url.rstrip('/')}/api/ps")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
        return {m["name"] for m in data.get("models", [])}
    except Exception:
        return set()


def _model_choices(ollama_url: str) -> list[tuple[str, str]]:
    """Dropdown (label, value) pairs — label gets a green ready-mark for
    whichever model Ollama currently has loaded. The underlying value stays
    the plain model name regardless of label, so nothing else needs to know
    about the indicator."""
    loaded = _get_loaded_models(ollama_url)
    return [(f"{m}  \U0001f7e2 ready" if m in loaded else m, m) for m in AVAILABLE_MODELS]

_DEMO_ROWS = [
    [1, "ICML - International Conference on Machine Learning", "2026-07-13", "Vienna, Austria", "A*", "2026-02-06", "94.2", "Strong match: deep learning focus, close location."],
    [2, "NeurIPS - Neural Information Processing Systems", "2026-12-07", "Vancouver, Canada", "A*", "2026-05-15", "89.5", "Top-tier venue, highly relevant research scope."],
    [3, "ICLR - International Conference on Learning Representations", "2026-05-02", "Singapore", "A*", "2026-10-01", "86.1", "Core venue for representation learning work."],
    [4, "ECML PKDD - European Conference on Machine Learning", "2026-09-14", "Berlin, Germany", "A", "2026-03-20", "81.7", "Good relevancy, short travel distance from Magdeburg."],
    [5, "ACML - Asian Conference on Machine Learning", "2026-11-20", "Tokyo, Japan", "A", "2026-06-01", "74.3", "Relevant topics, lower score due to distance."],
]


class _LogCapture(io.TextIOBase):
    """Redirects print() output into a thread-safe queue."""

    def __init__(self, q: queue.Queue) -> None:
        self._q = q

    def write(self, s: str) -> int:
        if s and s.strip():
            self._q.put(s.rstrip())
        return len(s)

    def flush(self) -> None:
        pass


def _run_pipeline(
    address: str,
    research_title: str,
    research_context: str,
    model: str,
    ollama_url: str,
) -> tuple[list[Conference], int] | Exception:
    coords = geocode(address)
    prefs = UserPreferences(
        address=address,
        coordinates=coords,
        research_title=research_title,
        research_context=research_context,
    )
    queries = build_queries(research_title, research_context)
    graph = build_graph()
    initial = make_initial_state(
        user_preferences=prefs,
        scrape_queries=queries,
        model_name=model,
        ollama_base_url=ollama_url,
    )
    result = graph.invoke(initial)
    scored = [Conference.model_validate(c) for c in result.get("scored_conferences", [])]
    rejected_count = len(result.get("rejected_conferences", []))
    return scored, rejected_count


def _build_table(scored: list[Conference], rejected_count: int) -> list[list]:
    rows = []
    for i, conf in enumerate(scored[:20], 1):
        location = ""
        if conf.location:
            location = f"{conf.location.city}, {conf.location.country}"
        rows.append([
            i,
            f"{conf.acronym} - {conf.name}" if conf.acronym else conf.name,
            str(conf.dates.start) if conf.dates.start else "-",
            location or "-",
            conf.core_rank.value if conf.core_rank else "-",
            str(conf.dates.submission_deadline) if conf.dates.submission_deadline else "-",
            f"{conf.scores.total:.1f}" if conf.scores else "-",
            conf.decision.reason if conf.decision else "",
        ])
    return rows


def recommend(
    address: str,
    research_title: str,
    research_context: str,
    model: str,
    ollama_url: str,
):
    if not address.strip() or not research_title.strip() or not research_context.strip():
        yield "Please fill in all required fields.", []
        return

    if DEMO_MODE:
        yield "[DEMO MODE] Geocoding address...", []
        time.sleep(0.6)
        yield "[DEMO MODE] Geocoding address...\n[DEMO MODE] Scraping conference listings...", []
        time.sleep(0.8)
        yield "[DEMO MODE] Geocoding address...\n[DEMO MODE] Scraping conference listings...\n[DEMO MODE] Running decision agent (validate + relevance)...", []
        time.sleep(0.8)
        yield (
            "[DEMO MODE] Geocoding address...\n"
            "[DEMO MODE] Scraping conference listings...\n"
            "[DEMO MODE] Running decision agent (validate + relevance)...\n"
            "[DEMO MODE] Scoring conferences...\n\n"
            f"Done: 5 recommended, 3 rejected.\n"
            f"Top match: ICML 2026  |  Score: 94.2",
            _DEMO_ROWS,
        )
        return

    log_queue: queue.Queue = queue.Queue()
    result_holder: dict = {}

    def worker() -> None:
        old_stdout = sys.stdout
        sys.stdout = _LogCapture(log_queue)
        try:
            scored, rejected = _run_pipeline(
                address, research_title, research_context, model, ollama_url
            )
            result_holder["scored"] = scored
            result_holder["rejected"] = rejected
        except Exception as exc:
            result_holder["error"] = str(exc)
        finally:
            sys.stdout = old_stdout
            log_queue.put(None)  # sentinel

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    log_lines: list[str] = ["Pipeline started..."]
    yield "\n".join(log_lines), []

    while True:
        try:
            msg = log_queue.get(timeout=0.3)
            if msg is None:
                break
            log_lines.append(msg)
            yield "\n".join(log_lines), []
        except queue.Empty:
            if not thread.is_alive():
                break
            yield "\n".join(log_lines), []

    thread.join()

    if "error" in result_holder:
        log_lines.append(f"\nError: {result_holder['error']}")
        yield "\n".join(log_lines), []
        return

    scored = result_holder.get("scored", [])
    rejected = result_holder.get("rejected", 0)

    if not scored:
        log_lines.append("\nNo conferences matched your profile.")
        yield "\n".join(log_lines), []
        return

    log_lines.append(
        f"\nDone: {len(scored)} recommended, {rejected} rejected."
    )
    yield "\n".join(log_lines), _build_table(scored, rejected)


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="Conference Recommender") as demo:

    gr.Markdown(
        """
# Conference Recommender
*AI Agents for Scientific Workflows - Advanced Topics in Deep Learning*

Enter your details below and click **Run** to get a personalised list of upcoming conferences.
        """
    )

    if DEMO_MODE:
        gr.Markdown(
            "> **Demo mode:** pipeline is simulated with example data. "
            "No Ollama or cluster connection required."
        )

    with gr.Row():
        address_box = gr.Textbox(
            label="Your address",
            placeholder="e.g. Universitätsplatz 2, Magdeburg, Germany",
            scale=3,
        )
        model_drop = gr.Dropdown(
            choices=_model_choices(DEFAULT_OLLAMA_URL) if not DEMO_MODE else AVAILABLE_MODELS,
            value=AVAILABLE_MODELS[0],
            label="Ollama model",
            scale=1,
        )

    with gr.Row():
        title_box = gr.Textbox(
            label="Research topic title",
            placeholder="e.g. Efficient Transformers for Low-Resource NLP",
            scale=2,
        )
        context_box = gr.Textbox(
            label="Brief research context (1-3 sentences)",
            placeholder="Describe your research focus...",
            lines=3,
            scale=3,
        )

    with gr.Accordion("Advanced settings", open=False):
        ollama_url_box = gr.Textbox(
            label="Ollama base URL",
            value=DEFAULT_OLLAMA_URL,
        )

    run_btn = gr.Button("Run pipeline", variant="primary")

    with gr.Accordion("Pipeline log", open=False):
        log_box = gr.Textbox(
            label="",
            lines=12,
            interactive=False,
        )

    gr.Markdown("### Results")
    results_table = gr.Dataframe(
        headers=["#", "Conference", "Date", "Location", "CORE", "Deadline", "Score", "Reason"],
        datatype=["number", "str", "str", "str", "str", "str", "str", "str"],
        interactive=False,
        wrap=True,
    )

    run_btn.click(
        fn=recommend,
        inputs=[address_box, title_box, context_box, model_drop, ollama_url_box],
        outputs=[log_box, results_table],
    )

    if not DEMO_MODE:
        # Refresh the green ready-mark periodically. Loading a model only
        # happens lazily when "Run pipeline" is clicked (not on dropdown
        # change), so this just reflects whatever Ollama currently has
        # resident — including models loaded by other users' runs.
        # Interval kept fairly long (not e.g. 5s) because each tick is a
        # round-trip over an SSH tunnel with no keepalive configured on the
        # client side — a tighter interval just means more chances for a
        # transient tunnel blip to surface as a "could not parse server
        # response" toast in the browser. The indicator doesn't need to be
        # second-fresh, so this trades a little staleness for far fewer
        # spurious error popups.
        model_status_timer = gr.Timer(25)
        model_status_timer.tick(
            fn=lambda url: gr.update(choices=_model_choices(url)),
            inputs=[ollama_url_box],
            outputs=[model_drop],
        )

if __name__ == "__main__":
    # Access via SSH tunnel, not the jhub.cs.ovgu.de Apache proxy: that proxy
    # applies a hardcoded 30-day cache to this route regardless of our own
    # Cache-Control headers, serving stale snapshots indefinitely — an Apache
    # config issue outside our control (see cluster_setup.md for the tunnel
    # command). No path mounting or proxy-scheme workarounds needed here.
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )
