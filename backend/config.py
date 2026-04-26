from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Allowed origins for CORS – read from env var ALLOWED_ORIGINS (comma‑separated)
# Fallback to common dev URLs if not set
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS')
if ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS.split(',')]
else:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Verified live models from OpenRouter API
MODEL_REGISTRY = [
    {"name": "google/gemini-2.0-flash-lite-preview-02-05:free", "cost": "low",  "quality": "medium"},
    {"name": "google/gemini-2.0-flash-exp:free",                "cost": "mid",  "quality": "high"},
    {"name": "google/gemma-3-4b-it",                    "cost": "low",  "quality": "medium"},
    {"name": "nvidia/nemotron-nano-9b-v2",               "cost": "low",  "quality": "medium"},
    {"name": "meta-llama/llama-3.2-3b-instruct",         "cost": "low",  "quality": "medium"},
    {"name": "google/gemma-3-27b-it",                    "cost": "mid",  "quality": "high"},
    {"name": "meta-llama/llama-3.3-70b-instruct",        "cost": "mid",  "quality": "high"},
    {"name": "qwen/qwen3-coder",                         "cost": "mid",  "quality": "high"},
    {"name": "nousresearch/hermes-3-llama-3.1-405b",     "cost": "high", "quality": "very-high"},
    {"name": "nvidia/nemotron-3-super-120b-a12b",        "cost": "high", "quality": "very-high"},
    {"name": "qwen/qwen3-next-80b-a3b-instruct",        "cost": "high", "quality": "very-high"},
]

MODEL_POOLS = {
    "cheap": [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemma-3-4b-it",
        "nvidia/nemotron-nano-9b-v2",
        "meta-llama/llama-3.2-3b-instruct",
    ],
    "mid": [
        "google/gemini-2.0-flash-exp:free",
        "google/gemma-3-27b-it",
        "meta-llama/llama-3.3-70b-instruct",
        "qwen/qwen3-coder",
    ],
    "expensive": [
        "nousresearch/hermes-3-llama-3.1-405b",
        "nvidia/nemotron-3-super-120b-a12b",
        "qwen/qwen3-next-80b-a3b-instruct",
    ],
}

# The only agents that use LLM are Employees. 
# Others (CEO, Executive, Dept, Manager) are rule-based.
AGENT_MODEL_MAP = {
    "information_technology": "mid",
    "operations": "cheap",
    "finance": "cheap",
    "sales_marketing": "cheap",
    "human_resources": "cheap",
    "customer_service": "cheap",
    "research": "cheap",
}

# Model cost tracking
MODEL_COSTS = {
    "google/gemma-3-4b-it":                    {"input": 0.0, "output": 0.0},
    "nvidia/nemotron-nano-9b-v2":               {"input": 0.0, "output": 0.0},
    "meta-llama/llama-3.2-3b-instruct":         {"input": 0.0, "output": 0.0},
    "google/gemma-3-27b-it":                    {"input": 0.0, "output": 0.0},
    "meta-llama/llama-3.3-70b-instruct":        {"input": 0.0, "output": 0.0},
    "qwen/qwen3-coder":                         {"input": 0.0, "output": 0.0},
    "nousresearch/hermes-3-llama-3.1-405b":     {"input": 0.0, "output": 0.0},
    "nvidia/nemotron-3-super-120b-a12b":        {"input": 0.0, "output": 0.0},
    "qwen/qwen3-next-80b-a3b-instruct":        {"input": 0.0, "output": 0.0},
}

MAX_TOKENS_PER_CALL = 8192
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "memory.db")
os.makedirs(DATA_DIR, exist_ok=True)