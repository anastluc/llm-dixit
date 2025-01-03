import base64
from vision_models.vision_API import VisionAPI
import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

class GeminiVision(VisionAPI):
    def __init__(self, model: str):
        load_dotenv()
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model
        self.API_TIME_DELAY = 5
    
        

    def analyze_image(self, image_path: str, prompt: str) -> str:
        print(f"Delaying {self.API_TIME_DELAY} seconds to avoid API's throttling")
        time.sleep(self.API_TIME_DELAY)

        # Create the model
        generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 50,
        "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(
            model_name=self.model,
            generation_config=generation_config,
        )
        files = [
            self.upload_to_gemini(image_path),
            ]
        
        chat_session = model.start_chat(
        history=[
            {
            "role": "user",
            "parts": [
                files[0],
            ],
            },
        ]
        )

        response = chat_session.send_message(prompt)

        print(response.text)
        return response.text
    
    def upload_to_gemini(self, path):
        """Uploads the given file to Gemini.

        See https://ai.google.dev/gemini-api/docs/prompting_with_media
        """
        file = genai.upload_file(path)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file.uri










# TODO Make these files available on the local file system
# You may need to update the file paths


