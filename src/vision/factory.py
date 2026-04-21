from __future__ import annotations
"""
Vision client factory.

Resolution order:
1. If model name is in OPENROUTER_VISION_MODELS → OpenRouterVision (async httpx, single API key)
2. Otherwise fall back to a direct provider client based on the provider prefix.

Direct fallback model name convention (when NOT using OpenRouter):
  anthropic/<model>  → ClaudeVision
  openai/<model>     → OpenAIVision
  google/<model>     → GeminiVision
  groq/<model>       → GroqVision
  x-ai/<model>       → XAIVision

For legacy bare model names (e.g. "gpt-4o", "claude-3-5-sonnet-20241022"),
pass provider= explicitly or use the full OpenRouter-style name.
"""

from vision.base import VisionAPI
from vision.openrouter import OPENROUTER_VISION_MODELS, OpenRouterVision


def create_vision_client(model: str, provider: str | None = None) -> VisionAPI:
    """
    Create a vision API client for the given model.

    Args:
        model: Model identifier. Prefer OpenRouter-style names like "openai/gpt-4o".
               Bare names like "gpt-4o" are also accepted for direct provider fallback.
        provider: Explicit provider override ("anthropic", "openai", "google", "groq", "xai").
                  Only needed when model is a bare name not in OpenRouter's model set.
    """
    import os

    # Primary rule: any "provider/model" name + OPENROUTER_API_KEY → OpenRouter.
    # This covers every model in the dropdown without needing a hardcoded allowlist.
    if "/" in model and os.getenv("OPENROUTER_API_KEY"):
        return OpenRouterVision(model)

    # Explicit set check (no API key set, or bare model name already in the known list)
    if model in OPENROUTER_VISION_MODELS:
        return OpenRouterVision(model)

    # Infer provider from model name prefix
    inferred_provider = provider or _infer_provider(model)

    if inferred_provider == "anthropic":
        from vision.providers.claude import ClaudeVision
        return ClaudeVision(model)
    elif inferred_provider == "openai":
        from vision.providers.openai_provider import OpenAIVision
        return OpenAIVision(model)
    elif inferred_provider == "google":
        from vision.providers.gemini import GeminiVision
        return GeminiVision(model)
    elif inferred_provider == "groq":
        from vision.providers.groq import GroqVision
        return GroqVision(model)
    elif inferred_provider == "xai":
        from vision.providers.xai import XAIVision
        return XAIVision(model)
    else:
        # Try OpenRouter as last resort
        return OpenRouterVision(model)


def _infer_provider(model: str) -> str | None:
    """Infer provider from model name prefix or well-known bare names."""
    prefix = model.split("/")[0].lower() if "/" in model else ""
    if prefix in ("anthropic", "openai", "google", "groq", "x-ai", "xai", "meta-llama", "mistralai", "qwen"):
        return prefix.replace("x-ai", "xai").replace("meta-llama", "groq")

    # Bare model name heuristics
    lower = model.lower()
    if lower.startswith("claude"):
        return "anthropic"
    if lower.startswith(("gpt-", "o1", "o3")):
        return "openai"
    if lower.startswith("gemini"):
        return "google"
    if lower.startswith("llama"):
        return "groq"
    if lower.startswith("grok"):
        return "xai"
    return None
