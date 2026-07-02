#!/usr/bin/env bash
# Setup Ollama on the OVGU AILab cluster.
# Run once after first login or after a zone rebuild.
# Safe to re-run — all steps are idempotent.

set -e

OLLAMA_DIR="/project/${LOGNAME}/ollama"
OLLAMA_BIN="${OLLAMA_DIR}/bin/ollama"
OLLAMA_MODELS="${OLLAMA_DIR}/models"
OLLAMA_DOWNLOAD_URL="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64"

# Models to pull by default
DEFAULT_MODELS=("llama3.2" "gemma2:9b")
# Optional larger models — uncomment to include:
# OPTIONAL_MODELS=("gemma4:e4b" "llama4")

# ── Proxy (required for all HTTP traffic on the cluster) ────────────────────
export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'
export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'
export NO_PROXY='localhost,127.0.0.1'
export TMPDIR=/var/tmp

echo "======================================================"
echo " Ollama Setup — OVGU AILab Cluster"
echo " User   : ${LOGNAME}"
echo " Zone   : $(hostname)"
echo "======================================================"
echo ""

# ── 1. Check /project permissions ───────────────────────────────────────────
if [ ! -d "/project" ]; then
    echo "[ERROR] /project does not exist. Contact your supervisor."
    exit 1
fi

PROJECT_GROUP=$(stat -c %G /project/ 2>/dev/null || echo "")
if [ -n "${PROJECT_GROUP}" ]; then
    echo "[*] Setting effective group to '${PROJECT_GROUP}'..."
    timeout 2 newgrp "${PROJECT_GROUP}" 2>/dev/null || true
fi

# ── 2. Create directories ────────────────────────────────────────────────────
if [ ! -d "${OLLAMA_DIR}" ]; then
    echo "[*] Creating ${OLLAMA_DIR}..."
    mkdir -p "${OLLAMA_DIR}"
else
    echo "[✓] ${OLLAMA_DIR} already exists."
fi

if [ ! -d "${OLLAMA_MODELS}" ]; then
    echo "[*] Creating ${OLLAMA_MODELS}..."
    mkdir -p "${OLLAMA_MODELS}"
else
    echo "[✓] ${OLLAMA_MODELS} already exists."
fi

if [ ! -d "$(dirname "${OLLAMA_BIN}")" ]; then
    echo "[*] Creating $(dirname "${OLLAMA_BIN}")..."
    mkdir -p "$(dirname "${OLLAMA_BIN}")"
fi

# ── 3. Download Ollama binary ────────────────────────────────────────────────
if [ ! -f "${OLLAMA_BIN}" ]; then
    echo "[*] Ollama binary not found. Downloading..."
    curl -L "${OLLAMA_DOWNLOAD_URL}" -o "${OLLAMA_BIN}"
    if ! file "${OLLAMA_BIN}" | grep -q "ELF"; then
        echo "[ERROR] Download did not produce a valid binary (got: $(cat "${OLLAMA_BIN}")). Check OLLAMA_DOWNLOAD_URL."
        rm -f "${OLLAMA_BIN}"
        exit 1
    fi
    chmod +x "${OLLAMA_BIN}"
    echo "[✓] Ollama binary downloaded and made executable."
else
    echo "[✓] Ollama binary already exists at ${OLLAMA_BIN}."
fi

# ── 4. Persist env vars in ~/.bashrc ────────────────────────────────────────
add_to_bashrc() {
    local line="$1"
    if ! grep -qF "${line}" ~/.bashrc 2>/dev/null; then
        echo "${line}" >> ~/.bashrc
        echo "[*] Added to ~/.bashrc: ${line}"
    fi
}

echo ""
echo "[*] Checking ~/.bashrc env vars..."
add_to_bashrc "export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'"
add_to_bashrc "export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'"
add_to_bashrc "export NO_PROXY='localhost,127.0.0.1'"
add_to_bashrc "export TMPDIR=/var/tmp"
add_to_bashrc "export OLLAMA_MODELS=${OLLAMA_MODELS}"
echo "[✓] ~/.bashrc is up to date."

# ── 5. Check available RAM ───────────────────────────────────────────────────
echo ""
MEM_AVAIL_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
MEM_AVAIL_GB=$(echo "scale=1; ${MEM_AVAIL_KB}/1048576" | bc)
echo "[i] Available RAM: ~${MEM_AVAIL_GB} GB"
if (( MEM_AVAIL_KB < 8000000 )); then
    echo "[!] WARNING: Less than 8 GB available. Large models may cause OOM kills."
    echo "    Stick to llama3.2 or gemma2:9b."
fi

# ── 6. Pull models ───────────────────────────────────────────────────────────
echo ""
echo "[*] Starting temporary Ollama server to pull models..."
export OLLAMA_MODELS="${OLLAMA_MODELS}"

# Start server in background for pulling
"${OLLAMA_BIN}" serve &> /tmp/ollama_setup.log &
OLLAMA_PID=$!

# Wait for server to be ready
echo "[*] Waiting for Ollama server to become ready..."
for i in $(seq 1 30); do
    if curl -sf --noproxy localhost http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[✓] Ollama server is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[ERROR] Ollama server did not start in time. Check /tmp/ollama_setup.log"
        kill "${OLLAMA_PID}" 2>/dev/null
        exit 1
    fi
    sleep 2
done

# Pull each model if not already present
for model in "${DEFAULT_MODELS[@]}"; do
    echo ""
    echo "[*] Checking model: ${model}..."
    if "${OLLAMA_BIN}" list | grep -q "^${model}"; then
        echo "[✓] ${model} already pulled."
    else
        echo "[*] Pulling ${model} (this may take a while)..."
        "${OLLAMA_BIN}" pull "${model}"
        echo "[✓] ${model} pulled successfully."
    fi
done

# Stop the temporary server
echo ""
echo "[*] Stopping temporary server..."
kill "${OLLAMA_PID}" 2>/dev/null
wait "${OLLAMA_PID}" 2>/dev/null || true

echo ""
echo "======================================================"
echo " Setup complete!"
echo " Run ./scripts/start_ollama.sh to start the server."
echo "======================================================"
