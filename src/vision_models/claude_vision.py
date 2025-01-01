import anthropic
from vision_models.vision_API import VisionAPI
from dotenv import load_dotenv
import os

class ClaudeVision(VisionAPI):
    def __init__(self, model: str):
        self.model = model
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Client(api_key=api_key)
        

    def analyze_image(self, image_base64: str, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}}
                ]
            }]
        )
        return response.content[0].text
