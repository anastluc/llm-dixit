from __future__ import annotations
from abc import ABC, abstractmethod


class VisionAPI(ABC):
    model: str

    @abstractmethod
    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        pass
