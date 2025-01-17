import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
import random
import time

from vision_models.groq_vision import GroqVision
from vision_models.vision_API import VisionAPI
from vision_models.claude_vision import ClaudeVision
from vision_models.gemini_vision import GeminiVision
from vision_models.openai_vision import OpenAIVision
from vision_models.xai_vision import XAI_Vision

import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
import random
import base64
import time
import json
from datetime import datetime

import random

from image_cache import ImageAnalysisCache

MLLM_Provider = Literal[
    "openai",
    "anthropic", 
    "google", 
    "groq-vision",
    "xai"]

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

    def to_dict(self):
        return {
            'name': self.name,
            'cards': str(self.cards),
            'score': self.score
        }


class DixitGame:
    def __init__(self):
        self.players: List[Player] = []
        self.current_round: Optional[int] = None
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []

    def load_deck(self, image_directory: str):
        for filename in os.listdir(image_directory):
            if filename.endswith(('.jpeg', '.jpg', '.png')):
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
    def __init__(self, model, vision_api: VisionAPI):
        self.model = str(model)
        self.vision_api = vision_api
    
    def to_dict(self):
        return {
            'model': self.model,
            'vision_api': str(self.vision_api.__class__.__name__)
        }

    def generate_clue(self, card_image: str) -> str:

        GEN_CLUE_PROMPT = "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure. Use from 2 up to 15 words."
        cache = ImageAnalysisCache()
    
        # Try to get cached response
        cached_response = cache.get_cached_response(self.model, card_image, GEN_CLUE_PROMPT)
        if cached_response is not None:
            return cached_response
        
        try:
            # Assuming original API call code is here
            response = self.vision_api.analyze_image(
                image_path =card_image,#base64_image,
                prompt = GEN_CLUE_PROMPT
            )
            
            # Cache the response
            cache.cache_response(self.model, card_image, GEN_CLUE_PROMPT, response)
            
            return response
        except Exception as e:
            print(f"Error analyzing image: {e}")
            raise
 

    def select_matching_card(self, clue: str, hand: List[Card]) -> tuple[Card, Dict[str, float]]:        
        scores = {}
        cache = ImageAnalysisCache()
        RATE_CARD_WITH_CLUE_PROMPT = f"Rate how well this image matches the clue '{clue}' on a scale of 0-10. Return just a number, nothing else"

        for card in hand:
                # Try to get cached response
            cached_response = cache.get_cached_response(self.model, card.image_path, RATE_CARD_WITH_CLUE_PROMPT)
            
            if cached_response is not None:
                response = cached_response
            else:
            
                try:
                    response = self.vision_api.analyze_image(
                        card.image_path,
                        RATE_CARD_WITH_CLUE_PROMPT
                    )
                    cache.cache_response(self.model, card.image_path, RATE_CARD_WITH_CLUE_PROMPT, response)
        
                    
                except Exception as e:
                    print(f"Error analyzing image: {e}")
                    raise

                    
            try:
                score = float(response.strip())
                scores[card.image_path] = score
                print(f"Card {card} is scored as {score} for this clue")
            except ValueError:
                scores[card.image_path] = 0
                print(f"Card {card} is scored as 0 for this clue as it had an error converting to number ({response.strip()})")
        
        print(hand)
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
        return GroqVision(specific_model)
    elif provider == "xai":
        return XAI_Vision(specific_model)
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
        
    def _json_default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
        
    def save_log(self):
        filename = f"dixit_game_log_{self.timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.game_log, f, indent=2, default=self._json_default)
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
        ai_players.append(AIPlayer(api.model,api))
        
    rounds = 0
    while rounds < max_number_of_rounds and any(p.score < score_to_win for p in game.players):
        print(f"\nRound {rounds + 1}")
        round_log = {"round": rounds + 1}
        
        storyteller_idx = rounds % len(game.players)
        storyteller = game.players[storyteller_idx]
        ai_storyteller = ai_players[storyteller_idx]
        round_log["storyteller"] = storyteller.name


        round_log["players"] = [player.to_dict() for player in ai_players]
        
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
    groq1 = create_vision_api("groq-vision", specific_model="llama-3.2-11b-vision-preview")
    groq2 = create_vision_api("groq-vision", specific_model="llama-3.2-90b-vision-preview")

    claude1 = create_vision_api("anthropic", specific_model="claude-3-opus-20240229")
    claude2 = create_vision_api("anthropic", specific_model="claude-3-5-sonnet-20241022")

    open1 = create_vision_api("openai", specific_model="gpt-4o")
    open2 = create_vision_api("openai", specific_model="gpt-4o-mini")

    gemini1flash = create_vision_api("google", "gemini-1.5-flash")
    gemini1 = create_vision_api("google","gemini-1.5-flash-8b")
    gemini15pro = create_vision_api("google","gemini-1.5-pro")
    
    gemini2 = create_vision_api("google","gemini-2.0-flash-exp")
    gemini3 = create_vision_api("google","gemini-2.0-flash-thinking-exp-1219")
    geminiExp = create_vision_api("google", "gemini-exp-1206")

    grok1 = create_vision_api("xai",specific_model="grok-vision-beta")
    grok2 = create_vision_api("xai",specific_model="grok-2-vision-1212")
    
    # vision_apis = [grok1, grok2, claude1, claude2]
    players_list = [claude1, groq1, groq2, claude2, open1, open2]
    # ai_players = [grok1, grok2, grok1]

    players_list = [claude1, groq1, groq2, claude2, open1, open2]

    random.shuffle(players_list)

    players_list = [groq1, groq2, claude1, claude2, open1, open2, 
                    gemini1, gemini2, gemini3, gemini15pro, geminiExp, gemini1flash]
    random.sample(players_list, 6)

    # ai_players = [gemini1, gemini2 , grok1, claude1, open2, gemini3, gemini2, gemini1]

    # gemini is playing gemini !
    # ai_players = [gemini1, gemini2 , gemini3, gemini1, gemini2 , gemini3]

    # everybody!
    ai_players = [ 
        # groq1, 
        groq2, 
        # claude1, 
        claude2, 
        open1, 
        # open2,         
        gemini15pro,
        gemini1flash,
        geminiExp,
        grok1
        ] 
    # players_list = [ groq1,
                #    gemini2, gemini3, 
                #    gemini1, groq2 ] 
    
    # # strongest from each provider
    # players_list = [ groq2,
    #                gemini2,
    #                claude2, 
    #                open1,
    #             #    grok2
                #    ] 


    play_game(
        # image_directory="data/original",
        image_directory="data/1_full",
        players = ai_players,
        max_number_of_rounds = 10,
        score_to_win = 30
    )
 