#!/usr/bin/env bash
# Start the Gradio web GUI on the OVGU AILab cluster.
# Run from the project root after Ollama is already running.
# Safe to re-run — skips startup if already running.

set -e

SCREEN_SESSION="gradio-gui"
GUI_PORT=7860
PROJECT_DIR="/project/${LOGNAME}/AI_agents_for_science_workflows"

echo "======================================================"
echo " Conference Recommender GUI — OVGU AILab Cluster"
echo " User : ${LOGNAME}"
echo " Zone : $(hostname)"
echo "======================================================"
echo ""

# ── 1. Locate project directory ──────────────────────────────────────────────
if [ ! -f "${PROJECT_DIR}/app.py" ]; then
    echo "[ERROR] app.py not found in ${PROJECT_DIR}"
    echo "        Make sure the project is cloned there."
    exit 1
fi

# ── 2. Check if already running ─────────────────────────────────────────────
if curl -sf --noproxy localhost http://localhost:${GUI_PORT}/ > /dev/null 2>&1; then
    echo "[✓] GUI is already running on port ${GUI_PORT}."
    echo ""
    echo "    Access from OVGU network: http://$(hostname):${GUI_PORT}"
    echo "    Reattach screen session:  screen -r ${SCREEN_SESSION}"
    exit 0
fi

# ── 3. Kill stale screen session if it exists ────────────────────────────────
if screen -ls 2>/dev/null | grep -q "${SCREEN_SESSION}"; then
    echo "[!] Stale screen session found — killing and restarting..."
    screen -S "${SCREEN_SESSION}" -X quit 2>/dev/null || true
    sleep 2
fi

# ── 4. Set env vars ──────────────────────────────────────────────────────────
export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'
export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'
export NO_PROXY='localhost,127.0.0.1'
export TMPDIR=/var/tmp

# ── 5. Start Gradio in a screen session ──────────────────────────────────────
# Use the venv's python explicitly — screen -dmS spawns a fresh shell that
# does NOT inherit venv activation from the calling shell, even if you
# `source venv/bin/activate`d before running this script.
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
if [ ! -x "${VENV_PYTHON}" ]; then
    echo "[ERROR] ${VENV_PYTHON} not found. Run scripts/setup_env.sh first."
    exit 1
fi

echo "[*] Starting Gradio GUI in screen session '${SCREEN_SESSION}'..."
screen -dmS "${SCREEN_SESSION}" bash -c \
    "cd ${PROJECT_DIR} && \
     export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export NO_PROXY='localhost,127.0.0.1'; \
     export TMPDIR=/var/tmp; \
     export OLLAMA_BASE_URL='http://localhost:11434'; \
     ${VENV_PYTHON} app.py 2>&1 | tee /tmp/gradio.log"

# ── 6. Wait for GUI to be ready ──────────────────────────────────────────────
echo "[*] Waiting for GUI to become ready..."
for i in $(seq 1 30); do
    if curl -sf --noproxy localhost http://localhost:${GUI_PORT}/ > /dev/null 2>&1; then
        echo "[✓] GUI is running."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[ERROR] GUI did not start in time."
        echo "        Check logs:           cat /tmp/gradio.log"
        echo "        Check screen session: screen -r ${SCREEN_SESSION}"
        exit 1
    fi
    sleep 2
done

echo ""
echo "======================================================"
echo " GUI is ready."
echo ""
echo " Access from OVGU network: http://$(hostname):${GUI_PORT}"
echo ""
echo " Reattach session : screen -r ${SCREEN_SESSION}"
echo " View logs        : cat /tmp/gradio.log"
echo " Detach session   : Ctrl+a d"
echo "======================================================"
