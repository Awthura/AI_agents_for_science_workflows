#!/usr/bin/env bash
# Start a public Cloudflare Tunnel to the Gradio GUI, bypassing the
# jhub.cs.ovgu.de Apache proxy entirely (see cluster_setup.md for why that
# proxy currently caches this route for 30 days regardless of origin headers).
# Run from the project root after scripts/start_gui.sh is already running.
# Safe to re-run — skips download if already installed.

set -e

SCREEN_SESSION="cloudflared-tunnel"
GUI_PORT=7860
PROJECT_DIR="/project/${LOGNAME}/AI_agents_for_science_workflows"
CLOUDFLARED_BIN="${PROJECT_DIR}/bin/cloudflared"
CLOUDFLARED_DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
LOG_FILE="/tmp/cloudflared_${LOGNAME}.log"

echo "======================================================"
echo " Public Tunnel (Cloudflare) — Conference Recommender"
echo " User : ${LOGNAME}"
echo " Zone : $(hostname)"
echo "======================================================"
echo ""

# ── 1. Download cloudflared if missing ──────────────────────────────────────
if [ ! -x "${CLOUDFLARED_BIN}" ]; then
    echo "[*] cloudflared not found. Downloading..."
    mkdir -p "$(dirname "${CLOUDFLARED_BIN}")"
    export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'
    export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'
    curl -L "${CLOUDFLARED_DOWNLOAD_URL}" -o "${CLOUDFLARED_BIN}"
    SIZE=$(stat -c%s "${CLOUDFLARED_BIN}" 2>/dev/null || echo 0)
    if [ "${SIZE}" -lt 1000000 ]; then
        echo "[ERROR] Download too small (${SIZE} bytes, expected >10MB) — got: $(head -c 200 "${CLOUDFLARED_BIN}")"
        rm -f "${CLOUDFLARED_BIN}"
        exit 1
    fi
    chmod +x "${CLOUDFLARED_BIN}"
    echo "[✓] cloudflared downloaded."
else
    echo "[✓] cloudflared already installed at ${CLOUDFLARED_BIN}."
fi

# ── 2. Check the GUI is actually running first ──────────────────────────────
if ! curl -sf --noproxy localhost "http://localhost:${GUI_PORT}/" > /dev/null 2>&1; then
    echo "[ERROR] Gradio GUI is not running on port ${GUI_PORT}. Run scripts/start_gui.sh first."
    exit 1
fi

# ── 3. Kill stale screen session if it exists ───────────────────────────────
if screen -ls 2>/dev/null | grep -q "${SCREEN_SESSION}"; then
    echo "[!] Stale tunnel session found — killing and restarting..."
    screen -S "${SCREEN_SESSION}" -X quit 2>/dev/null || true
    sleep 2
fi

# ── 4. Start the tunnel in a screen session ─────────────────────────────────
echo "[*] Starting Cloudflare Tunnel in screen session '${SCREEN_SESSION}'..."
rm -f "${LOG_FILE}"
screen -dmS "${SCREEN_SESSION}" bash -c \
    "export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'; \
     export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'; \
     ${CLOUDFLARED_BIN} tunnel --url http://localhost:${GUI_PORT} 2>&1 | tee ${LOG_FILE}"

# ── 5. Wait for the public URL to appear in the log ─────────────────────────
echo "[*] Waiting for public URL..."
for i in $(seq 1 30); do
    URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "${LOG_FILE}" 2>/dev/null | head -1)
    if [ -n "${URL}" ]; then
        echo ""
        echo "======================================================"
        echo " Tunnel is live!"
        echo ""
        echo " Public URL: ${URL}"
        echo ""
        echo " Note: this URL changes every time the tunnel restarts."
        echo " Reattach session : screen -r ${SCREEN_SESSION}"
        echo " View logs        : cat ${LOG_FILE}"
        echo "======================================================"
        exit 0
    fi
    sleep 2
done

echo "[ERROR] Tunnel did not report a URL in time."
echo "        Check logs: cat ${LOG_FILE}"
exit 1
