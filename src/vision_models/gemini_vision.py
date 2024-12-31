import base64
from vision_API import VisionAPI
import os
import google.generativeai as genai


class GeminiVision(VisionAPI):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.model = genai.GenerativeModel('gemini-pro-vision')

    def analyze_image(self, image_base64: str, prompt: str) -> str:
        # image_data = base64.b64decode(image_base64)
        # response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])
        # return response.text

        # Create the model
        generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
        )
        files = [
            self.upload_to_gemini("", mime_type="image/png"),
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
    
    def upload_to_gemini(path, mime_type=None):
        """Uploads the given file to Gemini.

        See https://ai.google.dev/gemini-api/docs/prompting_with_media
        """
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file.uri










# TODO Make these files available on the local file system
# You may need to update the file paths


