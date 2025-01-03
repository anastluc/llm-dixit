import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
import random
import base64
import time

from vision_models.grok_vision import GrokVision
from vision_models.vision_API import VisionAPI
from vision_models.claude_vision import ClaudeVision
from vision_models.gemini_vision import GeminiVision
from vision_models.openai_vision import OpenAIVision

import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
import random
import base64
import time
import json
from datetime import datetime

import random

API_TIME_DELAY = 7

MLLM_Provider = Literal[
    "openai",
    "anthropic", 
    "google", 
    "groq-vision"]

@dataclass
class Card:
    image_path: str

@dataclass
class Player:
    name: str
    cards: List[Card]
    score: int = 0

    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.name == other.name


class DixitGame:
    def __init__(self):
        self.players: List[Player] = []
        self.current_round: Optional[int] = None
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []

    def load_deck(self, image_directory: str):
        for filename in os.listdir(image_directory):
            if filename.endswith(('.jpeg', '.png')):
                self.deck.append(Card(os.path.join(image_directory, filename)))
        
        # print(self.deck)
        random.shuffle(self.deck)

    def add_player(self, name: str):
        player = Player(name=name, cards=[])
        self.players.append(player)
        self._deal_cards(player, 6)

    def _deal_cards(self, player: Player, count: int):
        for _ in range(count):
            if self.deck:
                player.cards.append(self.deck.pop())

class AIPlayer:
    def __init__(self, vision_api: VisionAPI):
        self.vision_api = vision_api

    def generate_clue(self, card_image: str) -> str:
        print(f"Delaying {API_TIME_DELAY} seconds to avoid API's throttling")
        time.sleep(API_TIME_DELAY)

        with open(card_image, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        return self.vision_api.analyze_image(
            base64_image,
            "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure. Use from 2 up to 15 words."
        )

    def select_matching_card(self, clue: str, hand: List[Card]) -> tuple[Card, Dict[str, float]]:        
        scores = {}
        for card in hand:
            print(f"Delaying {API_TIME_DELAY} seconds to avoid API's throttling")
            time.sleep(API_TIME_DELAY)
            with open(card.image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            response = self.vision_api.analyze_image(
                base64_image,
                f"Rate how well this image matches the clue '{clue}' on a scale of 0-10. Return just a number, nothing else"
            )
            try:
                score = float(response.strip())
                scores[card.image_path] = score
                print(f"Card {card} is scored as {score} for this clue")
            except ValueError:
                scores[card.image_path] = 0
                print(f"Card {card} is scored as 0 for this clue as it had an error converting to number ({response.strip()})")
        
        best_card = max(hand, key=lambda x: scores[x.image_path])
        return best_card, scores

def create_vision_api(provider: MLLM_Provider, specific_model:str) -> VisionAPI:
    if provider == "openai":
        return OpenAIVision(specific_model)
    elif provider == "anthropic":
        return ClaudeVision(specific_model)
    elif provider == "google":
        return GeminiVision(specific_model)
    elif provider == "groq-vision":
        return GrokVision(specific_model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

class GameLogger:
    def __init__(self, output_dir: str = "game_logs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.game_log = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_round(self, round_data: dict):
        self.game_log.append(round_data)
        
    def save_log(self):
        filename = f"dixit_game_log_{self.timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.game_log, f, indent=2)
        return filepath

def play_game(
    image_directory: str,
    players,
    max_number_of_rounds = 10,
    score_to_win = 30,
    **kwargs
) -> None:
    logger = GameLogger()
    game = DixitGame()
    game.load_deck(image_directory)
    
    ai_players:List[AIPlayer] = []
    for i, api in enumerate(players):
        player_name = f"AI_{api.__class__.__name__}_{i+1}"
        game.add_player(player_name)
        ai_players.append(AIPlayer(api))
        
    rounds = 0
    while rounds < max_number_of_rounds and any(p.score < score_to_win for p in game.players):
        print(f"\nRound {rounds + 1}")
        round_log = {"round": rounds + 1}
        
        storyteller_idx = rounds % len(game.players)
        storyteller = game.players[storyteller_idx]
        ai_storyteller = ai_players[storyteller_idx]
        round_log["storyteller"] = storyteller.name
        
        storyteller_card = random.choice(storyteller.cards)
        clue = ai_storyteller.generate_clue(storyteller_card.image_path)
        print(f"\n{storyteller.name} (Storyteller) gives clue: {clue}")
        print(f"Storyteller selected card: {storyteller_card.image_path}")
        round_log.update({
            "clue": clue,
            "storyteller_card": storyteller_card.image_path,
        })
        
        played_cards = {storyteller: storyteller_card}
        round_log["played_cards"] = {}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                matching_card, card_scores = ai.select_matching_card(clue, player.cards)
                played_cards[player] = matching_card
                print(f"{player.name} played card: {matching_card.image_path}")
                round_log["played_cards"][player.name] = {
                    "selected_card": matching_card.image_path,
                    "card_scores": card_scores
                }
                
        cards = list(played_cards.values())
        random.shuffle(cards)
        
        votes = {}
        round_log["votes"] = {}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                vote, vote_scores = ai.select_matching_card(clue, cards)
                votes[player] = vote
                print(f"{player.name} voted for card: {vote.image_path}")
                round_log["votes"][player.name] = {
                    "selected_card": vote.image_path,
                    "card_scores": vote_scores
                }

        storyteller_votes = sum(1 for v in votes.values() if v == storyteller_card)
        round_log["storyteller_votes"] = storyteller_votes
        
        round_log["score_changes"] = {}
        if storyteller_votes == 0 or storyteller_votes == len(game.players) - 1:
            print("\nNo one or everyone found the storyteller's card!")
            for player in game.players:
                if player != storyteller:
                    player.score += 2
                    round_log["score_changes"][player.name] = 2
        else:
            storyteller.score += 3
            round_log["score_changes"][storyteller.name] = 3
            for player, vote in votes.items():
                if vote == storyteller_card:
                    player.score += 3
                    round_log["score_changes"][player.name] = round_log["score_changes"].get(player.name, 0) + 3
                    print(f"{player.name} found the storyteller's card! (+3 points)")
        
        for voter, voted_card in votes.items():
            for player, played_card in played_cards.items():
                if player != storyteller and voted_card == played_card and voter != player:
                    player.score += 1
                    round_log["score_changes"][player.name] = round_log["score_changes"].get(player.name, 0) + 1
                    print(f"{player.name} got a vote from {voter.name} for their card! (+1 point)")
        
        round_log["current_scores"] = {player.name: player.score for player in game.players}
        print("\nScores:")
        for player in game.players:
            print(f"{player.name}: {player.score}")
            
        logger.log_round(round_log)
        rounds += 1
        
    winner = max(game.players, key=lambda p: p.score)
    print(f"\nGame Over! Winner: {winner.name} with {winner.score} points")
    
    final_log_path = logger.save_log()
    print(f"\nGame log saved to: {final_log_path}")

if __name__ == "__main__":
    grok1 = create_vision_api("groq-vision", specific_model="llama-3.2-11b-vision-preview")
    grok2 = create_vision_api("groq-vision", specific_model="llama-3.2-90b-vision-preview")
    claude1 = create_vision_api("anthropic", specific_model="claude-3-opus-20240229")
    # claude2 = create_vision_api("anthropic", specific_model="claude-3-5-haiku-20241022")
    claude3 = create_vision_api("anthropic", specific_model="claude-3-5-sonnet-20241022")

    open1 = create_vision_api("openai", specific_model="gpt-4o")
    open2 = create_vision_api("openai", specific_model="gpt-4o-mini")
    
    # vision_apis = [grok1, grok2, claude1, claude2]
    ai_players = [claude1, grok1, grok2, claude3, open1, open2]
    # ai_players = [grok1, grok2, grok1]

    random.shuffle(ai_players)

    play_game(
        image_directory="data/original",
        players = ai_players,
        max_number_of_rounds = 5,
        score_to_win = 30
    )
 