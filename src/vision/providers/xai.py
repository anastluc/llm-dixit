"""xAI Grok vision direct provider (fallback)."""

import asyncio
import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

from vision.base import VisionAPI

load_dotenv()


class XAIVision(VisionAPI):
    def __init__(self, model: str):
        self.model = model
        self._client = OpenAI(api_key=os.getenv("XAI_GROK_API_KEY"), base_url="https://api.x.ai/v1")

    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.chat.completions.create(
                model=self.model,
                max_completion_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ],
                    }
                ],
            ),
        )
        return response.choices[0].message.content

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "XAIVision"}
