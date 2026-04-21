"""
Leaderboard route.

GET /api/leaderboard  — aggregated per-model stats from all game logs
                        reads from Firebase when available, falls back to local JSON files
"""

import glob
import json
import logging
import os
from collections import defaultdict

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

GAME_LOGS_DIR = os.getenv("GAME_LOGS_DIR", "game_logs")


def _aggregate_from_logs(logs: list[dict]) -> list[dict]:
    stats: dict[str, dict] = defaultdict(lambda: {
        "model": "",
        "provider": "",
        "games_played": 0,
        "wins": 0,
        "total_score": 0,
        "total_rounds_played": 0,
        "storyteller_successes": 0,
        "storyteller_rounds": 0,
    })

    for log in logs:
        cfg = log.get("game_configuration", {})
        rounds = log.get("rounds", [])
        if not rounds:
            continue

        game_params = cfg.get("game_parameters", cfg)
        players_cfg = cfg.get("players", game_params.get("players", []))
        name_to_model = {p["name"]: p["model"] for p in players_cfg}
        name_to_provider = {
            p["name"]: p.get("provider", p["model"].split("/")[0])
            for p in players_cfg
        }

        final_scores = rounds[-1].get("current_scores", {})
        if not final_scores:
            continue
        winner_name = max(final_scores, key=final_scores.get)

        for player_name, model in name_to_model.items():
            s = stats[model]
            s["model"] = model
            s["provider"] = name_to_provider.get(player_name, "")
            s["games_played"] += 1
            s["total_score"] += final_scores.get(player_name, 0)
            s["total_rounds_played"] += len(rounds)
            if player_name == winner_name:
                s["wins"] += 1

        for round_data in rounds:
            storyteller_name = round_data.get("storyteller")
            storyteller_votes = round_data.get("storyteller_votes", 0)
            num_non_storytellers = len(players_cfg) - 1
            if storyteller_name in name_to_model:
                model = name_to_model[storyteller_name]
                stats[model]["storyteller_rounds"] += 1
                if 0 < storyteller_votes < num_non_storytellers:
                    stats[model]["storyteller_successes"] += 1

    leaderboard = []
    for model, s in stats.items():
        gp = s["games_played"]
        sr = s["storyteller_rounds"]
        leaderboard.append({
            "model": model,
            "provider": s["provider"],
            "games_played": gp,
            "wins": s["wins"],
            "win_rate": round(s["wins"] / gp, 3) if gp else 0,
            "avg_score": round(s["total_score"] / gp, 1) if gp else 0,
            "avg_score_per_round": round(
                s["total_score"] / s["total_rounds_played"], 2
            ) if s["total_rounds_played"] else 0,
            "storyteller_success_rate": round(
                s["storyteller_successes"] / sr, 3
            ) if sr else 0,
        })

    leaderboard.sort(key=lambda x: (-x["win_rate"], -x["avg_score"]))
    return leaderboard


def _aggregate_leaderboard() -> list[dict]:
    from core.firebase_store import is_available as fb_available, list_games as fb_list_games

    if fb_available():
        logs = fb_list_games()
        if logs:
            return _aggregate_from_logs(logs)

    # Fall back to local JSON files
    pattern = os.path.join(GAME_LOGS_DIR, "dixit_game_log_*.json")
    logs = []
    for path in glob.glob(pattern):
        try:
            with open(path) as f:
                logs.append(json.load(f))
        except Exception as exc:
            logger.warning("Skipping %s: %s", path, exc)
    return _aggregate_from_logs(logs)


@router.get("/leaderboard")
async def get_leaderboard():
    return _aggregate_leaderboard()
