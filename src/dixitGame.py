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

API_TIME_DELAY = 10

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
        print(f"Delaying {API_TIME_DELAY} seconds to avoid API's 429")
        time.sleep(API_TIME_DELAY)

        with open(card_image, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        return self.vision_api.analyze_image(
            base64_image,
            "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure. Use from 5 up to 50 words."
        )

    def select_matching_card(self, clue: str, hand: List[Card]) -> Card:        
        scores = []
        for card in hand:
            print(f"Delaying {API_TIME_DELAY} seconds to avoid API's 429")
            time.sleep(API_TIME_DELAY)
            with open(card.image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            response = self.vision_api.analyze_image(
                base64_image,
                f"Rate how well this image matches the clue '{clue}' on a scale of 0-10. Return just a number, nothing else"
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
    players,
    max_number_of_rounds = 10,
    score_to_win = 30,
    **kwargs
) -> None:
    

    
    game = DixitGame()  # Initialize with first API
    game.load_deck(image_directory)
    
    ai_players:List[AIPlayer] = []
    for i, api in enumerate(players):
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
        print(f"Storyteller selected card: {storyteller_card.image_path}")
        
        played_cards = {storyteller: storyteller_card}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                matching_card = ai.select_matching_card(clue, player.cards)
                played_cards[player] = matching_card
                print(f"{player.name} played card: {matching_card.image_path}")
                
        cards = list(played_cards.values())
        random.shuffle(cards)
        
        votes = {}
        for player, ai in zip(game.players, ai_players):
            if player != storyteller:
                vote = ai.select_matching_card(clue, cards)
                votes[player] = vote
                print(f"{player.name} voted for card: {vote.image_path}")

        # Count votes for storyteller's card
        storyteller_votes = sum(1 for v in votes.values() if v == storyteller_card)
        
        # Calculate scores for the round
        if storyteller_votes == 0 or storyteller_votes == len(game.players) - 1:
            # All players except storyteller get 2 points
            print("\nNo one or everyone found the storyteller's card!")
            for player in game.players:
                if player != storyteller:
                    player.score += 2
        else:
            # Storyteller and correct guessers get 3 points
            storyteller.score += 3
            for player, vote in votes.items():
                if vote == storyteller_card:
                    player.score += 3
                    print(f"{player.name} found the storyteller's card! (+3 points)")
        
        # Add points for players whose cards were voted for by others
        for voter, voted_card in votes.items():
            for player, played_card in played_cards.items():
                if player != storyteller and voted_card == played_card and voter != player:
                    player.score += 1
                    print(f"{player.name} got a vote from {voter.name} for their card! (+1 point)")
                    
        print("\nScores:")
        for player in game.players:
            print(f"{player.name}: {player.score}")
            
        rounds += 1
        
    winner = max(game.players, key=lambda p: p.score)
    print(f"\nGame Over! Winner: {winner.name} with {winner.score} points")

if __name__ == "__main__":
    grok1 = create_vision_api("groq-vision", specific_model="llama-3.2-11b-vision-preview")
    grok2 = create_vision_api("groq-vision", specific_model="llama-3.2-90b-vision-preview")
    claude1 = create_vision_api("antropic", specific_model="claude-3-opus")
    claude2 = create_vision_api("anthropic", specific_model="claude-3-sonnet")
    
    # vision_apis = [grok1, grok2, claude1, claude2]
    ai_players = [grok1, grok2, grok1, grok2]

    play_game(
        image_directory="data/original",
        ai_players = ai_players,
        max_number_of_rounds = 3,
        score_to_win = 30
    )
 