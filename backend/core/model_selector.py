import logging

logger = logging.getLogger(__name__)

MANUAL_OVERRIDES = {}

def set_manual_override(handle: str, model: str | None):
    if model and model != "auto":
        MANUAL_OVERRIDES[handle] = model
        logger.info(f"Manual model override set for {handle}: {model}")
    elif handle in MANUAL_OVERRIDES:
        del MANUAL_OVERRIDES[handle]
        logger.info(f"Manual model override cleared for {handle} (reverted to auto)")

def get_manual_override(handle: str) -> str | None:
    return MANUAL_OVERRIDES.get(handle)

def select_model(task_type: str, complexity: str) -> str:
    """
    Intelligently select the best model based on task type and complexity.
    
    Rules based on capabilities:
    - coding → Qwen Coder / Hermes
    - analysis/research → Qwen Next 80b / Llama 3.3 70b
    - content/writing → Gemma 27b / Llama 30b
    - fast tasks/simple → Nemotron Nano / Llama 3.2 3B
    """
    task_type = (task_type or "").lower()
    complexity = (complexity or "medium").lower()

    logger.info(f"Selecting model for task_type='{task_type}', complexity='{complexity}'")

    if complexity in ("fast", "simple"):
        # Small, fast models
        if "code" in task_type or "debug" in task_type:
            return "meta-llama/llama-3.2-3b-instruct"
        return "nvidia/nemotron-nano-9b-v2"

    if "code" in task_type or "coding" in task_type or "debug" in task_type or "information_technology" in task_type:
        if complexity == "complex":
            return "nousresearch/hermes-3-llama-3.1-405b"
        return "qwen/qwen3-coder"

    if "analysis" in task_type or "research" in task_type or "operations" in task_type or "finance" in task_type:
        if complexity == "complex":
            return "qwen/qwen3-next-80b-a3b-instruct"
        return "meta-llama/llama-3.3-70b-instruct"

    if "content" in task_type or "marketing" in task_type or "writing" in task_type or "sales_marketing" in task_type:
        if complexity == "complex":
            return "nousresearch/hermes-3-llama-3.1-405b"
        return "google/gemma-3-27b-it"

    if "hr" in task_type or "human_resources" in task_type or "customer_service" in task_type:
        if complexity == "complex":
            return "nvidia/nemotron-3-super-120b-a12b"
        return "meta-llama/llama-3.3-70b-instruct"

    # Default fallbacks based on complexity alone
    if complexity == "complex":
        return "nousresearch/hermes-3-llama-3.1-405b"
    elif complexity == "medium":
        return "meta-llama/llama-3.3-70b-instruct"
    
    return "google/gemma-3-4b-it"
