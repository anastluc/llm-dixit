"""Anthropic Claude direct provider (fallback)."""

import asyncio
import base64
import os

import anthropic
from dotenv import load_dotenv

from vision.base import VisionAPI

load_dotenv()


class ClaudeVision(VisionAPI):
    def __init__(self, model: str):
        self.model = model.removeprefix("anthropic/")
        self._client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        if image_path.startswith(("http://", "https://")):
            image_source = {"type": "url", "url": image_path}
        else:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            image_source = {"type": "base64", "media_type": "image/jpeg", "data": image_b64}

        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": image_source},
                        ],
                    }
                ],
            ),
        )
        return message.content[0].text

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "ClaudeVision"}
