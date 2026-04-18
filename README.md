# RxSentinel

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
