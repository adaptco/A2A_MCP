import os
import requests

def call_llm(prompt: str, system_prompt: str = "You are a helpful coding assistant."):
    """
    Centralized utility to call an LLM (Gemini/Claude).
    """
    api_key = os.getenv("LLM_API_KEY")
    # This example uses a generic POST structure; adapt based on your chosen provider
    endpoint = os.getenv("LLM_ENDPOINT", "https://api.provider.com/v1/chat")
    
    payload = {
        "model": "gemini-1.5-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM Call Failed: {str(e)}"
