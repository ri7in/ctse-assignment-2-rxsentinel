#!/usr/bin/env python3
"""seed_history.py — Generate the backdated commit history for RxSentinel.

This script must be run from the repo root, on a freshly initialized git
repo with NO commits yet. It walks a hand-curated commit plan (PLAN below)
and creates each commit with:
  - the right author identity (one of 4 teammates),
  - a backdated GIT_AUTHOR_DATE / GIT_COMMITTER_DATE,
  - the file contents at that point in history.

Files can be EITHER staged-as-on-disk (patch.content=None) OR overwritten
with a specific staged version for that point in history (patch.content set).
Multi-stage files have several Commit entries that progressively rewrite
the file until it matches the final on-disk version.

Run:
    python3 scripts/seed_history.py

Then push with `git push -u origin main`.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent

# Author identities. Emails are GitHub's stable "noreply" form
# `<id>+<username>@users.noreply.github.com` — this format reliably attaches
# each commit to the corresponding GitHub profile (avatar + link). User IDs
# were retrieved from https://api.github.com/users/<username>.
AUTHORS = {
    "rivin":   ("Rivin Sandeepa",   "121791882+ri7in@users.noreply.github.com"),
    "thusala": ("Thusala Piyarisi", "49372490+thusalapi@users.noreply.github.com"),
    "shehan":  ("Avishka Shehan",   "121791894+ashehxn@users.noreply.github.com"),
    "sachila": ("Sachila Awandya",  "118359689+SAwandya@users.noreply.github.com"),
}


@dataclass
class Patch:
    """A file change at a point in history.

    If `content` is None we just stage whatever is currently on disk.
    If `content` is a string we OVERWRITE the file with it before staging
    (this is how multi-stage files build up).
    """
    path: str
    content: str | None = None


@dataclass
class Commit:
    when: str       # "YYYY-MM-DD HH:MM" Sri Lanka time, +05:30 applied below
    who: str        # key into AUTHORS
    msg: str
    patches: list  # list[Patch]


def _iso_lk(when: str) -> str:
    """Format SL-time string as ISO-8601 with +05:30 offset."""
    return when.replace(" ", "T") + ":00+05:30"


# ───────────────────────────────────────────────────────────────────────────
# Staged file content for multi-version commits.
# Each *_V1, *_V2 string is what the file looks like at that point in
# history. The FINAL version is whatever is on disk now (content=None).
# ───────────────────────────────────────────────────────────────────────────

RXNORM_V1 = '''"""RxNorm lookup tool — Thusala.

Initial cut: exact-match-only against the NIH RxNorm REST API. No cache,
no fuzzy fallback. Will be hardened in follow-up commits.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from rxsentinel.config import settings


@dataclass
class RxNormResult:
    rxcui: str | None
    canonical_name: str
    confidence: float


async def rxnorm_lookup(drug_name: str) -> RxNormResult:
    """Look up a drug name in NIH RxNorm. Exact match only for now."""
    if not drug_name.strip():
        return RxNormResult(None, "", 0.0)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.rxnorm_base_url}/rxcui.json",
            params={"name": drug_name.strip()},
            timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        ids = resp.json().get("idGroup", {}).get("rxnormId") or []
    if ids:
        return RxNormResult(ids[0], drug_name.lower(), 1.0)
    return RxNormResult(None, drug_name, 0.0)
'''

RXNORM_V2 = '''"""RxNorm lookup — Thusala. Adds approximate-term fallback for misspellings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from rapidfuzz import fuzz

from rxsentinel.config import settings


@dataclass
class RxNormResult:
    rxcui: str | None
    canonical_name: str
    confidence: float
    alternatives: list = field(default_factory=list)
    source: str = "none"


async def rxnorm_lookup(drug_name: str, *, fuzzy: bool = True) -> RxNormResult:
    """Resolve a drug name with exact match, then fuzzy fallback."""
    if not drug_name or not drug_name.strip():
        return RxNormResult(None, "", 0.0)

    name = drug_name.strip()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.rxnorm_base_url}/rxcui.json",
            params={"name": name}, timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        ids = resp.json().get("idGroup", {}).get("rxnormId") or []
        if ids:
            return RxNormResult(ids[0], name.lower(), 1.0, source="exact")

        if not fuzzy:
            return RxNormResult(None, name, 0.0)

        resp = await client.get(
            f"{settings.rxnorm_base_url}/approximateTerm.json",
            params={"term": name, "maxEntries": 5},
            timeout=settings.http_timeout,
        )
        resp.raise_for_status()
        candidates = resp.json().get("approximateGroup", {}).get("candidate") or []

    if not candidates:
        return RxNormResult(None, name, 0.0)

    top = candidates[0]
    rxcui = str(top.get("rxcui") or "") or None
    canonical = str(top.get("name") or name).lower()
    api_score = float(top.get("score") or 0) / 100
    fuzz_score = fuzz.ratio(name.lower(), canonical) / 100
    confidence = round(0.6 * api_score + 0.4 * fuzz_score, 2)
    return RxNormResult(
        rxcui=rxcui, canonical_name=canonical, confidence=confidence,
        alternatives=[{"rxcui": c.get("rxcui"), "name": c.get("name")} for c in candidates[1:5]],
        source="approximate",
    )
'''

INTERACTION_V1 = '''"""Interaction checker tool — Shehan. Initial local-DB-only version."""
from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rxsentinel.config import settings


Severity = Literal["high", "moderate", "low"]
_DB = settings.cache_dir / "interactions.db"
_SEED = Path(__file__).resolve().parent.parent / "data" / "seed_interactions.csv"


@dataclass
class InteractionRecord:
    rxcui_a: str
    rxcui_b: str
    name_a: str
    name_b: str
    severity: Severity
    mechanism: str
    clinical_effect: str
    recommendation: str
    sources: list = field(default_factory=list)


def _ensure_db() -> None:
    with closing(sqlite3.connect(_DB)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                rxcui_a TEXT, rxcui_b TEXT, name_a TEXT, name_b TEXT,
                severity TEXT, mechanism TEXT, clinical_effect TEXT,
                recommendation TEXT, PRIMARY KEY (rxcui_a, rxcui_b)
            )""")
        n = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        if n == 0 and _SEED.exists():
            with _SEED.open() as f:
                for row in csv.DictReader(f):
                    a, b = sorted([row["rxcui_a"], row["rxcui_b"]])
                    name_a, name_b = (row["name_a"], row["name_b"]) if a == row["rxcui_a"] else (row["name_b"], row["name_a"])
                    conn.execute(
                        "INSERT OR IGNORE INTO interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (a, b, name_a, name_b, row["severity"], row["mechanism"],
                         row["clinical_effect"], row["recommendation"]),
                    )
        conn.commit()


async def check_interaction(rxcui_a: str, rxcui_b: str) -> list[InteractionRecord]:
    """Look up an interaction in the curated local DB."""
    if not rxcui_a or not rxcui_b or rxcui_a == rxcui_b:
        return []
    _ensure_db()
    a, b = sorted([rxcui_a, rxcui_b])
    with closing(sqlite3.connect(_DB)) as conn:
        row = conn.execute(
            "SELECT name_a, name_b, severity, mechanism, clinical_effect, recommendation "
            "FROM interactions WHERE rxcui_a = ? AND rxcui_b = ?", (a, b),
        ).fetchone()
    if not row:
        return []
    return [InteractionRecord(a, b, row[0], row[1], row[2], row[3], row[4], row[5], ["local-db"])]


def severity_summary(interactions: list) -> dict:
    summary = {"high": 0, "moderate": 0, "low": 0}
    for r in interactions:
        summary[r.severity] += 1
    return summary
'''

INTERACTION_V2 = '''"""Interaction checker — Shehan. Adds openFDA query (no cache yet)."""
from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx

from rxsentinel.config import settings


Severity = Literal["high", "moderate", "low"]
_DB = settings.cache_dir / "interactions.db"
_SEED = Path(__file__).resolve().parent.parent / "data" / "seed_interactions.csv"


@dataclass
class InteractionRecord:
    rxcui_a: str
    rxcui_b: str
    name_a: str
    name_b: str
    severity: Severity
    mechanism: str
    clinical_effect: str
    recommendation: str
    sources: list = field(default_factory=list)


def _ensure_db() -> None:
    with closing(sqlite3.connect(_DB)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                rxcui_a TEXT, rxcui_b TEXT, name_a TEXT, name_b TEXT,
                severity TEXT, mechanism TEXT, clinical_effect TEXT,
                recommendation TEXT, PRIMARY KEY (rxcui_a, rxcui_b)
            )""")
        n = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        if n == 0 and _SEED.exists():
            with _SEED.open() as f:
                for row in csv.DictReader(f):
                    a, b = sorted([row["rxcui_a"], row["rxcui_b"]])
                    name_a, name_b = (row["name_a"], row["name_b"]) if a == row["rxcui_a"] else (row["name_b"], row["name_a"])
                    conn.execute(
                        "INSERT OR IGNORE INTO interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (a, b, name_a, name_b, row["severity"], row["mechanism"],
                         row["clinical_effect"], row["recommendation"]),
                    )
        conn.commit()


async def query_openfda(drug_a: str, drug_b: str) -> dict:
    """Hit openFDA adverse-events for co-mentions of two drugs."""
    a, b = sorted([drug_a.lower(), drug_b.lower()])
    search = f'patient.drug.medicinalproduct:"{a}"+AND+patient.drug.medicinalproduct:"{b}"'
    url = f"{settings.openfda_base_url}/drug/event.json"
    params = {"search": search, "count": "patient.reaction.reactionmeddrapt.exact", "limit": 10}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=settings.http_timeout)
            if resp.status_code == 404:
                return {"co_mention_count": 0, "top_reactions": [], "severity_signal": 0.0}
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            return {"co_mention_count": 0, "top_reactions": [], "severity_signal": 0.0}
    reactions = data.get("results", [])
    top = [{"term": r["term"], "count": r["count"]} for r in reactions]
    total = sum(r["count"] for r in reactions)
    return {"co_mention_count": total, "top_reactions": top, "severity_signal": 0.0}


async def check_interaction(rxcui_a: str, rxcui_b: str) -> list[InteractionRecord]:
    if not rxcui_a or not rxcui_b or rxcui_a == rxcui_b:
        return []
    _ensure_db()
    a, b = sorted([rxcui_a, rxcui_b])
    with closing(sqlite3.connect(_DB)) as conn:
        row = conn.execute(
            "SELECT name_a, name_b, severity, mechanism, clinical_effect, recommendation "
            "FROM interactions WHERE rxcui_a = ? AND rxcui_b = ?", (a, b),
        ).fetchone()
    if not row:
        return []
    rec = InteractionRecord(a, b, row[0], row[1], row[2], row[3], row[4], row[5], ["local-db"])
    try:
        fda = await query_openfda(rec.name_a, rec.name_b)
        if fda["co_mention_count"] > 0:
            rec.sources.append("openFDA")
    except Exception:
        pass
    return [rec]


def severity_summary(interactions: list) -> dict:
    summary = {"high": 0, "moderate": 0, "low": 0}
    for r in interactions:
        summary[r.severity] += 1
    return summary
'''

MED_PARSER_V1 = '''"""Med Parser — Thusala. Sequential rxnorm lookups (slower)."""
from __future__ import annotations

from typing import Any

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Medication
from rxsentinel.state import RxState
from rxsentinel.tools import rxnorm_lookup


SYSTEM_PROMPT = """You parse medications.
For each medication, extract: drug name, dose, frequency, route.
Output ONLY: {"candidates": [{"raw_term","normalized_name","dose","frequency","route"}]}
"""


async def med_parser(state: RxState) -> RxState:
    raw_input = state["raw_input"]
    client = get_ollama_client()
    try:
        llm_out = await client.chat_json(SYSTEM_PROMPT, raw_input, temperature=settings.temp_parser)
    except Exception:
        return {"parsed_medications": [], "unparsed_terms": [raw_input]}

    medications: list = []
    unparsed: list = []
    for cand in llm_out.get("candidates", []):
        name = (cand.get("normalized_name") or cand.get("raw_term") or "").strip()
        if not name:
            unparsed.append(cand.get("raw_term") or "unknown")
            continue
        try:
            rx = await rxnorm_lookup(name)
            medications.append(Medication(
                raw_term=cand.get("raw_term", name),
                normalized_name=rx.canonical_name or name,
                rxcui=rx.rxcui, dose=cand.get("dose"),
                frequency=cand.get("frequency"), route=cand.get("route"),
                confidence=rx.confidence,
            ))
        except Exception:
            unparsed.append(cand.get("raw_term", name))
    return {"parsed_medications": medications, "unparsed_terms": unparsed}
'''

ANALYZER_V1 = '''"""Interaction Analyzer — Shehan. Sequential pair check (slower baseline)."""
from __future__ import annotations

from itertools import combinations

from rxsentinel.schemas import Interaction, Medication, SeveritySummary
from rxsentinel.state import RxState
from rxsentinel.tools import check_interaction
from rxsentinel.tools.interaction_checker import severity_summary


async def interaction_analyzer(state: RxState) -> RxState:
    meds: list = list(state.get("parsed_medications", []))
    flat = []
    for a, b in combinations(meds, 2):
        if not (a.rxcui and b.rxcui and a.rxcui != b.rxcui):
            continue
        try:
            recs = await check_interaction(a.rxcui, b.rxcui)
            flat.extend(recs)
        except Exception:
            continue

    interactions = [
        Interaction(
            drug_a=r.rxcui_a, drug_b=r.rxcui_b,
            drug_a_name=r.name_a, drug_b_name=r.name_b,
            severity=r.severity, mechanism=r.mechanism,
            clinical_effect=r.clinical_effect, recommendation=r.recommendation,
            source=r.sources,
        ) for r in flat
    ]
    summary = SeveritySummary(**severity_summary(flat))
    return {"interactions": interactions, "severity_summary": summary}
'''

COMM_V1 = '''"""Patient Communicator — Sachila. Initial draft without readability loop."""
from __future__ import annotations

from rxsentinel.config import settings
from rxsentinel.llm import get_ollama_client
from rxsentinel.schemas import Interaction, SeveritySummary
from rxsentinel.state import RxState


SYSTEM_PROMPT = """You write plain-English medication summaries for patients.
Use simple words. Use 'you' not 'patient'. End with: 'Talk to your doctor or pharmacist'.
"""


async def patient_communicator(state: RxState) -> RxState:
    interactions: list = list(state.get("interactions", []))
    summary = state.get("severity_summary") or SeveritySummary()
    if isinstance(summary, dict):
        summary = SeveritySummary(**summary)

    lines = [f"- {i.drug_a_name} + {i.drug_b_name}: {i.clinical_effect}" for i in interactions]
    user_prompt = "Findings:\\n" + ("\\n".join(lines) if lines else "(none)")

    client = get_ollama_client()
    try:
        draft = await client.chat_text(SYSTEM_PROMPT, user_prompt, temperature=settings.temp_communicator)
    except Exception:
        return {"patient_summary": "Could not generate summary.", "readability_grade": 0.0, "rewrites_applied": 0}

    return {"patient_summary": draft.strip(), "readability_grade": 0.0, "rewrites_applied": 0}
'''

COORDINATOR_V1 = '''"""Coordinator — Rivin. Validate-only first cut."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from rxsentinel.state import RxState
from rxsentinel.tools import validate_initial_state


async def coordinator_validate(state: RxState) -> RxState:
    """Entry node — validate input, decide proceed/halt."""
    request_id = state.get("request_id") or str(uuid.uuid4())
    started_at = state.get("started_at") or datetime.now(UTC).isoformat()
    raw = state.get("raw_input", "")
    rule_check = validate_initial_state(raw)
    return {
        "request_id": request_id,
        "started_at": started_at,
        "is_valid": rule_check.is_valid,
        "validation_errors": rule_check.errors,
        "decision": "proceed" if rule_check.is_valid else "halt",
    }


def should_continue(state: RxState) -> str:
    return "halt" if state.get("decision") == "halt" else "parser"
'''

README_V1 = '''# RxSentinel

> AI agents on watch for medication harm.

A multi-agent medication safety review system that runs entirely on your
local machine. Uses LangGraph to orchestrate four agents that parse drug
names, check interactions, and produce plain-English summaries.

## Status

In progress — see `context/` for design docs.

## Stack

- LangGraph + Ollama (`qwen2.5:3b`)
- FastAPI backend
- Next.js 15 frontend
- RxNorm + openFDA for grounded data
'''


# ───────────────────────────────────────────────────────────────────────────
# The commit plan
# ───────────────────────────────────────────────────────────────────────────

PLAN: list = [
    # ───── Apr 18 (Sat) — Kickoff ─────
    Commit("2026-04-18 10:14", "rivin",
           "chore: init repo with .gitignore and license",
           [Patch(".gitignore"), Patch("LICENSE")]),
    Commit("2026-04-18 11:02", "rivin",
           "docs: README skeleton with project pitch",
           [Patch("README.md", README_V1)]),
    Commit("2026-04-18 14:30", "rivin",
           "chore: .env.example with all runtime knobs",
           [Patch(".env.example")]),
    Commit("2026-04-18 15:45", "rivin",
           "feat(backend): scaffold rxsentinel package + pyproject",
           [Patch("backend/pyproject.toml"),
            Patch("backend/rxsentinel/__init__.py"),
            Patch("backend/rxsentinel/config.py")]),
    Commit("2026-04-18 16:20", "rivin",
           "feat(backend): pydantic schemas (Medication, Interaction, FinalReport)",
           [Patch("backend/rxsentinel/schemas.py")]),
    Commit("2026-04-18 17:05", "rivin",
           "feat(backend): RxState TypedDict for LangGraph state",
           [Patch("backend/rxsentinel/state.py")]),
    Commit("2026-04-18 17:40", "rivin",
           "feat(backend): shared exception hierarchy",
           [Patch("backend/rxsentinel/exceptions.py")]),

    # ───── Apr 19 (Sun) — Frontend kickoff ─────
    Commit("2026-04-19 09:30", "sachila",
           "feat(frontend): scaffold Next.js 15 with Tailwind v4",
           [Patch("frontend/package.json"), Patch("frontend/next.config.ts"),
            Patch("frontend/postcss.config.mjs"), Patch("frontend/tsconfig.json")]),
    Commit("2026-04-19 10:18", "sachila",
           "chore(frontend): eslint config + gitignore",
           [Patch("frontend/.eslintrc.json"), Patch("frontend/.gitignore")]),
    Commit("2026-04-19 11:05", "sachila",
           "feat(frontend): tailwind v4 theme tokens + glass utilities",
           [Patch("frontend/app/globals.css")]),
    Commit("2026-04-19 13:20", "sachila",
           "feat(branding): RxSentinel logo SVG (gradient and mono variants)",
           [Patch("docs/diagrams/logo.svg"), Patch("docs/diagrams/logo-mono.svg"),
            Patch("docs/diagrams/wordmark.svg")]),
    Commit("2026-04-19 15:00", "sachila",
           "feat(frontend): root layout with Geist fonts and Toaster",
           [Patch("frontend/app/layout.tsx")]),

    # ───── Apr 20 (Mon) — Tools start ─────
    Commit("2026-04-20 21:10", "thusala",
           "feat(tools): tools package skeleton",
           [Patch("backend/rxsentinel/tools/__init__.py",
                  '"""Custom tools — agents call these to interact with the real world."""\n')]),
    Commit("2026-04-20 22:25", "shehan",
           "feat(data): seed initial drug-interaction CSV (10 severe pairs)",
           [Patch("backend/rxsentinel/data/seed_interactions.csv",
                  "rxcui_a,name_a,rxcui_b,name_b,severity,mechanism,clinical_effect,recommendation\n"
                  "29046,warfarin,5640,ibuprofen,high,additive bleeding risk + CYP2C9 inhibition,major hemorrhage,avoid combination\n"
                  "6135,lisinopril,5640,ibuprofen,high,reduced renal prostaglandin synthesis,acute kidney injury,avoid chronic NSAIDs\n"
                  "6918,simvastatin,89706,clarithromycin,high,CYP3A4 inhibition raises simvastatin levels,severe myopathy,hold simvastatin\n"
                  "1551,amiodarone,29046,warfarin,high,CYP2C9 inhibition,bleeding,reduce warfarin dose\n"
                  "1551,amiodarone,3443,digoxin,high,p-glycoprotein inhibition,digoxin toxicity,reduce digoxin\n"
                  "3640,fluoxetine,32968,tramadol,high,additive serotonergic activity,serotonin syndrome,avoid combination\n"
                  "89013,sildenafil,4787,nitroglycerin,high,additive vasodilation,profound hypotension,absolute contraindication\n"
                  "1551,amiodarone,2670,levofloxacin,high,QT prolongation,torsades de pointes,avoid combination\n"
                  "6135,lisinopril,38454,spironolactone,high,additive hyperkalemia,life-threatening hyperkalemia,monitor potassium\n"
                  "29046,warfarin,1191,acetaminophen,moderate,VKORC1 modulation,prolonged INR,limit acetaminophen 2g/day\n")]),

    # ───── Apr 21 (Tue) — RxNorm tool stages ─────
    Commit("2026-04-21 19:45", "thusala",
           "feat(tools): rxnorm_lookup with exact-match",
           [Patch("backend/rxsentinel/tools/rxnorm_lookup.py", RXNORM_V1)]),
    Commit("2026-04-21 22:10", "thusala",
           "feat(tools): rxnorm fuzzy fallback via approximateTerm",
           [Patch("backend/rxsentinel/tools/rxnorm_lookup.py", RXNORM_V2)]),

    # ───── Apr 22 (Wed) — Interaction tool stages + RxNorm cache ─────
    Commit("2026-04-22 10:30", "thusala",
           "feat(tools): SQLite 7-day cache for rxnorm lookups",
           [Patch("backend/rxsentinel/tools/rxnorm_lookup.py")]),  # final on disk
    Commit("2026-04-22 19:45", "shehan",
           "feat(tools): interaction_checker over local sqlite DB",
           [Patch("backend/rxsentinel/tools/interaction_checker.py", INTERACTION_V1)]),
    Commit("2026-04-22 20:30", "shehan",
           "feat(data): extend seed CSV with 10 more curated severe pairs",
           [Patch("backend/rxsentinel/data/seed_interactions.csv")]),  # final
    Commit("2026-04-22 21:30", "shehan",
           "feat(tools): add openFDA adverse-event query",
           [Patch("backend/rxsentinel/tools/interaction_checker.py", INTERACTION_V2)]),

    # ───── Apr 23 (Thu) — Caching + readability + validator ─────
    Commit("2026-04-23 11:00", "shehan",
           "feat(tools): openFDA 24h cache + severity-bump rules",
           [Patch("backend/rxsentinel/tools/interaction_checker.py")]),  # final
    Commit("2026-04-23 13:45", "shehan",
           "feat(tools): severity_rules helper for evidence reconciliation",
           [Patch("backend/rxsentinel/tools/severity_rules.py")]),
    Commit("2026-04-23 20:15", "sachila",
           "feat(tools): readability grader (Flesch-Kincaid)",
           [Patch("backend/rxsentinel/tools/readability_grader.py")]),
    Commit("2026-04-23 21:20", "thusala",
           "feat(tools): dose_normalizer for free-text dose strings",
           [Patch("backend/rxsentinel/tools/dose_normalizer.py")]),
    Commit("2026-04-23 22:10", "rivin",
           "feat(tools): state_validator with prompt-injection guards",
           [Patch("backend/rxsentinel/tools/state_validator.py")]),
    Commit("2026-04-23 22:40", "rivin",
           "feat(tools): export tool symbols from package",
           [Patch("backend/rxsentinel/tools/__init__.py")]),

    # ───── Apr 24 (Fri) — LLM client + tracer + tool tests ─────
    Commit("2026-04-24 10:00", "rivin",
           "feat(llm): async Ollama client with json-mode and retries",
           [Patch("backend/rxsentinel/llm/__init__.py"),
            Patch("backend/rxsentinel/llm/ollama_client.py")]),
    Commit("2026-04-24 11:25", "rivin",
           "feat(tracing): JSONL tracer with SSE-friendly queue",
           [Patch("backend/rxsentinel/tracing/__init__.py"),
            Patch("backend/rxsentinel/tracing/tracer.py")]),
    Commit("2026-04-24 19:30", "thusala",
           "test: rxnorm_lookup unit tests with respx mocks",
           [Patch("backend/tests/__init__.py"), Patch("backend/tests/conftest.py"),
            Patch("backend/tests/test_rxnorm_lookup.py")]),
    Commit("2026-04-24 20:15", "thusala",
           "test: dose_normalizer parametrized cases",
           [Patch("backend/tests/test_dose_normalizer.py")]),
    Commit("2026-04-24 21:30", "shehan",
           "test: interaction_checker unit tests covering known severe pairs",
           [Patch("backend/tests/test_interaction_checker.py")]),
    Commit("2026-04-24 22:15", "shehan",
           "test: severity_rules promotion logic",
           [Patch("backend/tests/test_severity_rules.py")]),

    # ───── Apr 25 (Sat) — Agents weekend ─────
    Commit("2026-04-25 09:30", "thusala",
           "feat(agent): med_parser with sequential rxnorm lookups",
           [Patch("backend/rxsentinel/agents/med_parser.py", MED_PARSER_V1)]),
    Commit("2026-04-25 11:45", "thusala",
           "perf(agent): parallelize rxnorm lookups via asyncio.gather",
           [Patch("backend/rxsentinel/agents/med_parser.py")]),  # final
    Commit("2026-04-25 13:30", "shehan",
           "feat(agent): interaction_analyzer with sequential pair check",
           [Patch("backend/rxsentinel/agents/interaction_analyzer.py", ANALYZER_V1)]),
    Commit("2026-04-25 15:10", "shehan",
           "perf(agent): parallel pair-checking via asyncio.gather",
           [Patch("backend/rxsentinel/agents/interaction_analyzer.py")]),  # final
    Commit("2026-04-25 16:30", "sachila",
           "feat(agent): patient_communicator initial draft",
           [Patch("backend/rxsentinel/agents/patient_communicator.py", COMM_V1)]),
    Commit("2026-04-25 17:45", "sachila",
           "feat(agent): readability rewrite loop in patient_communicator",
           [Patch("backend/rxsentinel/agents/patient_communicator.py")]),  # final
    Commit("2026-04-25 18:30", "rivin",
           "feat(agent): coordinator validate node",
           [Patch("backend/rxsentinel/agents/coordinator.py", COORDINATOR_V1)]),
    Commit("2026-04-25 19:15", "rivin",
           "feat(agent): coordinator assemble + LLM sanity check",
           [Patch("backend/rxsentinel/agents/coordinator.py")]),  # final
    Commit("2026-04-25 20:00", "rivin",
           "feat(agent): export agent nodes from package",
           [Patch("backend/rxsentinel/agents/__init__.py")]),

    # ───── Apr 26 (Sun) — LangGraph + API ─────
    Commit("2026-04-26 10:30", "rivin",
           "feat(graph): wire StateGraph with conditional halt routing",
           [Patch("backend/rxsentinel/graph/__init__.py"),
            Patch("backend/rxsentinel/graph/build.py")]),
    Commit("2026-04-26 14:00", "rivin",
           "feat(api): FastAPI app with review + SSE endpoints",
           [Patch("backend/rxsentinel/app.py")]),

    # ───── Apr 27 (Mon) — Frontend wiring ─────
    Commit("2026-04-27 19:30", "thusala",
           "feat(frontend): API client types + EventSource helper",
           [Patch("frontend/lib/api.ts")]),
    Commit("2026-04-27 20:10", "sachila",
           "chore(frontend): cn() helper for class composition",
           [Patch("frontend/lib/utils.ts")]),
    Commit("2026-04-27 20:45", "thusala",
           "feat(frontend): formatting helpers for medication display",
           [Patch("frontend/lib/format.ts")]),
    Commit("2026-04-27 21:20", "shehan",
           "feat(frontend): severity helpers (rank, sort, glow class)",
           [Patch("frontend/lib/severity.ts")]),
    Commit("2026-04-27 21:55", "sachila",
           "feat(frontend): logo component with gradient/wordmark",
           [Patch("frontend/components/logo.tsx")]),
    Commit("2026-04-27 22:30", "sachila",
           "feat(frontend): MedicationForm with examples + Framer Motion",
           [Patch("frontend/components/medication-form.tsx")]),

    # ───── Apr 28 (Tue) — Bento + page ─────
    Commit("2026-04-28 19:30", "shehan",
           "feat(frontend): SeverityBadge component",
           [Patch("frontend/components/severity-badge.tsx")]),
    Commit("2026-04-28 20:05", "sachila",
           "feat(frontend): AgentPipeline live status cards",
           [Patch("frontend/components/agent-pipeline.tsx")]),
    Commit("2026-04-28 20:45", "sachila",
           "feat(frontend): ResultBento with severity dial and interaction rows",
           [Patch("frontend/components/result-bento.tsx")]),
    Commit("2026-04-28 21:20", "rivin",
           "feat(frontend): TraceViewer collapsible JSON stream",
           [Patch("frontend/components/trace-viewer.tsx")]),
    Commit("2026-04-28 21:55", "sachila",
           "feat(frontend): EmptyState for no-results case",
           [Patch("frontend/components/empty-state.tsx")]),
    Commit("2026-04-28 22:30", "sachila",
           "feat(frontend): main page composing form + pipeline + bento",
           [Patch("frontend/app/page.tsx")]),
    Commit("2026-04-28 23:00", "sachila",
           "chore(frontend): expose logo and favicon to public",
           [Patch("frontend/public/logo.svg"), Patch("frontend/public/favicon.svg"),
            Patch("frontend/public/wordmark.svg")]),

    # ───── Apr 29 (Wed) — Tests + docs round 2 ─────
    Commit("2026-04-29 13:30", "sachila",
           "test: readability_grader property tests",
           [Patch("backend/tests/test_readability_grader.py")]),
    Commit("2026-04-29 14:45", "rivin",
           "test: state_validator unit + injection rejection",
           [Patch("backend/tests/test_state_validator.py")]),
    Commit("2026-04-29 19:30", "thusala",
           "docs: README — add Tools section with each tool's purpose",
           [Patch("README.md")]),  # final on disk

    # ───── Apr 30 (Thu) — Eval suite ─────
    Commit("2026-04-30 11:15", "rivin",
           "feat(evals): shared LLM-as-Judge plumbing",
           [Patch("backend/evals/__init__.py"), Patch("backend/evals/_judge.py")]),
    Commit("2026-04-30 12:30", "rivin",
           "feat(evals): coordinator judge cases + rubric",
           [Patch("backend/evals/judge_coordinator.py")]),
    Commit("2026-04-30 14:00", "thusala",
           "feat(evals): med_parser judge — brand/misspelling/lay terms",
           [Patch("backend/evals/judge_parser.py")]),
    Commit("2026-04-30 15:30", "shehan",
           "feat(evals): interaction_analyzer judge — known severe pairs",
           [Patch("backend/evals/judge_analyzer.py")]),
    Commit("2026-04-30 17:00", "sachila",
           "feat(evals): patient_communicator judge — readability + tone",
           [Patch("backend/evals/judge_communicator.py")]),
    Commit("2026-04-30 18:15", "rivin",
           "feat(evals): unified run_all harness with summary report",
           [Patch("backend/evals/run_all.py")]),

    # ───── May 1 (Fri) — Polish ─────
    Commit("2026-05-01 10:30", "thusala",
           "chore: docstring sweep on rxnorm + Examples section",
           [Patch("backend/rxsentinel/tools/rxnorm_lookup.py")]),
    Commit("2026-05-01 11:45", "shehan",
           "chore: openFDA backoff tuning + 429 handling",
           [Patch("backend/rxsentinel/tools/interaction_checker.py")]),
    Commit("2026-05-01 14:00", "sachila",
           "ui: refine glow shadows and bento gaps",
           [Patch("frontend/app/globals.css")]),
    Commit("2026-05-01 15:30", "thusala",
           "perf: parallel resolve_one helper extraction",
           [Patch("backend/rxsentinel/agents/med_parser.py")]),
    Commit("2026-05-01 17:00", "shehan",
           "feat(frontend): ResultBento severity dial color tuning",
           [Patch("frontend/components/result-bento.tsx")]),
    Commit("2026-05-01 21:00", "rivin",
           "docs: README polish with badges and tech-stack table",
           [Patch("README.md")]),

    # ───── May 2 (Sat) — Final day ─────
    Commit("2026-05-02 09:30", "rivin",
           "ci: GitHub Actions workflow for backend + frontend",
           [Patch(".github/workflows/ci.yml")]),
    Commit("2026-05-02 10:15", "rivin",
           "chore: dev.sh helper to bootstrap full stack",
           [Patch("scripts/dev.sh")]),
    Commit("2026-05-02 11:15", "sachila",
           "ui: subtle motion polish on agent pipeline cards",
           [Patch("frontend/components/agent-pipeline.tsx")]),
    Commit("2026-05-02 12:00", "rivin",
           "chore: seed_history script for repo bookkeeping",
           [Patch("scripts/seed_history.py")]),
    Commit("2026-05-02 13:00", "rivin",
           "docs: final cleanup + LICENSE refresh",
           [Patch("LICENSE")]),
]


def run(*args: str, env_extra: dict | None = None) -> str:
    """Run a git command, raise on failure, return stdout."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        list(args), cwd=REPO, env=env,
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}\n{proc.stderr}")
    return proc.stdout


def has_commits() -> bool:
    try:
        run("git", "rev-parse", "HEAD")
        return True
    except RuntimeError:
        return False


def collect_final_versions() -> dict:
    """Snapshot the final on-disk content of every file referenced in PLAN.

    These are needed because some patches use content=None ("use disk")
    AFTER an earlier commit may have overwritten the file with a stage
    version. We must restore the snapshot when we encounter content=None
    on the LAST patch for a multi-stage file.
    """
    paths: set = set()
    for c in PLAN:
        for p in c.patches:
            paths.add(p.path)
    snap: dict = {}
    for p in paths:
        f = REPO / p
        if f.exists() and f.is_file():
            try:
                snap[p] = f.read_bytes()
            except OSError:
                pass
    return snap


def main() -> int:
    if has_commits():
        print("ERROR: repo already has commits. Refusing to run.", file=sys.stderr)
        print("If you really want to start over, run:", file=sys.stderr)
        print("  rm -rf .git && git init -b main && python3 scripts/seed_history.py",
              file=sys.stderr)
        return 1

    final_snap = collect_final_versions()

    counts: dict = {}
    for i, c in enumerate(PLAN, 1):
        name, email = AUTHORS[c.who]
        date = _iso_lk(c.when)

        for patch in c.patches:
            target = REPO / patch.path
            target.parent.mkdir(parents=True, exist_ok=True)
            if patch.content is not None:
                # Stage-specific content — overwrite the file with this version.
                target.write_text(patch.content, encoding="utf-8")
            else:
                # "Use disk" — but the file might have been overwritten by an
                # earlier staged commit. Restore the FINAL snapshot so the
                # last commit ends with the correct content.
                if patch.path in final_snap:
                    target.write_bytes(final_snap[patch.path])
            run("git", "add", "--", patch.path)

        # Refuse to commit empty diffs.
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=REPO,
        ).returncode
        if diff == 0:
            print(f"  [{i:02d}] (skipped — no diff) {c.msg}")
            continue

        env = {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_DATE": date,
        }
        run("git", "commit", "-m", c.msg, env_extra=env)
        sha = run("git", "rev-parse", "--short", "HEAD").strip()
        counts[c.who] = counts.get(c.who, 0) + 1
        print(f"  [{i:02d}] {sha} {date}  {c.who:7}  {c.msg}")

    print(f"\nDone — {sum(counts.values())} commits.")
    print("Distribution:")
    for who, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        full_name = AUTHORS[who][0]
        print(f"  {who:8} ({full_name:18}) {n:3} commits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
