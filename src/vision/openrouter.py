from __future__ import annotations
"""
OpenRouter vision client — primary provider for all model calls.

Sends base64-encoded images via the OpenAI-compatible chat completions endpoint.
Handles retries with exponential backoff on rate-limit (429) and server (5xx) errors.
"""

import asyncio
import base64
import logging
import os

import httpx
from dotenv import load_dotenv

from vision.base import VisionAPI

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://github.com/LLM_dixit")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "LLM Dixit Arena")

# Models available on OpenRouter that support vision (text+image input → text output).
# See https://openrouter.ai/models?modality=image  — updated 2025-04.
# This set is used as a fast-path check before routing to OpenRouter.
# New models are accepted automatically; only truly unsupported IDs are rejected.
OPENROUTER_VISION_MODELS: set[str] = {
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4o-2024-11-20",
    "openai/gpt-4o-2024-08-06",
    "openai/gpt-4-turbo",
    # Anthropic
    "anthropic/claude-opus-4.6",
    "anthropic/claude-opus-4.6-fast",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "anthropic/claude-opus-4.5",
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.5-haiku",
    # Google
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-2.0-flash-001",
    "google/gemini-3.1-flash-lite-preview",
    "google/gemini-3.1-pro-preview",
    # Meta / Llama
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-scout",
    "meta-llama/llama-3.2-11b-vision-instruct",
    # xAI
    "x-ai/grok-4",
    "x-ai/grok-4-fast",
    "x-ai/grok-4.1-fast",
    # Mistral
    "mistralai/pixtral-large-2411",
    "mistralai/pixtral-12b",
    # Qwen
    "qwen/qwen-vl-plus",
    "qwen/qwen3.5-122b-a10b",
}


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_media_type(image_path: str) -> str:
    ext = image_path.lower().rsplit(".", 1)[-1]
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")


class OpenRouterVision(VisionAPI):
    """Async vision client backed by OpenRouter."""

    def __init__(self, model: str):
        self.model = model
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            raise EnvironmentError("OPENROUTER_API_KEY not set in environment")

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 60,
        temperature: float = 1.0,
    ) -> str:
        if image_path.startswith(("http://", "https://")):
            image_url_str = image_path
        else:
            image_b64 = _encode_image(image_path)
            media_type = _image_media_type(image_path)
            image_url_str = f"data:{media_type};base64,{image_b64}"

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url_str},
                        },
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": OPENROUTER_SITE_URL,
            "X-Title": OPENROUTER_APP_NAME,
            "Content-Type": "application/json",
        }

        return await _post_with_retry(OPENROUTER_API_URL, payload, headers)

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "OpenRouterVision"}


async def _post_with_retry(
    url: str,
    payload: dict,
    headers: dict,
    retries: int = 3,
) -> str:
    """POST with exponential backoff on 429 / 5xx errors."""
    delay = 1.0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(retries):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if "error" in data:
                        logger.warning(
                            "OpenRouter 200 with error for model %s: %s",
                            payload.get("model"), str(data["error"])[:200],
                        )
                        return ""
                    content = data["choices"][0]["message"]["content"]
                    return content or ""
                if resp.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        "OpenRouter %s on attempt %d/%d, retrying in %.1fs",
                        resp.status_code, attempt + 1, retries, delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                # 4xx client errors — log body for diagnosis, don't retry
                body = resp.text[:500]
                logger.error(
                    "OpenRouter %s for model %s — %s",
                    resp.status_code, payload.get("model"), body,
                )
                return ""
            except httpx.RequestError as exc:
                logger.warning("Network error on attempt %d/%d: %s", attempt + 1, retries, exc)
                await asyncio.sleep(delay)
                delay *= 2
    logger.error("OpenRouter request failed after %d attempts for model %s", retries, payload.get("model"))
    return ""
