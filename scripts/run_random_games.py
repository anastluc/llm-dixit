"""
Run N randomised Dixit games using a given card set.

Usage:
    PYTHONPATH=src python scripts/run_random_games.py \
        --cards data/1_full \
        --num-games 10 \
        --players-per-game 4 \
        --models openai/gpt-4o anthropic/claude-3-5-sonnet google/gemini-2.0-flash \
        --prompt-styles creative deceptive \
        --max-rounds 8

`--cards` may be a local directory or a Firebase Storage collection name.
Each game randomly samples `--players-per-game` models from `--models`
and a prompt style from `--prompt-styles`.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.game import play_game


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cards", required=True, help="Local image dir or Firebase collection name")
    p.add_argument("--num-games", type=int, default=5)
    p.add_argument("--players-per-game", type=int, default=4)
    p.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Pool of model identifiers (e.g. openai/gpt-4o anthropic/claude-3-5-sonnet)",
    )
    p.add_argument(
        "--prompt-styles",
        nargs="+",
        default=["creative"],
        help="Pool of prompt styles to sample per game",
    )
    p.add_argument("--max-rounds", type=int, default=10)
    p.add_argument("--score-to-win", type=int, default=30)
    p.add_argument("--no-cache", action="store_true", help="Disable response cache")
    p.add_argument("--seed", type=int, help="Random seed for reproducibility")
    return p.parse_args()


async def run_one_game(idx: int, args: argparse.Namespace) -> dict:
    if args.players_per_game > len(args.models):
        raise ValueError(
            f"--players-per-game ({args.players_per_game}) > number of --models ({len(args.models)})"
        )
    chosen_models = random.sample(args.models, args.players_per_game)
    style = random.choice(args.prompt_styles)
    players = [{"model": m} for m in chosen_models]
    game_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx:03d}"
    logging.info("[Game %d/%d] id=%s style=%s models=%s", idx + 1, args.num_games, game_id, style, chosen_models)
    return await play_game(
        image_directory=args.cards,
        players=players,
        prompt_style=style,
        max_rounds=args.max_rounds,
        score_to_win=args.score_to_win,
        use_cache=not args.no_cache,
        game_id=game_id,
    )


async def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.seed is not None:
        random.seed(args.seed)

    summary = []
    for i in range(args.num_games):
        try:
            log = await run_one_game(i, args)
            winner = max(log["game_configuration"]["players"], key=lambda p: 0)  # placeholder
            final = log["rounds"][-1]["current_scores"] if log["rounds"] else {}
            summary.append({"game_id": log["game_id"], "final_scores": final})
        except Exception as exc:
            logging.exception("Game %d failed: %s", i + 1, exc)
            summary.append({"game_id": f"game_{i}", "error": str(exc)})

    print("\n=== Summary ===")
    for s in summary:
        print(s)


if __name__ == "__main__":
    asyncio.run(main())
