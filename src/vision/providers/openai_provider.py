"""OpenAI direct provider (fallback)."""

import asyncio
import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

from vision.base import VisionAPI

load_dotenv()


class OpenAIVision(VisionAPI):
    def __init__(self, model: str):
        # Strip "openai/" prefix — the native OpenAI SDK expects bare names like "gpt-4o"
        self.model = model.removeprefix("openai/")
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        if image_path.startswith(("http://", "https://")):
            image_url_str = image_path
        else:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            image_url_str = f"data:image/jpeg;base64,{image_b64}"

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
                            {"type": "image_url", "image_url": {"url": image_url_str}},
                        ],
                    }
                ],
            ),
        )
        return response.choices[0].message.content

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "OpenAIVision"}
