import requests
import os

class LLMService:
    def __init__(self):
        # We just grab the keys here
        self.api_key = os.getenv("LLM_API_KEY")
        self.endpoint = os.getenv("LLM_ENDPOINT")

    def call_llm(self, prompt: str, system_prompt: str = "You are a helpful coding assistant."):
        # Move the headers and payload INSIDE this function
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

        print(f"🚀 Sending request to: {self.endpoint}")
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
