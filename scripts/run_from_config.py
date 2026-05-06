"""
Run Dixit games from a JSON run-configuration file.

Usage:
    PYTHONPATH=src python scripts/run_from_config.py path/to/runs.json

Config file schema (JSON):
{
  "defaults": {                  // optional, merged into each run
    "cards": "data/1_full",
    "max_rounds": 10,
    "score_to_win": 30,
    "use_cache": true,
    "prompt_style": "creative"
  },
  "runs": [
    {
      "name": "gpt4o-vs-claude",
      "trials": 3,
      "cards": "data/1_full",
      "prompt_style": "creative",
      "max_rounds": 8,
      "players": [
        {"model": "openai/gpt-4o", "name": "GPT-4o"},
        {"model": "anthropic/claude-3-5-sonnet", "prompt_style": "deceptive"}
      ]
    },
    {
      "name": "gemini-trio",
      "trials": 2,
      "cards": "original",
      "players": [
        {"model": "google/gemini-2.0-flash"},
        {"model": "google/gemini-1.5-pro"},
        {"model": "openai/gpt-4o-mini"}
      ]
    }
  ]
}

Per-player `prompt_style` overrides the run-level style.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.game import play_game


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("config", help="Path to JSON run-configuration file")
    p.add_argument("--continue-on-error", action="store_true", help="Don't abort on a failed trial")
    return p.parse_args()


def merge(defaults: dict, run: dict) -> dict:
    merged = {**defaults, **run}
    return merged


async def run_trial(run: dict, trial_idx: int) -> dict:
    game_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{run.get('name', 'run')}_{trial_idx:02d}"
    return await play_game(
        image_directory=run["cards"],
        players=run["players"],
        prompt_style=run.get("prompt_style", "creative"),
        max_rounds=run.get("max_rounds", 10),
        score_to_win=run.get("score_to_win", 30),
        use_cache=run.get("use_cache", True),
        game_id=game_id,
    )


async def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    with open(args.config) as f:
        cfg = json.load(f)
    defaults = cfg.get("defaults", {})
    runs = cfg["runs"]

    summary: list[dict] = []
    for run in runs:
        merged = merge(defaults, run)
        trials = merged.get("trials", 1)
        name = merged.get("name", "unnamed")
        logging.info("=== Run '%s' (%d trials) ===", name, trials)
        for t in range(trials):
            try:
                log = await run_trial(merged, t)
                final = log["rounds"][-1]["current_scores"] if log["rounds"] else {}
                summary.append({"run": name, "trial": t, "game_id": log["game_id"], "final_scores": final})
                logging.info("  trial %d done: %s", t, final)
            except Exception as exc:
                logging.exception("  trial %d FAILED: %s", t, exc)
                summary.append({"run": name, "trial": t, "error": str(exc)})
                if not args.continue_on_error:
                    raise

    out_path = Path("game_logs") / f"run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to {out_path}")
    for s in summary:
        print(s)


if __name__ == "__main__":
    asyncio.run(main())
