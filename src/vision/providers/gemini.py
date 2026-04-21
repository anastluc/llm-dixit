"""Google Gemini direct provider (fallback — uses file upload API)."""

import asyncio
import os

import google.generativeai as genai
from dotenv import load_dotenv

from vision.base import VisionAPI

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))


class GeminiVision(VisionAPI):
    def __init__(self, model: str):
        self.model = model.removeprefix("google/")

    async def analyze_image(self, image_path: str, prompt: str, max_tokens: int = 60, temperature: float = 1.0) -> str:
        loop = asyncio.get_event_loop()

        def _call():
            import tempfile
            import urllib.request

            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": max_tokens,
                "response_mime_type": "text/plain",
            }
            model = genai.GenerativeModel(model_name=self.model, generation_config=generation_config)

            if image_path.startswith(("http://", "https://")):
                suffix = "." + image_path.rsplit(".", 1)[-1].split("?")[0]
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    urllib.request.urlretrieve(image_path, f.name)
                    local_path = f.name
            else:
                local_path = image_path

            file_uri = genai.upload_file(local_path)
            chat = model.start_chat(history=[{"role": "user", "parts": [file_uri]}])
            response = chat.send_message(prompt)
            return response.text

        return await loop.run_in_executor(None, _call)

    def to_dict(self) -> dict:
        return {"model": self.model, "vision_api": "GeminiVision"}
