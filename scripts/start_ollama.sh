#!/usr/bin/env bash
# Start the Ollama server on the OVGU AILab cluster.
# Run this every time you SSH in and need the server running.
# Safe to re-run — skips startup if already running.

set -e

OLLAMA_BIN="/project/${LOGNAME}/ollama/bin/ollama"
OLLAMA_MODELS="/project/${LOGNAME}/ollama/models"
SCREEN_SESSION="ollama"
# Empirically the best performer in the team's extraction benchmark (73/100,
# see src/benchmark/benchmark_4_with_score) — pre-loaded so it's ready before
# the first real request. OLLAMA_MAX_LOADED_MODELS=1 (below) means loading
# any other model automatically evicts this one; nothing extra to manage.
DEFAULT_MODEL="gemma4:e4b"

echo "======================================================"
echo " Ollama Start — OVGU AILab Cluster"
echo " User : ${LOGNAME}"
echo " Zone : $(hostname)"
echo "======================================================"
echo ""

# ── 1. Check binary exists ───────────────────────────────────────────────────
if [ ! -f "${OLLAMA_BIN}" ]; then
    echo "[ERROR] Ollama binary not found at ${OLLAMA_BIN}."
    echo "        Run ./scripts/setup_ollama.sh first."
    exit 1
fi

# ── 2. Check if already running ─────────────────────────────────────────────
if curl -sf --noproxy localhost http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[✓] Ollama is already running on port 11434."
    echo ""
    echo "    To reattach to the screen session: screen -r ${SCREEN_SESSION}"
    echo "    To list running models:            ${OLLAMA_BIN} list"
    exit 0
fi

# ── 3. Check if screen session already exists ────────────────────────────────
if screen -ls 2>/dev/null | grep -q "${SCREEN_SESSION}"; then
    echo "[!] Screen session '${SCREEN_SESSION}' exists but Ollama is not responding."
    echo "    Killing stale session and restarting..."
    screen -S "${SCREEN_SESSION}" -X quit 2>/dev/null || true
    sleep 2
fi

# ── 4. Set env vars ──────────────────────────────────────────────────────────
export OLLAMA_MODELS="${OLLAMA_MODELS}"
export OLLAMA_MAX_LOADED_MODELS=1
export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'
export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'
export NO_PROXY='localhost,127.0.0.1'
export TMPDIR=/var/tmp

# ── 5. Start Ollama in a screen session ──────────────────────────────────────
echo "[*] Starting Ollama in screen session '${SCREEN_SESSION}'..."
screen -dmS "${SCREEN_SESSION}" bash -c \
    "export OLLAMA_MODELS=${OLLAMA_MODELS}; \
     export OLLAMA_MAX_LOADED_MODELS=1; \
     export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export TMPDIR=/var/tmp; \
     ${OLLAMA_BIN} serve"

# ── 6. Wait for server to be ready ──────────────────────────────────────────
echo "[*] Waiting for Ollama to become ready..."
for i in $(seq 1 30); do
    if curl -sf --noproxy localhost http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[✓] Ollama is running on http://localhost:11434"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[ERROR] Ollama did not start in time."
        echo "        Check the screen session: screen -r ${SCREEN_SESSION}"
        exit 1
    fi
    sleep 2
done

# ── 7. Warm up the default model ─────────────────────────────────────────────
echo ""
echo "[*] Pre-loading default model (${DEFAULT_MODEL})..."
if curl -sf --noproxy localhost -X POST http://localhost:11434/api/generate \
    -d "{\"model\": \"${DEFAULT_MODEL}\", \"keep_alive\": -1}" > /dev/null 2>&1; then
    echo "[✓] ${DEFAULT_MODEL} is loaded and will stay resident until a different"
    echo "    model is requested (OLLAMA_MAX_LOADED_MODELS=1 evicts it then)."
else
    echo "[!] Could not pre-load ${DEFAULT_MODEL} — is it pulled? Run scripts/setup_ollama.sh."
fi

# ── 8. Show available models ─────────────────────────────────────────────────
echo ""
echo "[i] Available models:"
"${OLLAMA_BIN}" list

echo ""
echo "======================================================"
echo " Ollama is ready."
echo ""
echo " Reattach session : screen -r ${SCREEN_SESSION}"
echo " Detach session   : Ctrl+a d"
echo " API endpoint     : http://localhost:11434"
echo "======================================================"
