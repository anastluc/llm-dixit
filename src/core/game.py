from __future__ import annotations
"""
Async Dixit game engine.

Usage:
    asyncio.run(play_game(image_directory="data/1_full", players=[...]))

Each player entry is a dict:
    {"model": "openai/gpt-4o", "name": "GPT-4o"}   # name is optional

The event_bus (if provided) receives real-time events during play,
consumed by the WebSocket route for live streaming.
"""

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from core.cache import get_cache
from core.prompts import PromptStyle, get_prompt_style
from core.scoring import compute_score_changes
from vision.base import VisionAPI
from vision.factory import create_vision_client

if TYPE_CHECKING:
    from api.events import EventBus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Card:
    image_path: str  # local file path OR https:// URL

    def to_dict(self) -> dict:
        return {"image_path": self.image_path}


@dataclass
class Player:
    name: str
    model: str
    provider_label: str
    prompt_style: str = "creative"
    cards: list[Card] = field(default_factory=list)
    score: int = 0

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Player) and self.name == other.name

    def to_dict(self) -> dict:
        return {"name": self.name, "model": self.model, "provider": self.provider_label, "prompt_style": self.prompt_style, "score": self.score}


# ---------------------------------------------------------------------------
# AI Player — wraps a vision API
# ---------------------------------------------------------------------------

class AIPlayer:
    def __init__(self, player: Player, vision_api: VisionAPI, style: PromptStyle, use_cache: bool = True):
        self.player = player
        self.vision_api = vision_api
        self.style = style
        self.use_cache = use_cache
        self._cache = get_cache()

    async def _call(self, image_path: str, prompt: str, max_tokens: int, temperature: float) -> str:
        if self.use_cache:
            cached = self._cache.get(self.player.model, image_path, prompt)
            if cached is not None:
                return cached

        response = await self.vision_api.analyze_image(image_path, prompt, max_tokens, temperature)
        if not response:
            logger.warning("Empty response from %s for %s — skipping cache", self.player.model, image_path)
            return ""
        response = response.strip()

        if self.use_cache:
            self._cache.set(self.player.model, image_path, prompt, response)
        return response

    async def generate_clue(self, card: Card) -> str:
        return await self._call(card.image_path, self.style.clue_prompt, self.style.max_tokens, self.style.temperature)

    async def score_card(self, card: Card, clue: str) -> float:
        if not clue:
            return 5.0
        prompt = self.style.vote_prompt.format(clue=clue)
        raw = await self._call(card.image_path, prompt, 16, self.style.temperature)
        try:
            # Accept the first token that looks like a number (handles "7/10", "7.", "7,", etc.)
            first = raw.strip().split()[0].rstrip('.,/').split('/')[0]
            return float(first)
        except (ValueError, IndexError):
            logger.warning("Could not parse score from '%s' for %s, defaulting to 5", raw[:80], card.image_path)
            return 5.0

    async def select_best_card(self, cards: list[Card], clue: str) -> tuple[Card, dict[str, float]]:
        scores_list = await asyncio.gather(*[self.score_card(c, clue) for c in cards])
        scores = {c.image_path: s for c, s in zip(cards, scores_list)}
        best = max(cards, key=lambda c: scores[c.image_path])
        return best, scores


# ---------------------------------------------------------------------------
# Deck / game state
# ---------------------------------------------------------------------------

class Deck:
    def __init__(self, image_directory: str):
        """Load cards from a local directory or a Firebase Storage collection name.

        If ``image_directory`` is a path that exists on disk, images are loaded
        from there.  Otherwise it is treated as a Firebase Storage collection name
        and cards are loaded as public URLs.
        """
        self.cards: list[Card] = []
        if os.path.isdir(image_directory):
            for fn in os.listdir(image_directory):
                if fn.lower().endswith((".jpg", ".jpeg", ".png")):
                    self.cards.append(Card(os.path.join(image_directory, fn)))
        else:
            # Firebase Storage collection
            from core.firebase_storage import get_collection_urls, is_available as storage_ok
            if not storage_ok():
                raise ValueError(
                    f"Image directory '{image_directory}' does not exist locally "
                    "and Firebase Storage is not configured."
                )
            urls = get_collection_urls(image_directory)
            if not urls:
                raise ValueError(f"Firebase collection '{image_directory}' is empty or not found.")
            for _filename, url in urls:
                self.cards.append(Card(url))
        if not self.cards:
            raise ValueError(f"No card images found in '{image_directory}'.")
        random.shuffle(self.cards)

    def deal(self, count: int) -> list[Card]:
        dealt, self.cards = self.cards[:count], self.cards[count:]
        return dealt

    def __len__(self) -> int:
        return len(self.cards)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class GameLogger:
    def __init__(self, game_id: str, output_dir: str = "game_logs"):
        self.game_id = game_id
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._log: dict = {"game_id": game_id, "game_configuration": {}, "rounds": []}

    def log_config(self, params: dict) -> None:
        self._log["game_configuration"] = params

    def log_round(self, round_data: dict) -> None:
        self._log["rounds"].append(round_data)

    def save(self) -> str:
        import json
        from core.firebase_store import save_game, is_available as firebase_available

        # Always save locally as backup / when Firebase is not configured
        path = os.path.join(self.output_dir, f"dixit_game_log_{self.game_id}.json")
        with open(path, "w") as f:
            json.dump(self._log, f, indent=2)

        if firebase_available():
            save_game(self.game_id, self._log)

        return path


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

async def play_game(
    image_directory: str,
    players: list[dict],
    prompt_style: str = "creative",
    max_rounds: int = 10,
    score_to_win: int = 30,
    use_cache: bool = True,
    game_id: str | None = None,
    event_bus: "EventBus | None" = None,
) -> dict:
    """
    Run a full Dixit game asynchronously.

    Args:
        image_directory: Path to folder of card images.
        players: List of dicts with at least "model" key, optional "name".
                 e.g. [{"model": "openai/gpt-4o"}, {"model": "anthropic/claude-3-5-sonnet"}]
        prompt_style: One of "creative", "deceptive", "minimalist", "narrative".
        max_rounds: Maximum number of rounds to play.
        score_to_win: Score at which the game ends early.
        use_cache: Whether to use the SQLite response cache.
        game_id: Unique identifier for this game (used in log filenames and WS routing).
        event_bus: Optional EventBus for live WebSocket streaming.

    Returns:
        Final game log as a dict.
    """
    if game_id is None:
        game_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    deck = Deck(image_directory)
    logger_obj = GameLogger(game_id)

    # Build players — each can have its own prompt style
    game_players: list[Player] = []
    ai_players: list[AIPlayer] = []

    for i, spec in enumerate(players):
        model = spec["model"]
        name = spec.get("name") or f"{model.split('/')[-1]}_{i+1}"
        provider_label = model.split("/")[0] if "/" in model else spec.get("provider", "unknown")
        player_style_name = spec.get("prompt_style") or prompt_style
        player_style = get_prompt_style(player_style_name)
        player = Player(name=name, model=model, provider_label=provider_label, prompt_style=player_style_name)
        player.cards = deck.deal(6)
        game_players.append(player)

        vision_api = create_vision_client(model, spec.get("provider"))
        ai_players.append(AIPlayer(player, vision_api, player_style, use_cache=use_cache))

    # Log config
    config = {
        "timestamp": game_id,
        "prompt_style": prompt_style,
        "image_directory": image_directory,
        "max_rounds": max_rounds,
        "score_to_win": score_to_win,
        "use_cache": use_cache,
        "deck_size": len(deck) + 6 * len(game_players),
        "players": [p.to_dict() for p in game_players],
    }
    logger_obj.log_config(config)

    async def emit(event: dict) -> None:
        if event_bus:
            await event_bus.publish(game_id, event)

    # Announce game config so live subscribers can show player/model info immediately
    await emit({
        "type": "game_config",
        "players": [{"name": p.name, "model": p.model, "prompt_style": p.prompt_style} for p in game_players],
        "prompt_style": prompt_style,
    })

    # Game loop
    round_num = 0
    while round_num < max_rounds and all(p.score < score_to_win for p in game_players):
        round_num += 1
        logger.info("=== Round %d ===", round_num)
        await emit({"type": "round_start", "round": round_num})

        storyteller_idx = (round_num - 1) % len(game_players)
        storyteller_player = game_players[storyteller_idx]
        storyteller_ai = ai_players[storyteller_idx]

        # Storyteller picks a card and generates a clue
        storyteller_card = random.choice(storyteller_player.cards)
        clue = await storyteller_ai.generate_clue(storyteller_card)
        if not clue:
            clue = "mysterious"
            logger.warning("%s returned empty clue — using fallback '%s'", storyteller_player.name, clue)
        logger.info("%s (storyteller) clue: %s", storyteller_player.name, clue)
        await emit({
            "type": "clue_generated",
            "round": round_num,
            "storyteller": storyteller_player.name,
            "clue": clue,
            "storyteller_card": storyteller_card.image_path,
        })

        # Non-storytellers pick their best card concurrently
        non_storyteller_pairs = [
            (game_players[i], ai_players[i])
            for i in range(len(game_players))
            if i != storyteller_idx
        ]

        async def _pick_card(player: Player, ai: AIPlayer) -> tuple[str, Card, dict[str, float]]:
            card, scores = await ai.select_best_card(player.cards, clue)
            return player.name, card, scores

        pick_results = await asyncio.gather(*[_pick_card(p, a) for p, a in non_storyteller_pairs])

        played_cards: dict[str, str] = {storyteller_player.name: storyteller_card.image_path}
        played_card_objects: dict[str, Card] = {storyteller_player.name: storyteller_card}
        round_log_played: dict[str, dict] = {}

        for pname, card, scores in pick_results:
            played_cards[pname] = card.image_path
            played_card_objects[pname] = card
            round_log_played[pname] = {"selected_card": card.image_path, "card_scores": scores}
            await emit({"type": "card_selected", "round": round_num, "player": pname, "card": card.image_path})

        # Shuffle all played cards for the voting phase
        all_played = list(played_card_objects.values())
        random.shuffle(all_played)

        # All non-storytellers vote concurrently
        async def _vote(player: Player, ai: AIPlayer) -> tuple[str, Card, dict[str, float]]:
            card, scores = await ai.select_best_card(all_played, clue)
            return player.name, card, scores

        vote_results = await asyncio.gather(*[_vote(p, a) for p, a in non_storyteller_pairs])

        votes: dict[str, str] = {}  # voter_name -> card_path
        round_log_votes: dict[str, dict] = {}
        for vname, card, scores in vote_results:
            votes[vname] = card.image_path
            round_log_votes[vname] = {"selected_card": card.image_path, "card_scores": scores}
            await emit({"type": "vote_cast", "round": round_num, "player": vname, "voted_card": card.image_path})

        # Score
        result = compute_score_changes(
            storyteller_name=storyteller_player.name,
            all_player_names=[p.name for p in game_players],
            votes=votes,
            played_cards=played_cards,
            storyteller_card_path=storyteller_card.image_path,
        )
        for player in game_players:
            player.score += result.score_changes.get(player.name, 0)

        current_scores = {p.name: p.score for p in game_players}
        logger.info("Scores after round %d: %s", round_num, current_scores)
        await emit({
            "type": "round_scored",
            "round": round_num,
            "storyteller_votes": result.storyteller_votes,
            "score_changes": result.score_changes,
            "current_scores": current_scores,
        })

        # Deal replacement cards (fix: players always have cards)
        for player in game_players:
            # Remove the card that was played this round
            played_path = played_cards.get(player.name)
            player.cards = [c for c in player.cards if c.image_path != played_path]
            # Deal one replacement if deck has cards
            replacement = deck.deal(1)
            player.cards.extend(replacement)

        logger_obj.log_round({
            "round": round_num,
            "storyteller": storyteller_player.name,
            "clue": clue,
            "storyteller_card": storyteller_card.image_path,
            "played_cards": round_log_played,
            "votes": round_log_votes,
            "storyteller_votes": result.storyteller_votes,
            "score_changes": result.score_changes,
            "current_scores": current_scores,
        })

    winner = max(game_players, key=lambda p: p.score)
    logger.info("Game over! Winner: %s (%d pts)", winner.name, winner.score)
    await emit({
        "type": "game_over",
        "winner": winner.name,
        "winner_score": winner.score,
        "final_scores": {p.name: p.score for p in game_players},
    })

    path = logger_obj.save()
    logger.info("Log saved: %s", path)
    return logger_obj._log
