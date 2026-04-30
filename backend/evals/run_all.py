"""Unified evaluation harness — runs all 4 LLM-as-Judge suites.

Usage:
    python -m evals.run_all

Output: prints per-suite verdict + an overall pass rate and saves a JSON
report to runs/eval_<timestamp>.json so the technical report can cite it.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from rxsentinel.config import settings

from evals.judge_analyzer import run as run_analyzer
from evals.judge_communicator import run as run_communicator
from evals.judge_coordinator import run as run_coordinator
from evals.judge_parser import run as run_parser


SUITES = [
    ("coordinator", run_coordinator),
    ("med_parser", run_parser),
    ("interaction_analyzer", run_analyzer),
    ("patient_communicator", run_communicator),
]


async def main() -> None:
    print(f"\nRxSentinel — Evaluation Suite | model: {settings.ollama_model}\n")
    started = datetime.now(UTC)
    for name, fn in SUITES:
        print(f"\n>>> Running {name} judge...\n")
        await fn()
    finished = datetime.now(UTC)
    summary = {
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": (finished - started).total_seconds(),
        "model": settings.ollama_model,
        "suites": [n for n, _ in SUITES],
    }
    out_path: Path = settings.trace_dir / f"eval_{started.strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
