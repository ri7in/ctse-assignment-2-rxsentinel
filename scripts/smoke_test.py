#!/usr/bin/env python3
"""Quick smoke test — hits the backend directly without the frontend.

Usage:
    # In another terminal: cd backend && .venv/bin/uvicorn rxsentinel.app:app --port 8000
    python3 scripts/smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from urllib.request import Request, urlopen, build_opener, ProxyHandler, install_opener
from urllib.error import HTTPError, URLError

# Bypass any system-level proxy for localhost calls.
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"
install_opener(build_opener(ProxyHandler({})))

BASE = "http://127.0.0.1:8000/api"
TEST_INPUT = (
    "warfarin 5mg daily, amiodarone 200mg twice daily, "
    "ibuprofen 400mg as needed, simvastatin 40mg, "
    "clarithromycin 500mg twice daily"
)


def post(path: str, body: dict) -> dict:
    req = Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get(path: str) -> tuple[int, dict | str]:
    try:
        with urlopen(f"{BASE}{path}", timeout=60) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    print("▸ Health check...")
    try:
        with urlopen(f"{BASE}/health", timeout=5) as r:
            print(f"  {json.loads(r.read())}")
    except (HTTPError, URLError) as e:
        print(f"  ✗ backend not reachable: {e}")
        return 1

    print(f"\n▸ Submitting medication review...")
    print(f"  input: {TEST_INPUT[:80]}...")
    submit = post("/review", {"medications": TEST_INPUT})
    request_id = submit["request_id"]
    print(f"  request_id: {request_id}")

    print(f"\n▸ Polling for report...")
    started = time.time()
    while time.time() - started < 90:
        status, body = get(f"/runs/{request_id}/report")
        if status == 200:
            elapsed = time.time() - started
            print(f"  ✓ ready in {elapsed:.1f}s\n")
            print_report(body)
            return 0
        if status == 202:
            print(f"  ... still running ({int(time.time() - started)}s)", end="\r", flush=True)
            time.sleep(2)
            continue
        print(f"  ✗ unexpected status {status}: {body}")
        return 1

    print("\n  ✗ timed out after 90s")
    return 1


def print_report(report: dict) -> None:
    summary = report["severity_summary"]
    print(f"  ── Severity ──")
    print(f"     high:     {summary['high']}")
    print(f"     moderate: {summary['moderate']}")
    print(f"     low:      {summary['low']}")
    print(f"\n  ── Parsed ({len(report['medications'])}) ──")
    for m in report["medications"]:
        print(f"     • {m['normalized_name']:25} rxcui={m['rxcui']!s:>8}  "
              f"conf={m['confidence']:.2f}  dose={m.get('dose') or '-'}")
    print(f"\n  ── Interactions ({len(report['interactions'])}) ──")
    for i in report["interactions"][:8]:
        print(f"     [{i['severity'].upper():8}] {i['drug_a_name']} + {i['drug_b_name']}")
        print(f"                 → {i['clinical_effect']}")
    print(f"\n  ── Patient summary (grade {report['readability_grade']:.1f}) ──")
    print(f"  {report['patient_summary'][:400]}{'…' if len(report['patient_summary']) > 400 else ''}")
    print(f"\n  Total runtime: {report['duration_ms']:.0f}ms")


if __name__ == "__main__":
    sys.exit(main())
