"""FastAPI application exposing the RxSentinel pipeline.

Endpoints:
    POST   /api/review                — submit a medication list, returns request_id
    GET    /api/runs/{id}/events      — SSE stream of trace events for a run
    GET    /api/runs/{id}/report      — final structured report (when complete)
    GET    /api/health                — liveness check

Design:
    Submission is non-blocking. We start the LangGraph run as an asyncio Task
    and immediately return the request_id. The frontend opens an EventSource
    to /events for the live agent activity, and polls /report (or watches for
    a final SSE event) to get the structured result.
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from rxsentinel.config import settings
from rxsentinel.graph import build_graph
from rxsentinel.schemas import FinalReport
from rxsentinel.state import RxState
from rxsentinel.tracing.tracer import drop_tracer, get_tracer


_GRAPH = None
_RESULTS: dict[str, FinalReport] = {}
_TASKS: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Compile the graph once at startup."""
    global _GRAPH
    _GRAPH = build_graph()
    yield


app = FastAPI(
    title="RxSentinel API",
    description="Multi-agent medication safety review system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    medications: str = Field(..., min_length=3, max_length=4000)


class ReviewResponse(BaseModel):
    request_id: str
    started_at: datetime


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.ollama_model}


@app.post("/api/review", response_model=ReviewResponse)
async def submit_review(req: ReviewRequest) -> ReviewResponse:
    """Submit a medication list and start the agent pipeline asynchronously."""
    if _GRAPH is None:
        raise HTTPException(503, "Graph not compiled yet")

    request_id = str(uuid.uuid4())
    started_at = datetime.now(UTC)
    initial_state: RxState = {
        "raw_input": req.medications,
        "request_id": request_id,
        "started_at": started_at.isoformat(),
    }

    async def _run() -> None:
        tracer = get_tracer(request_id)
        try:
            result = await _GRAPH.ainvoke(initial_state)
            report = result.get("final_report")
            if report is not None:
                _RESULTS[request_id] = report
                tracer.emit(
                    "system",
                    "exit",
                    {"completed": True, "duration_ms": report.duration_ms},
                )
        except Exception as e:  # noqa: BLE001
            tracer.emit("system", "error", {"error": str(e)})
        finally:
            await tracer.close()

    _TASKS[request_id] = asyncio.create_task(_run())
    return ReviewResponse(request_id=request_id, started_at=started_at)


@app.get("/api/runs/{request_id}/events")
async def events(request_id: str) -> EventSourceResponse:
    """Server-Sent Events stream of trace events for a single run."""
    tracer = get_tracer(request_id)

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in tracer.stream():
                yield {
                    "event": event.event_type,
                    "data": event.model_dump_json(),
                }
        finally:
            drop_tracer(request_id)

    return EventSourceResponse(event_generator())


@app.get("/api/runs/{request_id}/report", response_model=FinalReport)
async def report(request_id: str) -> FinalReport:
    """Return the final structured report for a completed run."""
    if request_id not in _RESULTS:
        # If the run is still in flight, give the client an idea via 202.
        if request_id in _TASKS and not _TASKS[request_id].done():
            raise HTTPException(202, "Run still in progress")
        raise HTTPException(404, "Run not found")
    return _RESULTS[request_id]
