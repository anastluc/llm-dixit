import anthropic
from vision_models.vision_API import VisionAPI

class ClaudeVision(VisionAPI):
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Client(api_key=api_key)
        self.model = model

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
