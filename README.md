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
├── src/
│   ├── agents/
│   │   ├── decision.py          # Decision agent (LLM-based validation + relevance)
│   │   ├── scorer.py            # Scoring system (distance, relevancy, prestige)
│   │   ├── scraper.py           # WikiCFP web-scraping agent
│   │   ├── scraper2.py          # EasyChair web-scraping agent
│   │   └── ccfddl_conferences.py# Converts CCF-Deadlines YAML → JSON
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
│   ├── setup_ollama.sh          # One-time Ollama install on cluster
│   ├── setup_env.sh             # Python venv + requirements install on cluster
│   └── start_ollama.sh          # Start Ollama server in a screen session
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

This downloads the Ollama binary to `/project/${LOGNAME}/ollama/`, sets up env vars in `~/.bashrc`, and pulls the default models (`llama3.2`, `gemma2:9b`).

### 3. Set up Python environment

```bash
bash scripts/setup_env.sh
source venv/bin/activate
```

### 4. Start Ollama (every session)

```bash
bash scripts/start_ollama.sh
```

---

## Running the Pipeline

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

Both models are served locally via Ollama on the cluster:

| Model | Role | Notes |
|---|---|---|
| `llama3.2` | Decision agent + scorer | Conservative, high precision |
| `gemma2:9b` | Decision agent + scorer | Liberal, high recall |

Switch model via environment variable:
```bash
OLLAMA_MODEL=gemma2:9b python src/test_pipeline.py
```

---

## Dependencies

See `requirements.txt`. Key packages:

- `langgraph` — agent orchestration
- `langchain-ollama` — Ollama LLM integration
- `firecrawl-py` — web scraping
- `geopy` — address geocoding
- `pydantic` — data validation
- `rich` — terminal output
