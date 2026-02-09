import requests
import os

class LLMService:
    def __init__(self):
        # We grab the configuration from your .env
        self.api_key = os.getenv("FvVdKWlnGMXKOgmGUZaY9RWM4K20cI2r")
        self.endpoint = os.getenv("https://codestral.mistral.ai/v1/chat/completions")

    def call_llm(self, prompt: str, system_prompt: str = "You are a helpful coding assistant."):
        # Define headers and payload INSIDE the function so they are ready when called
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "codestral-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }

        # Now they are defined and ready to use
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]