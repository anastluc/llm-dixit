import requests
from vision_models.vision_API import VisionAPI
import os
from dotenv import load_dotenv

class GrokVision(VisionAPI):
    def __init__(self, api_key: str, api_endpoint: str):        
        load_dotenv()
        GROQ_API_URL = os.getenv("GROQ_API_URL")
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.api_key = api_key
        self.api_endpoint = api_endpoint

    def analyze_image(self, image_base64: str, prompt: str) -> str:

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": f"{prompt}"}            
                ]
            }
        ]

        # Make API request
        response = self.make_api_request("llama-3.2-90b-vision-preview", messages)

        if response.status_code != 200:
            raise Exception(f"API request failed with status code {response.status_code}")
        
        return response.json()["choices"][0]["message"]["content"]
        # if response.status_code == 200:
        #     content = response.json()["choices"][0]["message"]["content"]
        #     return content
        

    def make_api_request(self, model: str, messages: list) -> requests.Response:
        """Make request to Groq API."""
        return requests.post(
            self.api_endpoint,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1000
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )