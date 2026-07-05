#!/usr/bin/env bash
# Run the decision agent + scorer benchmark (6 models x 20 profiles = 120
# runs) in a screen session, since it's long (likely hours, not minutes) --
# see src/benchmark/decision_scoring_benchmark.py for details.
#
# Run from the project root after Ollama is already running with all 6
# models pulled (bash scripts/setup_ollama.sh on the cluster).
# Safe to re-run — the underlying Python script resumes from where it left
# off (skips already-completed model/profile combinations).

set -e

SCREEN_SESSION="decision-benchmark"
PROJECT_DIR="/project/${LOGNAME}/AI_agents_for_science_workflows"
OLLAMA_BIN="/project/${LOGNAME}/ollama/bin/ollama"
LOG_FILE="/tmp/decision_benchmark_${LOGNAME}.log"

REQUIRED_MODELS=(
    "gemma4:e4b"
    "llama3.2"
    "phi4-mini"
    "qwen3:4b"
    "granite4:3b"
    "deepseek-r1:7b"
)

echo "======================================================"
echo " Decision Agent + Scorer Benchmark"
echo " User : ${LOGNAME}"
echo " Zone : $(hostname)"
echo "======================================================"
echo ""

# ── 1. Check Ollama is running ───────────────────────────────────────────────
if ! curl -sf --noproxy localhost http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[ERROR] Ollama is not running. Run: bash scripts/start_ollama.sh"
    exit 1
fi

# ── 2. Check all 6 models are actually pulled ────────────────────────────────
echo "[*] Checking required models are pulled..."
MISSING=()
PULLED_LIST="$(${OLLAMA_BIN} list)"
for model in "${REQUIRED_MODELS[@]}"; do
    if echo "${PULLED_LIST}" | grep -q "^${model}"; then
        echo "  [✓] ${model}"
    else
        echo "  [✗] ${model} — NOT pulled"
        MISSING+=("${model}")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "[ERROR] Missing model(s): ${MISSING[*]}"
    echo "        Run: bash scripts/setup_ollama.sh"
    exit 1
fi

# ── 3. Check the venv exists ─────────────────────────────────────────────────
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
if [ ! -x "${VENV_PYTHON}" ]; then
    echo "[ERROR] ${VENV_PYTHON} not found. Run scripts/setup_env.sh first."
    exit 1
fi

# ── 4. Check for a stale/already-running session ─────────────────────────────
if screen -ls 2>/dev/null | grep -q "${SCREEN_SESSION}"; then
    echo ""
    echo "[!] A '${SCREEN_SESSION}' screen session already exists."
    echo "    Reattach with: screen -r ${SCREEN_SESSION}"
    echo "    (If it's stale/dead, quit it first: screen -S ${SCREEN_SESSION} -X quit)"
    exit 0
fi

# ── 5. Start the benchmark in a screen session ───────────────────────────────
echo ""
echo "[*] Starting benchmark in screen session '${SCREEN_SESSION}'..."
screen -dmS "${SCREEN_SESSION}" bash -c \
    "cd ${PROJECT_DIR} && \
     export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export NO_PROXY='localhost,127.0.0.1'; \
     export TMPDIR=/var/tmp; \
     ${VENV_PYTHON} src/benchmark/decision_scoring_benchmark.py 2>&1 | tee ${LOG_FILE}"

sleep 2
if screen -ls 2>/dev/null | grep -q "${SCREEN_SESSION}"; then
    echo "[✓] Benchmark started."
else
    echo "[ERROR] Screen session did not start. Check ${LOG_FILE}"
    exit 1
fi

echo ""
echo "======================================================"
echo " Benchmark running in the background."
echo ""
echo " This is a long job (likely hours) -- 6 models x 20"
echo " profiles, with the decision agent calling the LLM"
echo " once per conference, sequentially."
echo ""
echo " Watch progress   : tail -f ${LOG_FILE}"
echo " Reattach session : screen -r ${SCREEN_SESSION}"
echo " Detach session   : Ctrl+a d"
echo " Results file     : src/benchmark/decision_scoring_results.json"
echo "                    (updated incrementally after every run --"
echo "                     safe to inspect while the benchmark is still going)"
echo "======================================================"
