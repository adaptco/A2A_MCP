import requests
import json

def test_pickle_rick():
    url = "http://localhost:8000/agent/pickle-rick"
    payload = {
        "app_name": "Antigravity",
        "artifacts": [
            {
                "artifact_id": "art-1",
                "artifact_type": "requirements",
                "content": "Maintain contextual coherence of the build infrastructure logic.",
                "title": "Context Coherence",
                "tags": ["infra", "coherence"]
            }
        ]
    }

    # This is a unit test for the service/route logic
    from app.services.pickle_rick_agent import PickleRickAgent
    from app.schemas.website_agent import WebsiteTemplateRequest

    agent = PickleRickAgent()
    req = WebsiteTemplateRequest(**payload)
    result = agent.generate_implementation_plan(req)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_pickle_rick()
