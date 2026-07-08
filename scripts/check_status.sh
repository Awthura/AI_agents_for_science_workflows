#!/usr/bin/env bash
# Check whether Ollama, the Gradio GUI, and the Cloudflare tunnel are all
# running on the OVGU AILab cluster. Read-only — never starts or kills
# anything, safe to run anytime.
# Run this on the cluster (after `ssh n05-07`), or non-interactively via:
#   ssh n05-07 "cd /project/\${LOGNAME}/AI_agents_for_science_workflows && ./scripts/check_status.sh"

OLLAMA_PORT=11434
GUI_PORT=7860
OLLAMA_SCREEN="ollama"
GUI_SCREEN="gradio-gui"
TUNNEL_SCREEN="cloudflared-tunnel"

echo "======================================================"
echo " Service Status — OVGU AILab Cluster"
echo " User : ${LOGNAME}"
echo " Zone : $(hostname)"
echo "======================================================"
echo ""

check_port() {
    local name="$1" port="$2" path="${3:-/}"
    if curl -sf --noproxy localhost "http://localhost:${port}${path}" > /dev/null 2>&1; then
        echo "[✓] ${name} responding on port ${port}"
    else
        echo "[✗] ${name} NOT responding on port ${port}"
    fi
}

check_screen() {
    local name="$1" session="$2"
    if screen -ls 2>/dev/null | grep -q "${session}"; then
        echo "[✓] screen session '${session}' exists"
    else
        echo "[✗] screen session '${session}' NOT found"
    fi
}

echo "--- Ollama ---"
check_port "Ollama" "${OLLAMA_PORT}" "/api/tags"
check_screen "Ollama" "${OLLAMA_SCREEN}"
LOADED=$(curl -s --noproxy localhost "http://localhost:${OLLAMA_PORT}/api/ps" 2>/dev/null \
    | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
    names = [m['name'] for m in d.get('models', [])]
    print(', '.join(names) if names else '(none loaded)')
except Exception:
    print('(could not parse /api/ps)')" 2>/dev/null)
echo "    Currently loaded model(s): ${LOADED:-unknown}"
echo ""

echo "--- Gradio GUI ---"
check_port "Gradio GUI" "${GUI_PORT}" "/"
check_screen "Gradio GUI" "${GUI_SCREEN}"
echo ""

echo "--- Cloudflare tunnel (optional — only if using scripts/start_tunnel.sh) ---"
check_screen "Cloudflare tunnel" "${TUNNEL_SCREEN}"
if [ -f "/tmp/cloudflared_${LOGNAME}.log" ]; then
    URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "/tmp/cloudflared_${LOGNAME}.log" 2>/dev/null | tail -1)
    [ -n "${URL}" ] && echo "    Last known public URL: ${URL}"
fi
echo ""

echo "======================================================"
echo " Fix a [✗]:"
echo "   Ollama down     -> ./scripts/start_ollama.sh"
echo "   GUI down        -> ./scripts/start_gui.sh"
echo "   Tunnel down     -> ./scripts/start_tunnel.sh (or your local SSH -L command)"
echo "======================================================"
