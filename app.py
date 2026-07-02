"""Gradio web GUI for the conference recommendation pipeline.

Run from the project root:
    python app.py           # full pipeline (requires Ollama on cluster)
    python app.py --demo    # demo mode with fake data (no Ollama needed)

Accessible at http://localhost:7860 (or http://<zone-ip>:7860 within OVGU network).
"""

from __future__ import annotations

import io
import os
import queue
import sys
import threading
import time
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

DEMO_MODE = "--demo" in sys.argv

load_dotenv()

# Allow both package-style imports (src.graph) and flat imports used inside agents
_ROOT = Path(__file__).parent
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if not DEMO_MODE:
    from src.graph import build_graph, make_initial_state  # noqa: E402
    from src.main import build_queries  # noqa: E402
    from src.schemas.conference import Conference, UserPreferences  # noqa: E402
    from src.tools.geocoding import geocode  # noqa: E402

AVAILABLE_MODELS = ["llama3.2", "gemma2:9b"]
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

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
            choices=AVAILABLE_MODELS,
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

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    # Apache forwards the full "/aafsw/..." path unchanged rather than stripping
    # the prefix before proxying (confirmed via direct netcat test to the
    # backend). Gradio's `root_path` alone only affects generated URLs — it
    # doesn't register routes — so the app must actually be mounted at that
    # path for incoming requests to match.
    #
    # root_path must be the relative path ("/aafsw"), not an absolute URL:
    # passing an absolute URL here breaks route matching entirely (every
    # request 404s), since it's compared against incoming request paths,
    # which never include a scheme/host. Verified via local repro against
    # this exact Gradio version (6.19.0).
    fastapi_app = FastAPI()
    gr.mount_gradio_app(
        fastapi_app,
        demo.queue(),
        path="/aafsw",
        root_path="/aafsw",
        show_error=True,
    )

    # Apache doesn't send X-Forwarded-Proto, so Gradio infers "http" (the
    # scheme of the plain-HTTP connection Apache forwards internally) and
    # generates mixed-content asset/websocket URLs that browsers block on
    # this HTTPS-only deployment. Force the scheme since it's always HTTPS
    # externally on this proxy.
    @fastapi_app.middleware("http")
    async def _force_https_scheme(request, call_next):
        request.scope["scheme"] = "https"
        response = await call_next(request)
        # Apache's proxy appears to cache responses for up to 30 days by path
        # alone (ignoring query strings) — explicitly forbid caching so a
        # stale snapshot (e.g. captured mid-deploy with wrong config) can't
        # get served indefinitely regardless of what we ship afterward.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response
    uvicorn.run(fastapi_app, host="0.0.0.0", port=7860)
