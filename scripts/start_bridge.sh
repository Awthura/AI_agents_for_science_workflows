#!/usr/bin/env bash
# Bridge script: brings the public demo online at klar-learn.dev/aafsw and
# takes it back offline when stopped.
#
# Run this from your local machine (not the cluster) — it keeps two things
# alive while it runs:
#   1. An SSH tunnel forwarding this machine's localhost:7860 to n05-07:7860
#      (the Gradio app running on the OVGU cluster — see scripts/start_gui.sh)
#   2. A Cloudflare quick tunnel exposing that local port publicly
#
# It writes the resulting public URL into the klar repo's
# public/aafsw-status.json and pushes it, so klar-learn.dev/aafsw redirects
# visitors there. On exit (Ctrl+C or any termination), it kills both
# processes and flips the status file back to offline, so the page stops
# pointing at a dead link.
#
# This script lives in this repo (not the klar repo) because it's this
# project's demo infrastructure; it just happens to publish its status to
# a page hosted in a different repo.
#
# Requires your OVGU cluster password interactively (for the SSH gateway
# hop) — meant to be run manually in a terminal you keep open, not as a
# background daemon.

KLAR_REPO_DIR="/Users/awthura/personal/dsag"
STATUS_FILE="${KLAR_REPO_DIR}/public/aafsw-status.json"
GUI_PORT=7860
GATEWAY_USER="awthura"
GATEWAY_HOST="fcm.cs.ovgu.de"
ZONE_HOST="n05-07"
CLOUDFLARED_LOG="/tmp/aafsw_bridge_cloudflared.log"

SSH_PID=""
CLOUDFLARED_PID=""
CLEANED_UP=0

write_status() {
    local online="$1"
    local url="$2"
    if [ -n "${url}" ]; then
        url_json="\"${url}\""
    else
        url_json="null"
    fi
    cat > "${STATUS_FILE}" << EOF
{
  "online": ${online},
  "url": ${url_json},
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

publish_status() {
    ( cd "${KLAR_REPO_DIR}" && \
      if ! git diff --quiet -- public/aafsw-status.json 2>/dev/null; then
          git add public/aafsw-status.json && \
          git commit -m "aafsw bridge: $1" --quiet && \
          git push --quiet && \
          echo "[*] Status published: $1"
      fi
    ) || echo "[!] Failed to publish status ($1) — check git manually."
}

cleanup() {
    if [ "${CLEANED_UP}" -eq 1 ]; then
        return
    fi
    CLEANED_UP=1
    echo ""
    echo "[*] Shutting down bridge..."
    [ -n "${CLOUDFLARED_PID}" ] && kill "${CLOUDFLARED_PID}" 2>/dev/null
    [ -n "${SSH_PID}" ] && kill "${SSH_PID}" 2>/dev/null
    write_status "false" ""
    publish_status "demo offline"
    echo "[✓] Bridge stopped. Demo is offline."
}
trap cleanup INT TERM EXIT

echo "======================================================"
echo " AAFSW Demo Bridge"
echo "======================================================"
echo ""

# ── 0. Check the klar repo is where we expect ────────────────────────────────
if [ ! -f "${KLAR_REPO_DIR}/public/aafsw-status.json" ]; then
    echo "[ERROR] ${KLAR_REPO_DIR} doesn't look like the klar repo (no public/aafsw-status.json)."
    echo "        Update KLAR_REPO_DIR at the top of this script if it moved."
    exit 1
fi

# ── 1. Start SSH tunnel ──────────────────────────────────────────────────────
if lsof -i ":${GUI_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[!] Something is already listening on port ${GUI_PORT}."
    echo "    Kill it first, or this bridge may end up using a stale tunnel."
fi

echo "[*] Starting SSH tunnel to ${ZONE_HOST} (you may be asked for your gateway password)..."
ssh -N -L "${GUI_PORT}:${ZONE_HOST}:${GUI_PORT}" "${GATEWAY_USER}@${GATEWAY_HOST}" &
SSH_PID=$!

echo "[*] Waiting for tunnel to become ready..."
tunnel_ready=0
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${GUI_PORT}/" >/dev/null 2>&1; then
        echo "[✓] SSH tunnel is up."
        tunnel_ready=1
        break
    fi
    if ! kill -0 "${SSH_PID}" 2>/dev/null; then
        echo "[ERROR] SSH process exited before the tunnel became ready (bad password? connection refused?)."
        exit 1
    fi
    sleep 2
done
if [ "${tunnel_ready}" -eq 0 ]; then
    echo "[ERROR] SSH tunnel did not become ready in time."
    echo "        Is the Gradio GUI running on the cluster? (bash scripts/start_gui.sh there)"
    exit 1
fi

# ── 2. Start Cloudflare quick tunnel ─────────────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
    echo "[ERROR] cloudflared not found. Install with: brew install cloudflared"
    exit 1
fi

echo "[*] Starting Cloudflare tunnel..."
rm -f "${CLOUDFLARED_LOG}"
cloudflared tunnel --url "http://localhost:${GUI_PORT}" > "${CLOUDFLARED_LOG}" 2>&1 &
CLOUDFLARED_PID=$!

echo "[*] Waiting for public URL..."
PUBLIC_URL=""
for i in $(seq 1 30); do
    PUBLIC_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "${CLOUDFLARED_LOG}" 2>/dev/null | head -1)
    if [ -n "${PUBLIC_URL}" ]; then
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[ERROR] Cloudflare tunnel did not report a URL in time. Check ${CLOUDFLARED_LOG}"
        exit 1
    fi
    sleep 2
done

echo "[✓] Public URL: ${PUBLIC_URL}"

# ── 3. Publish status ─────────────────────────────────────────────────────
write_status "true" "${PUBLIC_URL}"
publish_status "demo online at ${PUBLIC_URL}"

echo ""
echo "======================================================"
echo " Bridge is live."
echo ""
echo " Public URL : ${PUBLIC_URL}"
echo " Vanity URL : https://klar-learn.dev/aafsw"
echo ""
echo " Keep this terminal open. Press Ctrl+C to stop the"
echo " bridge — this will also take the public page offline."
echo "======================================================"

# Stay alive until interrupted; if either child dies unexpectedly, stop too.
# (Not using `wait -n` — macOS ships bash 3.2 by default, which predates it.)
while true; do
    if ! kill -0 "${SSH_PID}" 2>/dev/null; then
        echo "[!] SSH tunnel process exited unexpectedly."
        break
    fi
    if ! kill -0 "${CLOUDFLARED_PID}" 2>/dev/null; then
        echo "[!] Cloudflare tunnel process exited unexpectedly."
        break
    fi
    sleep 3
done
