"""Groq vision direct provider (fallback)."""

import asyncio
import base64
import os

import httpx
from dotenv import load_dotenv

from vision.base import VisionAPI

load_dotenv()

VALID_GROQ_MODELS = {"llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"}


class GroqVision(VisionAPI):
    def __init__(self, model: str = "llama-3.2-90b-vision-preview"):
        if model not in VALID_GROQ_MODELS:
            raise ValueError(f"Invalid Groq model: {model}. Must be one of {VALID_GROQ_MODELS}")
        self.model = model
        self._api_key = os.getenv("GROQ_API_KEY")
        self._api_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._api_url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "GroqVision"}
