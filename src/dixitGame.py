import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from abc import ABC, abstractmethod
import random
import base64
from openai import OpenAI
import anthropic
import google.generativeai as genai
import requests

# from vision_models import ClaudeVision, GeminiVision, GrokVision, OpenAIVision, VisionAPI
from vision_models.grok_vision import GrokVision
from vision_models.vision_API import VisionAPI
from vision_models.claude_vision import ClaudeVision
from vision_models.gemini_vision import GeminiVision
from vision_models.openai_vision import OpenAIVision

ModelType = Literal[
    "gpt-4-vision", 
    "gpt-4-vision-preview", 
    "claude-3-opus", 
    "claude-3-sonnet", 
    "gemini-pro-vision", 
    "grok-vision"]

@dataclass
class Card:
    image_path: str

@dataclass
class Player:
    name: str
    cards: List[Card]
    score: int = 0


class DixitGame:
    def __init__(self, vision_api: VisionAPI):
        self.vision_api = vision_api
        self.players: List[Player] = []
        self.current_round: Optional[int] = None
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []

    def load_deck(self, image_directory: str):
        for filename in os.listdir(image_directory):
            if filename.endswith(('.jpg', '.png')):
                self.deck.append(Card(os.path.join(image_directory, filename)))
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
        with open(card_image, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        return self.vision_api.analyze_image(
            base64_image,
            "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure."
        )

    def select_matching_card(self, clue: str, hand: List[Card]) -> Card:
        scores = []
        for card in hand:
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

def create_vision_api(model: ModelType, api_key: str, **kwargs) -> VisionAPI:
    if model in ["gpt-4-vision", "gpt-4-vision-preview"]:
        return OpenAIVision(api_key, model)
    elif model in ["claude-3-opus", "claude-3-sonnet"]:
        return ClaudeVision(api_key, model)
    elif model == "gemini-pro-vision":
        return GeminiVision(api_key)
    elif model == "grok-vision":
        GROQ_API_URL = os.getenv("GROQ_API_URL")
        GROQ_API_URL = os.getenv("GROQ_API_KEY")
        if not GROQ_API_URL:
            raise ValueError("api_endpoint required for Grok Vision API")
        return GrokVision(GROQ_API_URL, GROQ_API_URL)
    else:
        raise ValueError(f"Unsupported model: {model}")

def play_game(
    image_directory: str,
    model: ModelType,
    api_key: str,
    num_ai_players: int = 3,
    **kwargs
) -> None:
    
    vision_api = create_vision_api(model, api_key, **kwargs)
    game = DixitGame(vision_api)
    game.load_deck(image_directory)
    
    ai_players = []
    for i in range(num_ai_players):
        player_name = f"AI_Player_{i+1}"
        game.add_player(player_name)
        ai_players.append(AIPlayer(vision_api))
        
    rounds = 0
    while rounds < 10 and any(p.score < 30 for p in game.players):
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
    play_game(
    image_directory="data/original",
    model="grok-vision",#"gpt-4-vision",  # or "claude-3-opus", "gemini-pro-vision", etc.
    api_key="your_api_key",
    num_ai_players=3,
    api_endpoint="https://api.grok.com/vision"  # only needed for Grok
)
 