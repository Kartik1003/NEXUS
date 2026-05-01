from dotenv import load_dotenv
import os

load_dotenv(override=True)

# ─── CORS ────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")
if ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS.split(",")]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

# ─── OpenRouter ───────────────────────────────────────────────────────────────
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL  = "https://openrouter.ai/api/v1/chat/completions"

# ─── Data directory (single source of truth for ALL runtime files) ───────────
# Every JSON stats file lives here instead of the project root.
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH             = os.path.join(DATA_DIR, "memory.db")
MODEL_STATS_FILE    = os.path.join(DATA_DIR, "model_memory.json")
PIPELINE_STATS_FILE = os.path.join(DATA_DIR, "pipeline_memory.json")
DEPT_MEMORY_FILE    = os.path.join(DATA_DIR, "department_memory.json")

# ─── LLM Settings ─────────────────────────────────────────────────────────────
MAX_TOKENS_PER_CALL = 8192

# ─── Model Registry ───────────────────────────────────────────────────────────
MODEL_REGISTRY = [
    {"name": "google/gemini-2.0-flash-lite-preview-02-05:free", "cost": "low",  "quality": "medium"},
    {"name": "google/gemini-2.0-flash-exp:free",                "cost": "mid",  "quality": "high"},
    {"name": "google/gemma-3-4b-it",                            "cost": "low",  "quality": "medium"},
    {"name": "nvidia/nemotron-nano-9b-v2",                      "cost": "low",  "quality": "medium"},
    {"name": "meta-llama/llama-3.2-3b-instruct",                "cost": "low",  "quality": "medium"},
    {"name": "google/gemma-3-27b-it",                           "cost": "mid",  "quality": "high"},
    {"name": "meta-llama/llama-3.3-70b-instruct",               "cost": "mid",  "quality": "high"},
    {"name": "qwen/qwen3-coder",                                "cost": "mid",  "quality": "high"},
    {"name": "nousresearch/hermes-3-llama-3.1-405b",            "cost": "high", "quality": "very-high"},
    {"name": "nvidia/nemotron-3-super-120b-a12b",               "cost": "high", "quality": "very-high"},
    {"name": "qwen/qwen3-next-80b-a3b-instruct",                "cost": "high", "quality": "very-high"},
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

# Only Employee agents use LLM — everything else is rule-based
AGENT_MODEL_MAP = {
    "information_technology": "mid",
    "operations":             "cheap",
    "finance":                "cheap",
    "sales_marketing":        "cheap",
    "human_resources":        "cheap",
    "customer_service":       "cheap",
    "research":               "cheap",
}

MODEL_COSTS = {m["name"]: {"input": 0.0, "output": 0.0} for m in MODEL_REGISTRY}
