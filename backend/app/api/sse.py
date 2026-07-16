"""
Server-Sent Events (SSE) progress endpoint.

Key fix: pre-create the queue when SSE connects, so push_event
never drops events because the queue doesn't exist yet.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# analysis_id -> asyncio.Queue
_queues: dict[str, asyncio.Queue] = {}
_lock = asyncio.Lock()


async def get_or_create_queue(analysis_id: str) -> asyncio.Queue:
    async with _lock:
        if analysis_id not in _queues:
            _queues[analysis_id] = asyncio.Queue()
        return _queues[analysis_id]


async def push_event(analysis_id: str, event: dict):
    """Push an event. Queue must already exist (created by SSE connect)."""
    if analysis_id and analysis_id in _queues:
        await _queues[analysis_id].put(event)


def cleanup_queue(analysis_id: str):
    _queues.pop(analysis_id, None)


@router.get("/progress/{analysis_id}")
async def sse_progress(analysis_id: str):
    # Pre-create queue immediately so push_event never misses events
    queue = await get_or_create_queue(analysis_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            cleanup_queue(analysis_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
