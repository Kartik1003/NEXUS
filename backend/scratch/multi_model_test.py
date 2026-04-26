import httpx
import json

def test_multi_model():
    url = "http://127.0.0.1:8000/api/test"
    # A slightly more complex task to trigger 'mid' tier and multi-model
    payload = {"task": "Write an optimized Python function to find the longest palindromic substring in a string. Include comments."}
    
    print(f"Task: {payload['task']}")
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                print("\n--- RESULTS ---")
                print(f"Model Selected: {result.get('model_used', 'N/A')}")
                print(f"Total Cost: ${result.get('cost', {}).get('total_cost_usd', 0)}")
                
                print("\n--- EXECUTION LOG ---")
                for log in result.get("execution_log", []):
                    agent = log.get("agent", "unknown")
                    step = log.get("step", "N/A")
                    res = log.get("result", "")
                    print(f"[{agent.upper()}] {step}: {res[:100]}...")

                print("\n--- FINAL CODE PREVIEW ---")
                print(result.get("final_code", "")[:300] + "...")
            else:
                print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_multi_model()
