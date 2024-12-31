import unittest
from unittest.mock import Mock, patch
import base64
# from vision_models.vision_API import VisionAPI
from vision_models.grok_vision import GrokVision
# from ..vision_API import VisionAPI
# from ..grok_vision import GrokVision

class TestGrokVision(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_key"
        self.api_endpoint = "test_endpoint"
        self.vision = GrokVision(self.api_key, self.api_endpoint)
        self.test_image = "test image data"
        self.test_base64 = base64.b64encode(self.test_image.encode()).decode()
        self.test_prompt = "test prompt"

    @patch.object(GrokVision, 'make_api_request')
    def test_successful_analysis(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test content"}}]
        }
        mock_request.return_value = mock_response

        expected_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self.test_base64}"}},
                    {"type": "text", "text": self.test_prompt}
                ]
            }
        ]

        result = self.vision.analyze_image(self.test_base64, self.test_prompt)

        mock_request.assert_called_once_with("llama-3.2-90b-vision-preview", expected_messages)
        self.assertEqual(result, "test content")

    @patch.object(GrokVision, 'make_api_request')
    def test_failed_analysis(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response

        with self.assertRaises(Exception):
            self.vision.analyze_image(self.test_base64, self.test_prompt)

if __name__ == '__main__':
    unittest.main()