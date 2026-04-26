import httpx
import json

def check_health():
    try:
        resp = httpx.get("http://127.0.0.1:8001/api/health")
        print(f"Status: {resp.status_code}")
        print(f"Body: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_health()
