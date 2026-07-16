"""
WebSocket connection manager for real-time agent progress streaming.

Decision: we maintain a per-analysis-id set of WebSocket connections.
Multiple browser tabs analyzing the same issue all get the same stream.
Using asyncio.gather to broadcast keeps it non-blocking even with many
simultaneous connections.

Each message is a structured JSON event with a 'type' field so the
frontend can handle different event types (node_start, node_complete,
result, error) without parsing free-form text.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        # analysis_id -> set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, analysis_id: str) -> None:
        await websocket.accept()
        self._connections[analysis_id].add(websocket)
        logger.info("ws_connected", analysis_id=analysis_id)

    def disconnect(self, websocket: WebSocket, analysis_id: str) -> None:
        self._connections[analysis_id].discard(websocket)
        if not self._connections[analysis_id]:
            del self._connections[analysis_id]
        logger.info("ws_disconnected", analysis_id=analysis_id)

    async def broadcast(self, analysis_id: str, event: dict) -> None:
        """Send a JSON event to all connections for this analysis."""
        connections = self._connections.get(analysis_id, set()).copy()
        if not connections:
            return
        message = json.dumps(event)
        results = await asyncio.gather(
            *[ws.send_text(message) for ws in connections],
            return_exceptions=True,
        )
        # Clean up dead connections
        for ws, result in zip(connections, results):
            if isinstance(result, Exception):
                self._connections[analysis_id].discard(ws)

    async def send_node_start(self, analysis_id: str, node_name: str, node_index: int) -> None:
        await self.broadcast(analysis_id, {
            "type": "node_start",
            "node": node_name,
            "index": node_index,
            "total": 6,
        })

    async def send_node_complete(self, analysis_id: str, node_name: str, node_index: int, summary: str) -> None:
        await self.broadcast(analysis_id, {
            "type": "node_complete",
            "node": node_name,
            "index": node_index,
            "summary": summary,
        })

    async def send_result(self, analysis_id: str, result: dict) -> None:
        await self.broadcast(analysis_id, {
            "type": "result",
            "data": result,
        })

    async def send_error(self, analysis_id: str, error: str) -> None:
        await self.broadcast(analysis_id, {
            "type": "error",
            "message": error,
        })


# Global singleton — shared across all requests in the same process
manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return manager
