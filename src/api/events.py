from __future__ import annotations
"""
In-memory pub/sub event bus for live game streaming over WebSockets.

Games publish events via publish(); WebSocket connections subscribe via subscribe().
"""

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        # game_id -> list of connected WebSocket clients
        self._subscribers: dict[str, list[WebSocket]] = defaultdict(list)
        # game_id -> list of past events (for late joiners to catch up)
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, game_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._subscribers[game_id].append(ws)

        # Replay past events to the new subscriber
        for event in self._history.get(game_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                break

    async def unsubscribe(self, game_id: str, ws: WebSocket) -> None:
        async with self._lock:
            subs = self._subscribers.get(game_id, [])
            if ws in subs:
                subs.remove(ws)

    async def publish(self, game_id: str, event: dict) -> None:
        self._history[game_id].append(event)

        dead: list[WebSocket] = []
        for ws in list(self._subscribers.get(game_id, [])):
            try:
                await ws.send_json(event)
            except Exception as exc:
                logger.debug("WS send failed (%s), marking for removal", exc)
                dead.append(ws)

        async with self._lock:
            for ws in dead:
                subs = self._subscribers.get(game_id, [])
                if ws in subs:
                    subs.remove(ws)

    def clear(self, game_id: str) -> None:
        self._subscribers.pop(game_id, None)
        self._history.pop(game_id, None)


# Singleton used across the app
bus = EventBus()
