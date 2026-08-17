"""Live-update push over WebSocket, scoped per business.

Deliberately a signal channel, not a data channel: every message is just
`{"type": "invalidate", "keys": [...]}` naming which React Query keys are
now stale. The frontend still fetches the real data over the normal REST
endpoints — this only tells it *when* to, instead of waiting for the next
15-30s poll. That keeps the wire format trivial and means a client that
never connects (or whose socket drops) degrades gracefully to exactly the
polling behavior the app already had, not a broken one.

Every path operation in this app is a sync `def`, run by FastAPI in a
worker thread via anyio's threadpool — not on the event loop that actually
owns the WebSocket connections. `broadcast()` is the sync-safe entry point
services call; it hands the real (async) send off to that other loop via
`run_coroutine_threadsafe` rather than trying to await it from the wrong
thread, which would either deadlock or silently do nothing depending on
the anyio backend.
"""
import asyncio
import uuid
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, business_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[business_id].add(websocket)

    def disconnect(self, business_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[business_id].discard(websocket)
        if not self._connections[business_id]:
            self._connections.pop(business_id, None)

    async def _broadcast_async(self, business_id: uuid.UUID, message: dict) -> None:
        dead: list[WebSocket] = []
        for websocket in list(self._connections.get(business_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(business_id, websocket)

    def broadcast(self, business_id: uuid.UUID, message: dict) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast_async(business_id, message), self._loop)

    def notify(self, business_id: uuid.UUID | None, *keys: str) -> None:
        """The one method services actually call. business_id is typed
        nullable only because a couple of call sites already have an
        Optional on hand — never actually broadcasts for None."""
        if business_id is None:
            return
        self.broadcast(business_id, {"type": "invalidate", "keys": list(keys)})


manager = ConnectionManager()
