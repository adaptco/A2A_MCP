import os
import requests
from dotenv import load_dotenv

# Load your local .env file
load_dotenv()

def test_codestral_fim():
    api_key = os.getenv("LLM_API_KEY")
    # Use the FIM endpoint we patched into your .env
    endpoint = "https://codestral.mistral.ai/v1/fim/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # FIM prompt structure: Prefix and Suffix
    data = {
        "model": "codestral-latest",
        "prompt": "def calculate_area(radius):\n    import math\n   ",
        "suffix": "\n    return area",
        "max_tokens": 64,
        "temperature": 0
    }

    print(f"🚀 Testing Codestral FIM at: {endpoint}...")
    
    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Extract the generated code between the prefix and suffix
        generated_code = result['choices'][0]['message']['content']
        print("\n✅ FIM Handshake Successful!")
        print(f"Synthesized Code Loop: \n{generated_code}")
        
    except Exception as e:
        print(f"\n❌ FIM Test Failed: {e}")

if __name__ == "__main__":
    test_codestral_fim()
