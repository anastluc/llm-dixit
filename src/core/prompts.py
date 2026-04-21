from __future__ import annotations
"""
Prompt style registry for LLM Dixit Arena.


Each style defines:
  - clue_prompt: shown to the storyteller with the card image
  - vote_prompt: shown to voters; use {clue} as a placeholder
  - max_tokens / temperature: API parameters tuned per style
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptStyle:
    name: str
    description: str
    clue_prompt: str
    vote_prompt: str
    max_tokens: int
    temperature: float


PROMPT_STYLES: dict[str, PromptStyle] = {
    "creative": PromptStyle(
        name="Creative / Poetic",
        description="Abstract, metaphorical clues in the spirit of classic Dixit — neither too obvious nor too obscure.",
        clue_prompt=(
            "Generate a creative, metaphorical clue for this Dixit card that is neither too obvious nor too obscure. "
            "Use 2–15 words. Reply with only the clue, nothing else."
        ),
        vote_prompt=(
            "On a scale of 0–10, how well does this card match the clue '{clue}'? "
            "Reply with a single number only."
        ),
        max_tokens=60,
        temperature=1.0,
    ),
    "deceptive": PromptStyle(
        name="Deceptive / Strategic",
        description="Clues designed to mislead — must genuinely relate to your card but plausibly fit others. Tests theory-of-mind.",
        clue_prompt=(
            "Generate a clue for this Dixit card that will mislead other players into choosing a different card. "
            "The clue MUST genuinely relate to your card, but should plausibly fit other abstract images too. "
            "Use 2–15 words. Reply with only the clue, nothing else."
        ),
        vote_prompt=(
            "On a scale of 0–10, how well does this card match the clue '{clue}'? "
            "Consider that this clue may be deliberately misleading. "
            "Reply with a single number only."
        ),
        max_tokens=60,
        temperature=1.2,
    ),
    "minimalist": PromptStyle(
        name="Minimalist",
        description="1–3 word clues only. Forces extreme abstraction and brevity.",
        clue_prompt=(
            "Give a 1–3 word abstract clue for this Dixit card. "
            "No sentences, no punctuation. Reply with only those words."
        ),
        vote_prompt=(
            "On a scale of 0–10, how well does this card match the word clue '{clue}'? "
            "Reply with a single number only."
        ),
        max_tokens=20,
        temperature=0.9,
    ),
    "narrative": PromptStyle(
        name="Narrative / Story",
        description="Micro-story clues — a single evocative sentence as if beginning a short story.",
        clue_prompt=(
            "Write a single evocative sentence (10–20 words) as if beginning a short story inspired by this Dixit card. "
            "Reply with only the sentence, nothing else."
        ),
        vote_prompt=(
            "On a scale of 0–10, how well does this card match the story opening '{clue}'? "
            "Reply with a single number only."
        ),
        max_tokens=80,
        temperature=1.1,
    ),
}

DEFAULT_STYLE = "creative"


def get_prompt_style(name: str) -> PromptStyle:
    if name not in PROMPT_STYLES:
        raise ValueError(f"Unknown prompt style '{name}'. Available: {list(PROMPT_STYLES.keys())}")
    return PROMPT_STYLES[name]
