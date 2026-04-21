from __future__ import annotations
"""
Game management routes.

POST /api/games        — start a new game (runs in background)
GET  /api/games        — list all finished game logs
GET  /api/games/{id}   — full log for a specific game
GET  /api/prompt-styles — list available prompt styles
"""

import glob
import json
import logging
import os

import httpx
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.events import bus
from core.firebase_store import get_game as fb_get_game, list_games as fb_list_games, is_available as fb_available, clear_all_games as fb_clear_all
from core.game import play_game
from core.model_filter import is_vision_chat
from core.prompts import PROMPT_STYLES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

GAME_LOGS_DIR = os.getenv("GAME_LOGS_DIR", "game_logs")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class PlayerSpec(BaseModel):
    model: str
    name: Optional[str] = None
    provider: Optional[str] = None
    prompt_style: Optional[str] = None


class StartGameRequest(BaseModel):
    players: List[PlayerSpec]
    prompt_style: str = "creative"
    max_rounds: int = 10
    score_to_win: int = 30
    use_cache: bool = True
    image_directory: str = "data/1_full"


class StartGameResponse(BaseModel):
    game_id: str
    message: str
    live_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_log(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _summarise(log: dict, game_id: str | None = None) -> dict:
    """Extract list-view summary fields from a raw game log dict."""
    cfg = log.get("game_configuration", {})
    game_params = cfg.get("game_parameters", cfg)
    players_cfg = cfg.get("players", game_params.get("players", []))
    rounds = log.get("rounds", [])
    final_scores = rounds[-1].get("current_scores", {}) if rounds else {}
    winner = max(final_scores, key=final_scores.get) if final_scores else None
    return {
        "game_id": game_id or log.get("game_id", ""),
        "timestamp": cfg.get("timestamp", game_params.get("timestamp", "")),
        "prompt_style": cfg.get("prompt_style", ""),
        "prompt_style_name": cfg.get("prompt_style_name", ""),
        "players": [p.get("name") for p in players_cfg],
        "models": [p.get("model") for p in players_cfg],
        "rounds_played": len(rounds),
        "max_rounds": cfg.get("max_rounds", game_params.get("max_number_of_rounds", 10)),
        "winner": winner,
        "final_scores": final_scores,
    }


def _list_logs_local() -> list[dict]:
    """Fallback: read game summaries from local JSON files."""
    pattern = os.path.join(GAME_LOGS_DIR, "dixit_game_log_*.json")
    logs = []
    for path in sorted(glob.glob(pattern), reverse=True):
        try:
            log = _load_log(path)
            fname = os.path.basename(path)
            game_id = log.get("game_id") or fname.replace("dixit_game_log_", "").replace(".json", "")
            logs.append(_summarise(log, game_id))
        except Exception as exc:
            logger.warning("Could not read log %s: %s", path, exc)
    return logs


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/prompt-styles")
async def list_prompt_styles():
    return [
        {
            "id": k,
            "name": v.name,
            "description": v.description,
            "clue_prompt": v.clue_prompt,
            "vote_prompt": v.vote_prompt,
            "temperature": v.temperature,
            "max_tokens": v.max_tokens,
        }
        for k, v in PROMPT_STYLES.items()
    ]


# Popular vision models shown first; others follow alphabetically.
# Verified against OpenRouter /api/v1/models (2025-04).
_POPULAR_VISION_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "google/gemini-2.5-flash",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-scout",
    "meta-llama/llama-3.2-11b-vision-instruct",
    "x-ai/grok-4",
    "mistralai/pixtral-large-2411",
    "qwen/qwen-vl-plus",
]


_COMPATIBLE_MODELS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data", "compatible_models.json",
)


def _load_compatible_models() -> list[dict] | None:
    """Return [{id, name}, …] from the compatibility-probe output, or None if absent."""
    path = os.getenv("COMPATIBLE_MODELS_FILE", _COMPATIBLE_MODELS_PATH)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        models = data.get("models", [])
        if models:
            logger.info("Loaded %d compatible models from %s (updated %s)", len(models), path, data.get("updated_at", "?"))
            return models
    except Exception as exc:
        logger.warning("Could not read compatible_models.json: %s", exc)
    return None


@router.get("/models")
async def list_vision_models():
    """Return vision-capable models.

    Priority:
    1. data/compatible_models.json — written by the compatibility probe script;
       contains only models that have been verified to work with the game prompts.
    2. Live OpenRouter catalogue filtered to vision models — used when the probe
       has not been run yet.
    3. Hardcoded fallback list — used when OpenRouter is unreachable.
    """
    # 1. Compatibility-probe allowlist
    compatible = _load_compatible_models()
    if compatible is not None:
        popular_set = {m: i for i, m in enumerate(_POPULAR_VISION_MODELS)}
        compatible.sort(key=lambda m: (popular_set.get(m["id"], len(_POPULAR_VISION_MODELS)), m["id"]))
        return compatible

    # 2. Live OpenRouter catalogue
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return [{"id": m, "name": m} for m in _POPULAR_VISION_MODELS]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code != 200:
            raise ValueError(f"OpenRouter returned {resp.status_code}")

        all_models = resp.json().get("data", [])

        vision_models = [m for m in all_models if is_vision_chat(m)]
        popular_set = {m: i for i, m in enumerate(_POPULAR_VISION_MODELS)}
        vision_models.sort(key=lambda m: (popular_set.get(m["id"], len(_POPULAR_VISION_MODELS)), m["id"]))
        return [{"id": m["id"], "name": m.get("name", m["id"])} for m in vision_models]

    except Exception as exc:
        logger.warning("Could not fetch OpenRouter models: %s — using fallback list", exc)
        return [{"id": m, "name": m} for m in _POPULAR_VISION_MODELS]


@router.get("/games")
async def list_games():
    if fb_available():
        docs = fb_list_games()
        if docs:
            return [_summarise(d, d.get("game_id")) for d in docs]
    return _list_logs_local()


@router.delete("/games")
async def delete_all_games():
    """Wipe every game from Firestore (and local log files)."""
    # Clear Firestore
    deleted_fb = fb_clear_all() if fb_available() else 0

    # Clear local JSON logs
    import glob as _glob
    deleted_local = 0
    for path in _glob.glob(os.path.join(GAME_LOGS_DIR, "dixit_game_log_*.json")):
        try:
            os.remove(path)
            deleted_local += 1
        except Exception as exc:
            logger.warning("Could not delete local log %s: %s", path, exc)

    return {"deleted_firestore": deleted_fb, "deleted_local": deleted_local}


@router.get("/games/{game_id}")
async def get_game(game_id: str):
    if fb_available():
        doc = fb_get_game(game_id)
        if doc:
            return doc

    # Local file fallback
    path = os.path.join(GAME_LOGS_DIR, f"dixit_game_log_{game_id}.json")
    if os.path.isfile(path):
        return _load_log(path)
    for p in glob.glob(os.path.join(GAME_LOGS_DIR, "dixit_game_log_*.json")):
        try:
            log = _load_log(p)
            if log.get("game_id") == game_id:
                return log
        except Exception:
            continue
    raise HTTPException(status_code=404, detail=f"Game '{game_id}' not found")


@router.post("/games", response_model=StartGameResponse)
async def start_game(req: StartGameRequest, background_tasks: BackgroundTasks):
    from datetime import datetime
    game_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    players = [p.model_dump() for p in req.players]

    async def _run():
        try:
            await play_game(
                image_directory=req.image_directory,
                players=players,
                prompt_style=req.prompt_style,
                max_rounds=req.max_rounds,
                score_to_win=req.score_to_win,
                use_cache=req.use_cache,
                game_id=game_id,
                event_bus=bus,
            )
        except Exception as exc:
            logger.exception("Game %s failed: %s", game_id, exc)
            await bus.publish(game_id, {"type": "error", "message": str(exc)})

    background_tasks.add_task(_run)

    return StartGameResponse(
        game_id=game_id,
        message="Game started",
        live_url=f"/live/{game_id}",
    )
