# AI Agents for Scientific Workflows

A multi-agent pipeline that recommends academic conferences to researchers.
Given a researcher's location and research topic, the system finds, filters, and scores upcoming conferences to help them decide which to attend.

**Authors:** Till Friedemann, Kilian Schröder, Aw Thura
**Institution:** Otto-von-Guericke-Universität Magdeburg, Faculty of Computer Science

---

## Research Questions

| RQ | Question |
|---|---|
| RQ1 | Which LLM is most compatible for each agent role? |
| RQ2 | How do different models perform on web-scraping and decision-making tasks? |
| RQ3 | How does the system perform with different complex individual preferences? |

---

## System Architecture

```
User Preferences (location + research topic)
        │
        ▼
┌───────────────────┐
│  Data Sources     │  CCF-Deadlines YAML, WikiCFP (scraper), EasyChair (scraper)
└────────┬──────────┘
         │  future_conferences.json
         ▼
┌───────────────────┐
│  Topic Pre-filter │  Keyword-based, no LLM — drops obvious topic mismatches
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Decision Agent   │  Ollama LLM — validates conference + checks relevance
│                   │  (few-shot prompted by default, see Models below)
└────────┬──────────┘
         │  accepted conferences
         ▼
┌───────────────────┐
│  Scoring System   │  Distance (30%) + Relevancy (50%) + Prestige (20%)
└────────┬──────────┘
         │
         ▼
    Ranked Results
```

### Scoring System

Each accepted conference is scored 0–100 on three axes:

| Axis | Method | Weight |
|---|---|---|
| **Relevancy** | LLM semantic match between research topic and conference scope | 50% |
| **Distance** | Haversine distance from researcher's address to conference city, exponential decay | 30% |
| **Prestige** | CORE rank: A*→100, A→80, B→55, C→30, Unranked→10 | 20% |

---

## Project Structure

```
AI_agents_for_science_workflows/
├── app.py                       # Gradio web GUI — primary interface (model dropdown, live log)
├── src/
│   ├── agents/
│   │   ├── decision.py          # Decision agent (LLM-based validation + relevance, few-shot prompted)
│   │   ├── scorer.py            # Scoring system (distance, relevancy, prestige)
│   │   ├── scraper.py           # WikiCFP web-scraping agent
│   │   ├── scraper2.py          # EasyChair web-scraping agent
│   │   └── ccfddl_conferences.py# Converts CCF-Deadlines YAML → JSON
│   ├── benchmark/
│   │   ├── benchmark_pipeline.py          # Extraction benchmark (JSON-parsing accuracy per model)
│   │   ├── decision_scoring_benchmark.py  # Decision/scoring quality benchmark (6 models x 20 profiles)
│   │   ├── decision_scoring_profiles.py   # The 20 synthetic researcher profiles used above
│   │   ├── decision_scoring_rubric.md     # Rubric for judging decision/scoring quality
│   │   └── claude_judgments.md            # Claude-as-judge results + hallucination-mitigation experiments
│   ├── fetcher/
│   │   └── ccf-deadlines_fetcher.py  # Downloads CCF-Deadlines repo from GitHub
│   ├── schemas/
│   │   └── conference.py        # Pydantic models (Conference, UserPreferences, etc.)
│   ├── tools/
│   │   ├── firecrawl_tool.py    # Firecrawl wrapper (WikiCFP, EasyChair, CORE)
│   │   └── geocoding.py         # Address → coordinates + Haversine distance
│   ├── graph.py                 # LangGraph pipeline definition
│   ├── main.py                  # Interactive CLI entry point
│   ├── test_pipeline.py         # End-to-end benchmark test (multi-model, multi-profile)
│   └── test_run.py              # Scraper-based test entry point
├── scripts/
│   ├── setup_ollama.sh          # One-time Ollama install + model pull on cluster
│   ├── setup_env.sh             # Python venv + requirements install on cluster
│   ├── start_ollama.sh          # Start Ollama server in a screen session (pre-loads default model)
│   ├── start_gui.sh             # Start the Gradio GUI in a screen session
│   ├── run_decision_benchmark.sh# Run the decision/scoring benchmark in a screen session
│   └── watch_benchmark.py       # Live tqdm progress bar for a running benchmark
├── docs/
│   └── architecture.md          # Detailed architecture documentation
├── temp/                        # Gitignored — scraped conference cache
├── requirements.txt
└── README.md
```

---

## Setup (OVGU AILab Cluster)

### 1. Clone the repo

```bash
git clone git@github.com:Awthura/AI_agents_for_science_workflows.git
cd AI_agents_for_science_workflows
```

### 2. Install Ollama

```bash
bash scripts/setup_ollama.sh
```

This downloads the Ollama binary to `/project/${LOGNAME}/ollama/`, sets up env vars in `~/.bashrc`, and pulls the default models (see Models below).

### 3. Set up Python environment

```bash
bash scripts/setup_env.sh
source venv/bin/activate
```

### 4. Start Ollama (every session)

```bash
bash scripts/start_ollama.sh
```

### 5. Start the web GUI (every session)

```bash
bash scripts/start_gui.sh
```

Access at `http://<zone>:7860` (via SSH tunnel — see `docs/architecture.md`
for the tunnel command). Pick a model from the dropdown, enter an address
and research topic, and click **Run pipeline**. The dropdown shows a green
"ready" mark next to whichever model Ollama currently has loaded in memory.

---

## Running the Pipeline

### Web GUI (recommended)

```bash
python app.py           # full pipeline, requires Ollama running
python app.py --demo     # demo mode with fake data, no Ollama needed
```

### Fetch conference data

```bash
python src/fetcher/ccf-deadlines_fetcher.py   # download YAML from CCF-Deadlines GitHub
python src/agents/ccfddl_conferences.py        # convert YAML → future_conferences.json
```

### Run benchmark test (multi-model, multi-profile)

```bash
screen -S pipeline
python src/test_pipeline.py
```

Runs all profiles defined in `TEST_PROFILES` against all models in `TEST_MODELS` and saves results to `pipeline_results.json`.

### Run interactive CLI

```bash
python src/main.py
```

Prompts for location and research topic, then runs the full pipeline and prints a ranked table.

---

## Data Sources

| Source | Method | Status |
|---|---|---|
| **CCF-Deadlines** | GitHub YAML download (no scraping) | Working on cluster |
| **WikiCFP** | Firecrawl scraping | Blocked by cluster proxy |
| **EasyChair** | Firecrawl scraping | Blocked by cluster proxy |

> The CCF-Deadlines source is the primary data source for cluster runs.
> Scraping-based sources work locally when Firecrawl is running.

---

## Models

All 6 models are served locally via Ollama on the cluster (`scripts/setup_ollama.sh` pulls all of them):

| Model | Notes |
|---|---|
| `gemma4:e4b` | Default / pre-loaded. Best performer on both the extraction benchmark (73/100) and the decision/scoring benchmark (see `src/benchmark/claude_judgments.md`) |
| `llama3.2` | |
| `phi4-mini` | |
| `qwen3:4b` | Tied for best decision/scoring accuracy with gemma4:e4b |
| `granite4:3b` | |
| `deepseek-r1:7b` | Reasoning model — currently has a parse-failure issue under some configurations (see `claude_judgments.md`), needs a clean re-run to confirm the fix |

Only one model is kept loaded in Ollama's memory at a time
(`OLLAMA_MAX_LOADED_MODELS=1`, set by `scripts/start_ollama.sh`) — switching
models in the GUI dropdown evicts the previous one automatically. Loading
only happens lazily on "Run pipeline" click, not on dropdown change.

For CLI use, switch model via environment variable:
```bash
OLLAMA_MODEL=qwen3:4b python src/test_pipeline.py
```

### Decision agent prompting

The decision agent (`src/agents/decision.py`) uses **few-shot prompting** by
default in the live pipeline — 4 worked examples in the system prompt that
improved accuracy and reasoning quality for every one of the 5 benchmarked
models (`deepseek-r1:7b` excluded, see note above), at no added latency
(see `src/benchmark/claude_judgments.md`'s "Few-Shot Prompting Experiment"
for the full write-up, including a head-to-head comparison against a
self-validation approach that was tried first and found to be net-negative
for most models).

---

## Dependencies

See `requirements.txt`. Key packages:

- `langgraph` — agent orchestration
- `langchain-ollama` — Ollama LLM integration
- `firecrawl-py` — web scraping
- `geopy` — address geocoding
- `pydantic` — data validation
- `rich` — terminal output
- `gradio` — web GUI
- `tqdm` — benchmark progress bars
