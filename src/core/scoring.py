from __future__ import annotations
"""
Pure scoring logic for a single Dixit round.

Dixit scoring rules:
- If 0 or ALL non-storyteller players voted for the storyteller's card:
    All non-storytellers +2 (storyteller gets nothing)
- Otherwise:
    Storyteller +3
    Each correct voter +3
- Bonus (always applied):
    Each non-storyteller whose card received at least one vote: +1 per vote received
"""

from dataclasses import dataclass


@dataclass
class RoundResult:
    score_changes: dict[str, int]  # player_name -> delta
    storyteller_found_by_all: bool
    storyteller_found_by_none: bool
    storyteller_votes: int


def compute_score_changes(
    storyteller_name: str,
    all_player_names: list[str],
    votes: dict[str, str],           # voter_name -> voted_card_path
    played_cards: dict[str, str],    # player_name -> card_path
    storyteller_card_path: str,
) -> RoundResult:
    """
    Compute score deltas for one round.

    Args:
        storyteller_name: Name of the storyteller player.
        all_player_names: All players in the game (including storyteller).
        votes: Mapping from voter name to the card path they voted for.
        played_cards: Mapping from player name to the card path they played.
        storyteller_card_path: Path of the storyteller's card.

    Returns:
        RoundResult with per-player score changes.
    """
    non_storytellers = [p for p in all_player_names if p != storyteller_name]
    storyteller_votes = sum(1 for card in votes.values() if card == storyteller_card_path)

    changes: dict[str, int] = {name: 0 for name in all_player_names}

    found_by_all = storyteller_votes == len(non_storytellers)
    found_by_none = storyteller_votes == 0

    if found_by_none or found_by_all:
        for name in non_storytellers:
            changes[name] += 2
    else:
        changes[storyteller_name] += 3
        for voter, card in votes.items():
            if card == storyteller_card_path:
                changes[voter] += 3

    # Bonus: +1 per vote a non-storyteller's card received from other players
    for voter, voted_card in votes.items():
        for player_name, played_card in played_cards.items():
            if player_name != storyteller_name and voted_card == played_card and voter != player_name:
                changes[player_name] += 1

    # Remove zero-change entries for cleaner logs
    changes = {k: v for k, v in changes.items() if v != 0}

    return RoundResult(
        score_changes=changes,
        storyteller_found_by_all=found_by_all,
        storyteller_found_by_none=found_by_none,
        storyteller_votes=storyteller_votes,
    )
