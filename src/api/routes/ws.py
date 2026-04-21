"""
WebSocket route for live game streaming.

WS /ws/live/{game_id}

Clients connect and receive a stream of game events as JSON objects.
Past events are replayed immediately on connect (catch-up for late joiners).
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.events import bus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/live/{game_id}")
async def live_game(websocket: WebSocket, game_id: str):
    await websocket.accept()
    await bus.subscribe(game_id, websocket)
    logger.info("WS client connected to game %s", game_id)
    try:
        # Keep connection alive; events are pushed via EventBus.publish()
        while True:
            # Listen for client pings or close frames
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WS client disconnected from game %s", game_id)
    except Exception as exc:
        # StrictMode double-mount, proxy resets, or other transient errors
        logger.debug("WS handler exiting for game %s: %s", game_id, exc)
    finally:
        await bus.unsubscribe(game_id, websocket)
