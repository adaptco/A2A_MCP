import requests
import json

def test_orchestrator():
    url = "http://localhost:8000/orchestrate"
    params = {"user_query": "Create a Python script that calculates Fibonacci numbers"}
    
    print(f"🚀 Sending request to Orchestrator...")
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print("\n✅ A2A Pipeline Success!")
        print(f"--- Pipeline Trace ---")
        print(f"Research ID: {data['pipeline_results']['research']}")
        print(f"Coding ID:   {data['pipeline_results']['coding']}")
        print(f"Testing ID:  {data['pipeline_results']['testing']}")
        
        print("\n--- Final Test Summary ---")
        print(data['test_summary'])
        
        print("\n--- Generated Code Snippet ---")
        print(data['final_code'][:200] + "...")
        
    except Exception as e:
        print(f"❌ Error: Could not connect to the orchestrator. Is Docker running?")
        print(e)

if __name__ == "__main__":
    test_orchestrator()
