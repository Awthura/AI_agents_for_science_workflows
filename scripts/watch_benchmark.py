#!/usr/bin/env python3
"""Live progress bar for a running decision-scoring benchmark.

Polls the results JSON file and renders a tqdm bar -- does not touch the
running benchmark process, safe to run alongside it in a separate terminal.

Usage (from repo root):
    python3 scripts/watch_benchmark.py                    # default file below
    python3 scripts/watch_benchmark.py path/to/results.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from tqdm import tqdm

DEFAULT_FILE = Path(__file__).parent.parent / "src/benchmark/decision_scoring_results_fewshot.json"
POLL_SECONDS = 5


def read_progress(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    data = json.loads(path.read_text(encoding="utf-8"))
    total = len(data.get("models", [])) * data.get("profile_count", 0)
    return len(data.get("results", [])), total


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE

    n, total = read_progress(path)
    while total == 0:
        print(f"[*] Waiting for {path} to be created...")
        time.sleep(POLL_SECONDS)
        n, total = read_progress(path)

    with tqdm(total=total, initial=n, desc=path.stem, unit="run") as bar:
        while bar.n < total:
            time.sleep(POLL_SECONDS)
            new_n, total = read_progress(path)
            bar.total = total
            bar.update(new_n - bar.n)

    print("[DONE]")


if __name__ == "__main__":
    main()
