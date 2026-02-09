import requests
import time

def test_persistent_orchestrator():
    url = "http://localhost:8000/orchestrate"
    # Example query to trigger the full Research -> Code -> Test chain
    params = {"user_query": "Create a robust Python function for calculating compound interest"}
    
    print(f"🚀 Triggering Persistent A2A Pipeline...")
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        root_id = data.get("root_id")
        
        print(f"\n✅ Success! Workflow initiated.")
        print(f"Root Artifact ID (Stored in DB): {root_id}")
        print(f"\nNext Step: Run 'python inspect_db.py' to see the full trace.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Tip: Ensure your Docker containers are running with 'docker-compose up'")

if __name__ == "__main__":
    test_persistent_orchestrator()
