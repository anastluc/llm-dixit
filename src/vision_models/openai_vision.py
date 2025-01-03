from vision_models.vision_API import VisionAPI
from openai import OpenAI
from dotenv import load_dotenv
import os

class OpenAIVision(VisionAPI):
    def __init__(self, model: str):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_image(self, image_base64: str, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": f"{prompt}"
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"\"data:image/jpeg;base64,{image_base64}\""
                    }
                    }
                ]
                }
            ],
            response_format={
                "type": "text"
            },
            temperature=1,
            max_completion_tokens=50,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
        return response.choices[0].message.content
