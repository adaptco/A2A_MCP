import os
from dotenv import load_dotenv

# This tells Python to look for your local .env file
load_dotenv()

class LLMService:
    def __init__(self):
        # These variables pull from your local .env
        self.api_key = os.getenv("LLM_API_KEY")
        self.endpoint = os.getenv("LLM_ENDPOINT")

    def call_llm(self, prompt: str, system_prompt: str = "You are a helpful coding assistant."):
        if not self.api_key or not self.endpoint:
            raise ValueError("API Key or Endpoint missing from your local .env file!")

        import requests

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

        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]