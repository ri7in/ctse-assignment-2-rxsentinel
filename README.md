# RxSentinel

> AI agents on watch for medication harm.

A locally-hosted **multi-agent system** that performs comprehensive medication
safety reviews — drug interactions, severity ranking, and plain-English patient
explanations — entirely offline, using local SLMs via Ollama.

[![Made with LangGraph](https://img.shields.io/badge/LangGraph-0.2-1c3d5a)](https://langchain-ai.github.io/langgraph/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000)](https://nextjs.org/)
[![Ollama](https://img.shields.io/badge/Ollama-qwen2.5%3A3b-7b3fe4)](https://ollama.com/library/qwen2.5)
[![License: MIT](https://img.shields.io/badge/license-MIT-06b6d4)](LICENSE)

## What it does

Paste a list of medications — even messy free text — and a swarm of agents will:

1. **Parse** each drug to a normalized RxNorm code.
2. **Analyze** every drug-pair for interactions (openFDA + curated severe-interaction DB).
3. **Communicate** the findings in plain English at a 6th-grade reading level.

All locally. No data leaves your machine.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Coordinator → Parser → Analyzer → Communicator → END    │
│  (validate)   (RxNorm)  (openFDA)  (Flesch-Kincaid)      │
└──────────────────────────────────────────────────────────┘
              ▲                                 ▲
              │  shared TypedDict state         │
              └─────────  trace logger ─────────┘
```

See [`docs/diagrams/`](docs/diagrams/) for full architecture diagrams.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestrator | **LangGraph** | First-class state, observability, conditional routing |
| LLM | **Ollama** (`qwen2.5:3b`) | Local, free, strong tool-calling on small hardware |
| Backend | **FastAPI + Pydantic v2** | Async, typed, SSE-native |
| Frontend | **Next.js 15 + Tailwind v4 + shadcn/ui** | Modern, RSC-first, fast |
| State store | **SQLite** | Zero-setup, file-backed caches |
| Tracing | **Custom JSONL tracer** | Streamed live to UI via SSE |

## Quick start

```bash
# Prerequisites: macOS/Linux, Python 3.11+, Node 20+, Ollama

# 1. Pull the model
ollama pull qwen2.5:3b

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn rxsentinel.app:app --reload

# 3. Frontend (new terminal)
cd frontend
pnpm install
pnpm dev

# Open http://localhost:3000
```

## Project structure

```
.
├── backend/
│   ├── rxsentinel/
│   │   ├── agents/         # 4 LangGraph nodes
│   │   ├── tools/          # 4 custom tools (one per agent)
│   │   ├── graph/          # StateGraph wiring
│   │   ├── tracing/        # JSONL tracer + SSE
│   │   └── app.py          # FastAPI entrypoint
│   ├── tests/              # pytest unit + integration
│   └── evals/              # LLM-as-Judge scripts
├── frontend/
│   ├── app/                # Next.js App Router
│   ├── components/         # shadcn/ui components
│   └── lib/                # Client utilities
├── docs/
│   ├── diagrams/           # Architecture diagrams
│   └── report/             # LaTeX technical report
└── scripts/                # Helper scripts
```

## Team

| Member | Student ID | GitHub | Owns |
|---|---|---|---|
| Jayasuriya L. K. R. S. (Rivin)        | @ri7in's student ID | [@ri7in](https://github.com/ri7in)          | Coordinator agent + state validator + orchestration |
| Piyarisi T. D. (Thusala)              | IT22326690 | [@thusalapi](https://github.com/thusalapi)  | Medication Parser agent + RxNorm tool |
| Wickramasooriya J. D. A. S. (Avishka) | IT22347244 | [@ashehxn](https://github.com/ashehxn)      | Interaction Analyzer agent + openFDA + interactions DB |
| Manamperi S. A. (Sachila)             | IT22004772 | [@SAwandya](https://github.com/SAwandya)    | Patient Communicator agent + readability grader + frontend |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/) — NIH normalized drug names
- [openFDA](https://open.fda.gov/) — Adverse event data
- [LangGraph](https://langchain-ai.github.io/langgraph/) — Graph-based agent orchestration
- [Ollama](https://ollama.com/) — Local model serving
