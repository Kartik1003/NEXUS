"""Quick script to fetch all currently-active free models from OpenRouter."""
import urllib.request
import json

req = urllib.request.Request("https://openrouter.ai/api/v1/models")
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode("utf-8"))

free_models = []
for m in data["data"]:
    pricing = m.get("pricing", {})
    prompt_cost = pricing.get("prompt", "1")
    completion_cost = pricing.get("completion", "1")
    if prompt_cost == "0" and completion_cost == "0":
        free_models.append(m["id"])

print(f"Found {len(free_models)} free models:\n")
for model_id in sorted(free_models):
    print(f"  {model_id}")
