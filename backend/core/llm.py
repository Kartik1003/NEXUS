"""OpenRouter LLM client with multi-LLM parallel execution and cost tracking."""

import httpx
import json
import asyncio
import logging
import re
import os
import time
import math
from typing import Optional, Any, Callable, Awaitable

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    MODEL_REGISTRY,
    MAX_TOKENS_PER_CALL,
)
from core.models import CostRecord, AgentType

logger = logging.getLogger(__name__)

# User defined pricing map
MODEL_PRICING = {
    "google/gemini-2.0-flash-lite-preview-02-05:free": 0.0,
    "google/gemini-2.0-flash-exp:free": 0.0,
    "google/gemma-3-4b-it:free": 0.0,
    "nvidia/nemotron-nano-9b-v2:free": 0.0,
    "meta-llama/llama-3.2-3b-instruct:free": 0.0,
    "google/gemma-3-27b-it:free": 0.0,
    "meta-llama/llama-3.3-70b-instruct:free": 0.0,
    "qwen/qwen3-coder:free": 0.0,
    "nousresearch/hermes-3-llama-3.1-405b:free": 0.0,
    "nvidia/nemotron-3-super-120b-a12b:free": 0.0,
    "qwen/qwen3-next-80b-a3b-instruct:free": 0.0,
    "openrouter/free": 0.0,
}

STATS_FILE = "model_memory.json"

class LLMClient:
    def __init__(self):
        self.cost_records: list[CostRecord] = []
        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.invalid_models: set[str] = set()
        self.cache: dict[str, dict] = {}  # prompt hash -> response
        self.model_stats: dict[str, dict] = self._load_stats()
        self.total_system_runs: int = sum(m.get("total_runs", 0) for m in self.model_stats.values()) or 1
        # Rate limiter: max 3 concurrent requests + delay between calls
        self._semaphore = asyncio.Semaphore(2)  # Decreased concurrency to avoid bursts
        self._last_call_time: float = 0.0
        self._min_delay: float = 0.5  # Reduced delay for better throughput
        self._cooldowns: dict[str, float] = {}  # model -> resume_time_ts
        self.pipeline_stats: dict = self._load_pipeline_stats()

        self.timeout = httpx.Timeout(
            connect=10.0,    # 10s to connect
            read=120.0,      # 120s read — free models on OpenRouter can be slow
            write=10.0,
            pool=5.0
        )

    def _load_stats(self) -> dict:
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading stats: {e}")
        return {}

    def _save_stats(self):
        try:
            with open(STATS_FILE, "w") as f:
                json.dump(self.model_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")

    def update_model_memory(self, model: str, score: float, cost: float, success: bool, reward: float):
        if model not in self.model_stats:
            self.model_stats[model] = {
                "total_runs": 0,
                "successes": 0,
                "failures": 0,
                "avg_score": 0.0,
                "avg_cost": 0.0,
                "reward": 0.0
            }
            
        stats = self.model_stats[model]
        stats["total_runs"] += 1
        self.total_system_runs += 1
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            
        n = stats["total_runs"]
        stats["avg_score"] = stats["avg_score"] + (score - stats["avg_score"]) / n
        stats["avg_cost"] = stats["avg_cost"] + (cost - stats["avg_cost"]) / n
        stats["reward"] = stats["reward"] + (reward - stats["reward"]) / n
        
        self._save_stats()

    def rank_models(self) -> list[str]:
        """Rank models dynamically via UCB Bandit logic with 80/20 Exploitation/Exploration."""
        ranked = []
        import random
        
        for model in MODEL_REGISTRY:
            name = model["name"]
            # Skip if manually restricted or in active cooldown
            if name in self.invalid_models or time.time() < self._cooldowns.get(name, 0):
                continue
            
            stats = self.model_stats.get(name)
            if not stats:
                ranked.append((name, 1.0)) # Initial high UCB for untested
                continue
                
            runs = stats.get("total_runs", 0)
            avg_reward = stats.get("reward", 0.5)
            
            if runs == 0:
                ucb_score = 10.0
            else:
                # UCB formula: avg_reward + sqrt(log(total_system_runs) / (model_runs + 1))
                ucb_score = avg_reward + math.sqrt(math.log(self.total_system_runs + 1) / (runs + 1))
                
            ranked.append((name, ucb_score))
            
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in ranked]

    def _load_pipeline_stats(self) -> dict:
        PIPELINE_STATS_FILE = "pipeline_memory.json"
        if os.path.exists(PIPELINE_STATS_FILE):
            try:
                with open(PIPELINE_STATS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading pipeline stats: {e}")
        return {}

    def _save_pipeline_stats(self):
        PIPELINE_STATS_FILE = "pipeline_memory.json"
        try:
            with open(PIPELINE_STATS_FILE, "w") as f:
                json.dump(self.pipeline_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pipeline stats: {e}")

    def update_pipeline_memory(self, task_type: str, sequence: list[str], score: float, cost: float, success: bool):
        if task_type not in self.pipeline_stats:
            self.pipeline_stats[task_type] = {"pipelines": []}
            
        pipelines = self.pipeline_stats[task_type]["pipelines"]
        target = next((p for p in pipelines if p["sequence"] == sequence), None)
                
        if not target:
            target = {
                "sequence": sequence,
                "avg_score": 0.0,
                "avg_cost": 0.0,
                "success_rate": 0.0,
                "runs": 0
            }
            pipelines.append(target)
            
        target["runs"] += 1
        n = target["runs"]
        
        target["avg_score"] = target["avg_score"] + (score - target["avg_score"]) / n
        target["avg_cost"] = target["avg_cost"] + (cost - target["avg_cost"]) / n
        success_val = 1.0 if success else 0.0
        target["success_rate"] = target["success_rate"] + (success_val - target["success_rate"]) / n
        
        self._save_pipeline_stats()

    def select_best_pipeline(self, task_type: str, default_pipeline: list[str]) -> tuple[list[str], bool]:
        import random
        if task_type in self.pipeline_stats and self.pipeline_stats[task_type]["pipelines"]:
            pipelines = self.pipeline_stats[task_type]["pipelines"]
            total_runs = sum(p["runs"] for p in pipelines)
            
            scored = []
            for p in pipelines:
                avg_score = p["avg_score"]
                runs = p["runs"]
                alpha = 0.5 # penalty weight for cost scaling
                # If runs < 1, boost arbitrarily to test it
                if runs == 0:
                    ucb = 10.0 
                else:
                    base_score = avg_score - (alpha * p["avg_cost"])
                    ucb = base_score + math.sqrt(math.log(total_runs + 1) / (runs + 1))
                scored.append((p["sequence"], ucb))
                
            scored.sort(key=lambda x: x[1], reverse=True)
            best_seq = scored[0][0]
            
            if random.random() < 0.2:
                return default_pipeline, False
            else:
                return best_seq, True
        return default_pipeline, False

    def _get_cache_key(self, messages: list[dict], model: str) -> str:
        s = json.dumps(messages, sort_keys=True) + model
        return s

    def get_models_by_quality(self, quality: str) -> list[str]:
        return [m["name"] for m in MODEL_REGISTRY if m["quality"] == quality and m["name"] not in self.invalid_models]

    def get_models_by_cost(self, cost: str) -> list[str]:
        return [m["name"] for m in MODEL_REGISTRY if m["cost"] == cost and m["name"] not in self.invalid_models]

    def get_best_cheap_model(self) -> str:
        ranked = self.rank_models()
        cheap_models = self.get_models_by_cost("low")
        for r in ranked:
            if r in cheap_models:
                return r
        if cheap_models:
            return cheap_models[0]
        return MODEL_REGISTRY[0]["name"]

    def _estimate_tokens(self, text: str) -> int:
        """Fallback token estimator if API response is missing usage data."""
        return int(len(str(text).split()) * 1.3)

    async def call(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        agent: AgentType = AgentType.ROUTER,
        task_id: str = "",
        json_mode: bool = True,
        max_retries: int = 2,  # 2 retries per model — fail fast and move to next in pool
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        is_fallback: bool = False,
    ) -> dict:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found")

        # Determine which models to try
        if model:
            model_pool = [model]
        else:
            model_pool = self.rank_models()

        last_error = "No models available in pool"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "AgentForge-System",
        }

        sys_msg = "Please output your response strictly in JSON format. Provide your detailed response in an 'answer' key. If applicable, provide your confidence score in a 'confidence' key. Only output JSON."
        msg_copy = messages
        if json_mode:
            if not any(m["role"] == "system" for m in messages):
                msg_copy = [{"role": "system", "content": sys_msg}] + messages
            else:
                msg_copy = []
                for m in messages:
                    if m["role"] == "system":
                        msg_copy.append({"role": "system", "content": m["content"] + "\n" + sys_msg})
                    else:
                        msg_copy.append(m)

        logger.info(f"[LLM POOL] Agent={agent.value if agent else 'None'} Pool_Size={len(model_pool)}")

        for current_model in model_pool:
            if not current_model: continue
            
            cache_key = self._get_cache_key(messages, current_model)
            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] Model={current_model}")
                res = self.cache[cache_key]
                if stream_callback and res.get("answer"):
                    await stream_callback(res["answer"])
                return res

            payload = {
                "model": current_model,
                "messages": msg_copy,
                "max_tokens": MAX_TOKENS_PER_CALL,
                "temperature": 0.3,
                "stream": True
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            # Retry loop for CURRENT model
            for attempt in range(max_retries):
                try:
                    content = ""
                    input_tokens = 0
                    output_tokens = 0
                    start_time = time.time()
                    
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        async with self._semaphore:
                            elapsed = time.time() - self._last_call_time
                            if elapsed < self._min_delay:
                                await asyncio.sleep(self._min_delay - elapsed)
                            self._last_call_time = time.time()
                        
                            async with client.stream("POST", OPENROUTER_BASE_URL, headers=headers, json=payload) as resp:
                                if resp.status_code == 429:
                                    wait = 5 * (attempt + 1)
                                    logger.warning(f"Rate limited on {current_model}, waiting {wait}s...")
                                    await asyncio.sleep(wait)
                                    continue
                                
                                if resp.status_code in (500, 502, 503):
                                    logger.warning(f"Server error {resp.status_code} on {current_model}, retrying...")
                                    await asyncio.sleep(3)
                                    continue
                                    
                                if resp.status_code != 200:
                                    error_text = await resp.aread()
                                    logger.error(f"HTTP {resp.status_code} on {current_model}: {error_text}")
                                    if resp.status_code == 404:
                                        self.invalid_models.add(current_model)
                                    break # Try next model

                                async for line in resp.aiter_lines():
                                    if line.startswith("data: "):
                                        data_str = line[len("data: "):].strip()
                                        if data_str == "[DONE]": break
                                        if not data_str: continue
                                        try:
                                            chunk = json.loads(data_str)
                                            if "usage" in chunk and chunk["usage"]:
                                                usage = chunk["usage"]
                                                if usage.get("prompt_tokens"): input_tokens = usage.get("prompt_tokens", 0)
                                                if usage.get("completion_tokens"): output_tokens = usage.get("completion_tokens", 0)
                                            if "choices" in chunk and chunk["choices"]:
                                                delta = chunk["choices"][0].get("delta", {})
                                                token = delta.get("content", "")
                                                if token:
                                                    content += token
                                                    if stream_callback: await stream_callback(token)
                                        except: pass

                    latency = time.time() - start_time
                    if input_tokens == 0: input_tokens = sum(self._estimate_tokens(m["content"]) for m in msg_copy)
                    if output_tokens == 0: output_tokens = self._estimate_tokens(content)
                    total_req_tokens = input_tokens + output_tokens
                    rate = MODEL_PRICING.get(current_model, 0.000001)
                    cost = total_req_tokens * rate
                    self.total_cost += cost
                    self.total_tokens += total_req_tokens

                    if agent:
                        self.cost_records.append(CostRecord(task_id=task_id, agent=agent, model=current_model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=round(cost, 6)))

                    answer = content
                    confidence = 0.7
                    if json_mode:
                        try:
                            cleaned = content.strip()
                            if cleaned.startswith("```"): cleaned = "\n".join(cleaned.split("\n")[1:-1])
                            parsed = json.loads(cleaned)
                            answer = parsed.get("answer", parsed) if isinstance(parsed, dict) else parsed
                            confidence = float(parsed.get("confidence", 0.7)) if isinstance(parsed, dict) else 0.7
                        except: answer = content

                    res = {
                        "model": current_model, "answer": answer, "confidence": confidence,
                        "tokens_used": total_req_tokens, "cost_usd": round(cost, 6),
                        "latency": latency, "status": "success", "final_status": "success"
                    }
                    self.update_model_memory(current_model, score=confidence, cost=cost, success=True, reward=confidence)
                    self.cache[cache_key] = res
                    return res

                except httpx.TimeoutException:
                    logger.warning(f"Timeout on attempt {attempt+1} for model {current_model}")
                    if attempt == max_retries - 1: break
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[ERROR] {current_model}: {e}")
                    last_error = str(e)
                    break 

            self.update_model_memory(current_model, score=0, cost=0, success=False, reward=0.0)
            logger.warning(f"Model {current_model} failed, attempting next model in pool...")

        raise ValueError(f"All models in pool failed. Last error: {last_error}")

    async def call_with_validation(
        self,
        messages: list[dict],
        primary_model: str,
        validator_model: str,
        agent: AgentType = AgentType.ROUTER,
        task_id: str = "",
        json_mode: bool = True,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> dict:
        """Execute with primary model, then validate with a second model."""
        primary_result = await self.call(
            messages=messages,
            model=primary_model,
            agent=agent,
            task_id=task_id,
            json_mode=json_mode,
            stream_callback=stream_callback,
        )

        if not primary_result or primary_result.get("status") != "success":
            return primary_result

        primary_answer = primary_result.get("answer", "")

        validation_prompt = f"""You are a quality validator. Review this response and provide validation.

ORIGINAL TASK:
{messages[-1].get('content', '') if messages else ''}

RESPONSE TO VALIDATE:
{json.dumps(primary_answer) if isinstance(primary_answer, dict) else str(primary_answer)}

Evaluate for: correctness, completeness, accuracy, and quality.
Output JSON: {{"is_valid": true/false, "quality_score": 0.0-1.0, "issues": ["list of issues if any"], "improved_answer": "only if is_valid is false"}}"""

        validator_result = await self.call(
            messages=[{"role": "user", "content": validation_prompt}],
            model=validator_model,
            agent=AgentType.EVALUATOR,
            task_id=task_id,
            json_mode=True,
        )

        validation_data = {}
        if validator_result and isinstance(validator_result, dict) and validator_result.get("status") == "success":
            val_answer = validator_result.get("answer", {})
            if isinstance(val_answer, str):
                try: val_answer = json.loads(val_answer)
                except: val_answer = {}
            
            if isinstance(val_answer, dict):
                validation_data = val_answer
                if not val_answer.get("is_valid", True) and val_answer.get("improved_answer"):
                    primary_result["answer"] = val_answer["improved_answer"]
                    primary_result["confidence"] = max(primary_result.get("confidence", 0.7) - 0.1, 0.3)
                else:
                    q_score = float(val_answer.get("quality_score", 0.7))
                    primary_result["confidence"] = min((primary_result.get("confidence", 0.7) + q_score) / 2, 1.0)

            primary_result["tokens_used"] += validator_result.get("tokens_used", 0)
            primary_result["cost_usd"] += validator_result.get("cost_usd", 0.0)

        primary_result["validation"] = validation_data
        primary_result["validator_model"] = validator_model
        primary_result["execution_mode"] = "validation"

        return primary_result

    async def multi_call(
        self,
        messages: list[dict],
        tier: str = "cheap",
        complexity: str = "simple",
        agent: AgentType = AgentType.ROUTER,
        task_id: str = "",
        task_type: str = "general",
        json_mode: bool = True,
    ) -> list[dict]:
        """Call multiple models in parallel."""
        models = self.select_models(tier, complexity, task_type)
        tasks = [self.call(messages, model=m, agent=agent, task_id=task_id, json_mode=json_mode) for m in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        clean_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"[MULTI_CALL] Model {models[i]} raised: {r}")
                clean_results.append({"model": models[i], "error": str(r), "status": "error"})
            else:
                clean_results.append(r)
        return clean_results

    def select_models(self, tier: str, complexity: str, task_type: str = "general") -> list[str]:
        count = 1 if complexity == "simple" else 2
        pool = []
        if tier == "cheap": pool = self.get_models_by_cost("low")
        elif tier in ("mid", "standard"): pool = self.get_models_by_quality("high")
        elif tier in ("high", "expensive"): pool = self.get_models_by_cost("high")
        else: pool = [m["name"] for m in MODEL_REGISTRY]
            
        ranked = self.rank_models()
        available = [r for r in ranked if r in pool]
        if len(available) < count:
            for r in ranked:
                if r not in available and len(available) < count:
                    available.append(r)
        return available[:count]

    def get_cost_summary(self) -> dict:
        by_agent = {}
        by_model = {}
        for r in self.cost_records:
            by_agent[r.agent.value] = by_agent.get(r.agent.value, 0) + r.cost_usd
            by_model[r.model] = by_model.get(r.model, 0) + r.cost_usd
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "by_agent": by_agent,
            "by_model": by_model,
        }

    def reset(self):
        self.cost_records.clear()
        self.total_cost = 0.0
        self.total_tokens = 0

llm_client = LLMClient()
