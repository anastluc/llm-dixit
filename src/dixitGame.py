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

MLLM_Provider = Literal[
    "openai",
    "anthropic", 
    "google", 
    "grok-vision"]

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
        time_delay = 10
        print(f"Delaying {time_delay} seconds to avoid API's 429")
        time.sleep(time_delay)

        with open(card_image, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        return self.vision_api.analyze_image(
            base64_image,
            "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure. Use from 5 up to 50 words."
        )

    def select_matching_card(self, clue: str, hand: List[Card]) -> Card:
        time_delay = 10
        
        scores = []
        for card in hand:
            print(f"Delaying {time_delay} seconds to avoid API's 429")
            time.sleep(time_delay)
            with open(card.image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            response = self.vision_api.analyze_image(
                base64_image,
                f"Rate how well this image matches the clue '{clue}' on a scale of 0-10."
            )
            try:
                score = float(response.strip())
                scores.append((score, card))
            except ValueError:
                scores.append((0, card))
        return max(scores, key=lambda x: x[0])[1]

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

def play_game(
    image_directory: str,
    ai_players,
    max_number_of_rounds = 10,
    score_to_win = 30,
    **kwargs
) -> None:
    

    
    game = DixitGame()  # Initialize with first API
    game.load_deck("data/original")
    
    ai_players = []
    for i, api in enumerate(ai_players):
        player_name = f"AI_{api.__class__.__name__}_{i+1}"
        game.add_player(player_name)
        ai_players.append(AIPlayer(api))
        
    rounds = 0
    while rounds < max_number_of_rounds and any(p.score < score_to_win for p in game.players):
        print(f"\nRound {rounds + 1}")
        storyteller_idx = rounds % len(game.players)
        storyteller = game.players[storyteller_idx]
        ai_storyteller = ai_players[storyteller_idx]
        
        storyteller_card = random.choice(storyteller.cards)
        clue = ai_storyteller.generate_clue(storyteller_card.image_path)
        print(f"\n{storyteller.name} (Storyteller) gives clue: {clue}")
        
        played_cards = {storyteller: storyteller_card}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                matching_card = ai.select_matching_card(clue, player.cards)
                played_cards[player] = matching_card
                
        cards = list(played_cards.values())
        random.shuffle(cards)
        
        votes = {}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                vote = ai.select_matching_card(clue, cards)
                votes[player] = vote
                
        storyteller_votes = sum(1 for v in votes.values() if v == storyteller_card)
        if storyteller_votes == 0 or storyteller_votes == len(game.players) - 1:
            for player in game.players:
                if player != storyteller:
                    player.score += 2
        else:
            storyteller.score += 3
            for player, vote in votes.items():
                if vote == storyteller_card:
                    player.score += 3
                    
        print("\nScores:")
        for player in game.players:
            print(f"{player.name}: {player.score}")
            
        rounds += 1
        
    winner = max(game.players, key=lambda p: p.score)
    print(f"\nGame Over! Winner: {winner.name} with {winner.score} points")

if __name__ == "__main__":
    grok1 = create_vision_api("grok-vision", specific_model="llama-3.2-11b-vision-preview")
    grok2 = create_vision_api("grok-vision", specific_model="llama-3.2-90b-vision-preview")
    claude1 = create_vision_api("antropic", specific_model="claude-3-opus")
    claude2 = create_vision_api("anthropic", specific_model="claude-3-sonnet")
    
    # vision_apis = [grok1, grok2, claude1, claude2]
    ai_players = [grok1, grok2, grok1, grok2]

    play_game(
    image_directory="data/original",
    ai_players = ai_players,
    max_number_of_rounds = 10,
    score_to_win = 30
)
 
# if __name__ == "__main__":
#     # Create and run game for each player with their respective models
#     grok1 = create_vision_api("grok-vision", specific_model="llama-3.2-11b-vision-preview")
#     grok2 = create_vision_api("grok-vision", specific_model="llama-3.2-90b-vision-preview")
#     claude1 = create_vision_api("antropic", specific_model="claude-3-opus")
#     claude2 = create_vision_api("anthropic", specific_model="claude-3-sonnet")
    
#     # vision_apis = [grok1, grok2, claude1, claude2]
#     vision_apis = [grok1, grok2, grok1, grok2]
#     game = DixitGame(vision_apis[0])  # Initialize with first API
#     game.load_deck("data/original")
    
#     ai_players = []
#     for i, api in enumerate(vision_apis):
#         player_name = f"AI_{api.__class__.__name__}_{i+1}"
#         game.add_player(player_name)
#         ai_players.append(AIPlayer(api))