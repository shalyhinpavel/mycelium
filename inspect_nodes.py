import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = "https://mycelium-service-e7auq33oka-ey.a.run.app/v1/search"
API_KEY = os.getenv("MYCELIUM_API_KEY", "sk_live_benchmark_viewer_here")
PERSONALITY_ID = "musique_test_1"

def debug_search():
    headers = {"X-API-Key": API_KEY}
    payload = {
        "query": "Who is the spouse of the Green performer?",
        "personality_id": PERSONALITY_ID,
        "limit": 2,
        "rerank": True
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            node = results[0]
            print("\n=== RAW NODE 0 ===")
            print(f"Content: {node.get('content', '')}")
            print("-" * 20)
            print(f"Metadata: {json.dumps(node.get('metadata', {}), indent=2)}")
        else:
            print("No results found.")
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    debug_search()
