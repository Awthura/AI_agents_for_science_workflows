#!/usr/bin/env bash
# Set up the Python virtual environment on the OVGU AILab cluster.
# Run once after cloning, or after requirements.txt changes.
# Safe to re-run — skips steps already done.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/venv"
PYTHON="python3"

export HTTP_PROXY='http://fp.cs.ovgu.de:3210/'
export HTTPS_PROXY='http://fp.cs.ovgu.de:3210/'
export TMPDIR=/var/tmp

echo "======================================================"
echo " Python Env Setup — OVGU AILab Cluster"
echo " User : ${LOGNAME}"
echo " Repo : ${REPO_DIR}"
echo "======================================================"
echo ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
if ! command -v ${PYTHON} &>/dev/null; then
    echo "[ERROR] python3 not found. Ask your supervisor to install it."
    exit 1
fi

PY_VERSION=$(${PYTHON} --version 2>&1)
echo "[✓] Found ${PY_VERSION}"

# ── 2. Create venv if it doesn't exist ──────────────────────────────────────
if [ ! -d "${VENV_DIR}" ]; then
    echo "[*] Creating virtual environment at ${VENV_DIR}..."
    ${PYTHON} -m venv "${VENV_DIR}"
    echo "[✓] Virtual environment created."
else
    echo "[✓] Virtual environment already exists."
fi

# ── 3. Activate venv ────────────────────────────────────────────────────────
source "${VENV_DIR}/bin/activate"
echo "[✓] Activated venv: $(which python)"

# ── 4. Upgrade pip ──────────────────────────────────────────────────────────
echo ""
echo "[*] Upgrading pip..."
pip install --upgrade pip --quiet
echo "[✓] pip up to date: $(pip --version)"

# ── 5. Install requirements ──────────────────────────────────────────────────
echo ""
echo "[*] Installing requirements from requirements.txt..."
pip install -r "${REPO_DIR}/requirements.txt"
echo "[✓] All packages installed."

# ── 6. Persist NO_PROXY to ~/.bashrc ────────────────────────────────────────
# Required so langchain_ollama reaches localhost:11434 without going through the proxy.
NO_PROXY_LINE="export NO_PROXY='localhost,127.0.0.1'"
if ! grep -qF "${NO_PROXY_LINE}" ~/.bashrc 2>/dev/null; then
    echo "${NO_PROXY_LINE}" >> ~/.bashrc
    echo "[*] Added NO_PROXY to ~/.bashrc"
fi
export NO_PROXY='localhost,127.0.0.1'
echo "[✓] NO_PROXY set."

# ── 8. Verify key imports ────────────────────────────────────────────────────
echo ""
echo "[*] Verifying key imports..."
python -c "import langgraph; print('  [✓] langgraph')"
python -c "import langchain_ollama; print('  [✓] langchain_ollama')"
python -c "import pydantic; print('  [✓] pydantic', pydantic.__version__)"
python -c "import rich, importlib.metadata; print('  [✓] rich', importlib.metadata.version('rich'))"

# ── 9. Create .env if missing ────────────────────────────────────────────────
if [ ! -f "${REPO_DIR}/.env" ]; then
    echo ""
    echo "[*] Creating .env from template..."
    cat > "${REPO_DIR}/.env" <<EOF
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
FIRECRAWL_API_KEY=
FIRECRAWL_API_URL=http://localhost:3002
EOF
    echo "[✓] .env created — edit it if needed."
else
    echo "[✓] .env already exists."
fi

echo ""
echo "======================================================"
echo " Setup complete!"
echo ""
echo " Activate the venv:  source venv/bin/activate"
echo " Run the pipeline:   python -m src.main"
echo "======================================================"
