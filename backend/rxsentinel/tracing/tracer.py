"""Tracer — append-only JSONL log of every agent + tool event.

The tracer is the single source of truth for the "Agent Activity" stream
the frontend renders live via SSE. Each event is also persisted to
runs/<request_id>.jsonl for post-hoc analysis.

Design choices:
- One file per request keeps reads cheap and avoids lock contention.
- Events are flushed immediately so SSE consumers see them without buffering.
- Structured payload (dict) is serialized via Pydantic on emit.
"""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, TypeVar

from rxsentinel.config import settings
from rxsentinel.schemas import TraceEvent

T = TypeVar("T")


class Tracer:
    """Per-request tracer. Owns one JSONL file and one in-memory queue for SSE."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.path: Path = settings.trace_dir / f"{request_id}.jsonl"
        self._queue: asyncio.Queue[TraceEvent | None] = asyncio.Queue()
        self._closed = False

    def emit(
        self,
        agent: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> TraceEvent:
        """Write one event to disk and push to the SSE queue."""
        evt = TraceEvent(
            ts=datetime.now(UTC),
            agent=agent,
            event_type=event_type,  # type: ignore[arg-type]
            payload=payload or {},
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(evt.model_dump_json() + "\n")
        try:
            self._queue.put_nowait(evt)
        except asyncio.QueueFull:
            pass
        return evt

    async def close(self) -> None:
        """Signal SSE consumers that this run has ended."""
        if not self._closed:
            self._closed = True
            await self._queue.put(None)

    async def stream(self) -> AsyncIterator[TraceEvent]:
        """Yield events as they arrive, terminating on close()."""
        while True:
            evt = await self._queue.get()
            if evt is None:
                return
            yield evt


_TRACERS: dict[str, Tracer] = {}


def get_tracer(request_id: str) -> Tracer:
    """Return (or create) the singleton tracer for a request."""
    if request_id not in _TRACERS:
        _TRACERS[request_id] = Tracer(request_id)
    return _TRACERS[request_id]


def drop_tracer(request_id: str) -> None:
    """Remove a tracer once the request is fully consumed (frees memory)."""
    _TRACERS.pop(request_id, None)


def traced(agent_name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator: wraps an async agent node, emitting enter/exit events.

    The wrapped function must accept `state: RxState` as first positional arg.
    The state must contain `request_id` for events to route correctly.

    Example:
        @traced("parser")
        async def parser_node(state: RxState) -> RxState: ...
    """
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(state: dict, *args: Any, **kwargs: Any) -> T:
            req_id = state.get("request_id", "unknown")
            tracer = get_tracer(req_id)
            tracer.emit(agent_name, "enter", {"keys": list(state.keys())})
            t0 = time.perf_counter()
            try:
                result = await fn(state, *args, **kwargs)
                dur = (time.perf_counter() - t0) * 1000
                tracer.emit(
                    agent_name,
                    "exit",
                    {"output_keys": list(result.keys()) if isinstance(result, dict) else []},
                    duration_ms=dur,
                )
                return result
            except Exception as e:  # noqa: BLE001
                dur = (time.perf_counter() - t0) * 1000
                tracer.emit(agent_name, "error", {"error": str(e)}, duration_ms=dur)
                raise

        return wrapper

    return decorator


@asynccontextmanager
async def tool_event(
    request_id: str, agent: str, tool_name: str, args: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    """Context manager that emits a tool_call + tool_result pair.

    Usage:
        async with tool_event(req_id, "parser", "rxnorm_lookup", {"term": "x"}) as ctx:
            result = await rxnorm_lookup("x")
            ctx["result"] = result
    """
    tracer = get_tracer(request_id)
    tracer.emit(agent, "tool_call", {"tool": tool_name, "args": args})
    t0 = time.perf_counter()
    ctx: dict[str, Any] = {}
    try:
        yield ctx
        dur = (time.perf_counter() - t0) * 1000
        tracer.emit(
            agent,
            "tool_result",
            {"tool": tool_name, "summary": _summarize(ctx.get("result"))},
            duration_ms=dur,
        )
    except Exception as e:  # noqa: BLE001
        dur = (time.perf_counter() - t0) * 1000
        tracer.emit(agent, "error", {"tool": tool_name, "error": str(e)}, duration_ms=dur)
        raise


def _summarize(obj: Any, max_len: int = 200) -> str:
    """Render a tool result into a short string for the trace UI."""
    try:
        s = json.dumps(obj, default=str)
    except (TypeError, ValueError):
        s = str(obj)
    return s if len(s) <= max_len else s[:max_len] + "…"
