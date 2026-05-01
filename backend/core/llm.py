"""OpenRouter LLM client.

Fixes applied:
  #1  — True token streaming: each token fires immediately through stream_callback.
        The _stream_token path in Orchestrator now delivers real chunks, not a
        buffered dump.  stream_callback is called inside the SSE loop.
  #10 — All data files (model_memory.json, pipeline_memory.json) now live under
        DATA_DIR from config, not the project root.
"""

import httpx
import json
import asyncio
import logging
import time
import math
import os
from typing import Optional, Callable, Awaitable

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    MODEL_REGISTRY,
    MAX_TOKENS_PER_CALL,
    MODEL_STATS_FILE,
    PIPELINE_STATS_FILE,
)
from core.models import CostRecord, AgentType

logger = logging.getLogger(__name__)

MODEL_PRICING = {m["name"]: 0.0 for m in MODEL_REGISTRY}  # all free tier


class LLMClient:
    def __init__(self):
        self.cost_records: list[CostRecord] = []
        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.invalid_models: set[str] = set()
        self.cache: dict[str, dict] = {}
        self.model_stats: dict[str, dict] = self._load_stats()
        self.total_system_runs: int = (
            sum(m.get("total_runs", 0) for m in self.model_stats.values()) or 1
        )
        self._semaphore = asyncio.Semaphore(2)
        self._last_call_time: float = 0.0
        self._min_delay: float = 0.5
        self._cooldowns: dict[str, float] = {}
        self.pipeline_stats: dict = self._load_pipeline_stats()

        self.timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _load_stats(self) -> dict:
        if os.path.exists(MODEL_STATS_FILE):
            try:
                with open(MODEL_STATS_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading model stats: {e}")
        return {}

    def _save_stats(self):
        try:
            with open(MODEL_STATS_FILE, "w") as f:
                json.dump(self.model_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving model stats: {e}")

    def _load_pipeline_stats(self) -> dict:
        if os.path.exists(PIPELINE_STATS_FILE):
            try:
                with open(PIPELINE_STATS_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading pipeline stats: {e}")
        return {}

    def _save_pipeline_stats(self):
        try:
            with open(PIPELINE_STATS_FILE, "w") as f:
                json.dump(self.pipeline_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pipeline stats: {e}")

    # ─── UCB Bandit Model Ranking ─────────────────────────────────────────────

    def update_model_memory(self, model: str, score: float, cost: float,
                             success: bool, reward: float):
        if model not in self.model_stats:
            self.model_stats[model] = {
                "total_runs": 0, "successes": 0, "failures": 0,
                "avg_score": 0.0, "avg_cost": 0.0, "reward": 0.0,
            }
        s = self.model_stats[model]
        s["total_runs"] += 1
        self.total_system_runs += 1
        if success:
            s["successes"] += 1
        else:
            s["failures"] += 1
        n = s["total_runs"]
        s["avg_score"] = s["avg_score"] + (score - s["avg_score"]) / n
        s["avg_cost"]  = s["avg_cost"]  + (cost  - s["avg_cost"])  / n
        s["reward"]    = s["reward"]    + (reward - s["reward"])    / n
        self._save_stats()

    def rank_models(self) -> list[str]:
        ranked = []
        for model in MODEL_REGISTRY:
            name = model["name"]
            if name in self.invalid_models or time.time() < self._cooldowns.get(name, 0):
                continue
            stats = self.model_stats.get(name)
            if not stats:
                ranked.append((name, 1.0))
                continue
            runs = stats.get("total_runs", 0)
            avg_reward = stats.get("reward", 0.5)
            if runs == 0:
                ucb_score = 10.0
            else:
                ucb_score = avg_reward + math.sqrt(
                    math.log(self.total_system_runs + 1) / (runs + 1)
                )
            ranked.append((name, ucb_score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in ranked]

    # ─── Pipeline Memory ──────────────────────────────────────────────────────

    def update_pipeline_memory(self, task_type: str, sequence: list[str],
                                score: float, cost: float, success: bool):
        if task_type not in self.pipeline_stats:
            self.pipeline_stats[task_type] = {"pipelines": []}
        pipelines = self.pipeline_stats[task_type]["pipelines"]
        target = next((p for p in pipelines if p["sequence"] == sequence), None)
        if not target:
            target = {"sequence": sequence, "avg_score": 0.0, "avg_cost": 0.0,
                      "success_rate": 0.0, "runs": 0}
            pipelines.append(target)
        target["runs"] += 1
        n = target["runs"]
        target["avg_score"]    = target["avg_score"]    + (score - target["avg_score"])    / n
        target["avg_cost"]     = target["avg_cost"]     + (cost  - target["avg_cost"])     / n
        target["success_rate"] = target["success_rate"] + ((1.0 if success else 0.0) - target["success_rate"]) / n
        self._save_pipeline_stats()

    def select_best_pipeline(self, task_type: str,
                              default_pipeline: list[str]) -> tuple[list[str], bool]:
        import random
        if task_type in self.pipeline_stats and self.pipeline_stats[task_type]["pipelines"]:
            pipelines = self.pipeline_stats[task_type]["pipelines"]
            total_runs = sum(p["runs"] for p in pipelines)
            scored = []
            for p in pipelines:
                runs = p["runs"]
                if runs == 0:
                    ucb = 10.0
                else:
                    base = p["avg_score"] - 0.5 * p["avg_cost"]
                    ucb  = base + math.sqrt(math.log(total_runs + 1) / (runs + 1))
                scored.append((p["sequence"], ucb))
            scored.sort(key=lambda x: x[1], reverse=True)
            if random.random() < 0.2:
                return default_pipeline, False
            return scored[0][0], True
        return default_pipeline, False

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_cache_key(self, messages: list[dict], model: str) -> str:
        return json.dumps(messages, sort_keys=True) + model

    def _estimate_tokens(self, text: str) -> int:
        return int(len(str(text).split()) * 1.3)

    def get_models_by_quality(self, quality: str) -> list[str]:
        return [m["name"] for m in MODEL_REGISTRY
                if m["quality"] == quality and m["name"] not in self.invalid_models]

    def get_models_by_cost(self, cost: str) -> list[str]:
        return [m["name"] for m in MODEL_REGISTRY
                if m["cost"] == cost and m["name"] not in self.invalid_models]

    def get_best_cheap_model(self) -> str:
        ranked = self.rank_models()
        cheap = self.get_models_by_cost("low")
        for r in ranked:
            if r in cheap:
                return r
        return cheap[0] if cheap else MODEL_REGISTRY[0]["name"]

    def select_models(self, tier: str, complexity: str, task_type: str = "general") -> list[str]:
        count = 1 if complexity == "simple" else 2
        if tier == "cheap":
            pool = self.get_models_by_cost("low")
        elif tier in ("mid", "standard"):
            pool = self.get_models_by_quality("high")
        elif tier in ("high", "expensive"):
            pool = self.get_models_by_cost("high")
        else:
            pool = [m["name"] for m in MODEL_REGISTRY]
        ranked = self.rank_models()
        available = [r for r in ranked if r in pool]
        for r in ranked:
            if r not in available and len(available) < count:
                available.append(r)
        return available[:count]

    # ─── Core LLM Call (Fix #1: real streaming) ───────────────────────────────

    async def call(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        agent: AgentType = AgentType.ROUTER,
        task_id: str = "",
        json_mode: bool = True,
        max_retries: int = 2,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        is_fallback: bool = False,
    ) -> dict:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found")

        model_pool = [model] if model else self.rank_models()
        last_error  = "No models available"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:5173",
            "X-Title":       "AegisOps-MultiAgent",
        }

        sys_msg  = (
            "Please output your response strictly in JSON format. "
            "Provide your detailed response in an 'answer' key. "
            "If applicable, provide your confidence score in a 'confidence' key. "
            "Only output JSON."
        )
        msg_copy = messages
        if json_mode:
            if not any(m["role"] == "system" for m in messages):
                msg_copy = [{"role": "system", "content": sys_msg}] + messages
            else:
                msg_copy = []
                for m in messages:
                    if m["role"] == "system":
                        msg_copy.append({"role": "system",
                                         "content": m["content"] + "\n" + sys_msg})
                    else:
                        msg_copy.append(m)

        for current_model in model_pool:
            if not current_model:
                continue

            cache_key = self._get_cache_key(messages, current_model)
            if cache_key in self.cache:
                logger.info(f"[CACHE HIT] {current_model}")
                res = self.cache[cache_key]
                # Still stream cached answer so the frontend gets tokens
                if stream_callback and res.get("answer"):
                    answer_text = res["answer"]
                    if isinstance(answer_text, dict):
                        answer_text = json.dumps(answer_text)
                    await stream_callback(str(answer_text))
                return res

            payload = {
                "model":      current_model,
                "messages":   msg_copy,
                "max_tokens": MAX_TOKENS_PER_CALL,
                "temperature": 0.3,
                "stream":     True,   # always stream
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            for attempt in range(max_retries):
                try:
                    content       = ""
                    input_tokens  = 0
                    output_tokens = 0
                    start_time    = time.time()

                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        async with self._semaphore:
                            elapsed = time.time() - self._last_call_time
                            if elapsed < self._min_delay:
                                await asyncio.sleep(self._min_delay - elapsed)
                            self._last_call_time = time.time()

                        async with client.stream(
                            "POST", OPENROUTER_BASE_URL,
                            headers=headers, json=payload
                        ) as resp:
                            if resp.status_code == 429:
                                wait = 5 * (attempt + 1)
                                logger.warning(f"Rate-limited on {current_model}, waiting {wait}s")
                                await asyncio.sleep(wait)
                                continue
                            if resp.status_code in (500, 502, 503):
                                logger.warning(f"Server error {resp.status_code} on {current_model}")
                                await asyncio.sleep(3)
                                continue
                            if resp.status_code != 200:
                                error_body = await resp.aread()
                                logger.error(f"HTTP {resp.status_code} on {current_model}: {error_body[:200]}")
                                if resp.status_code == 404:
                                    self.invalid_models.add(current_model)
                                break

                            # ── Fix #1: stream each token immediately ──────────────
                            async for line in resp.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                data_str = line[len("data: "):].strip()
                                if data_str == "[DONE]" or not data_str:
                                    continue
                                try:
                                    chunk = json.loads(data_str)
                                    if "usage" in chunk and chunk["usage"]:
                                        u = chunk["usage"]
                                        input_tokens  = u.get("prompt_tokens", input_tokens)
                                        output_tokens = u.get("completion_tokens", output_tokens)
                                    if "choices" in chunk and chunk["choices"]:
                                        token = chunk["choices"][0].get("delta", {}).get("content", "")
                                        if token:
                                            content += token
                                            # Fire the callback immediately — real streaming
                                            if stream_callback:
                                                await stream_callback(token)
                                except Exception:
                                    pass

                    latency = time.time() - start_time
                    if input_tokens == 0:
                        input_tokens = sum(self._estimate_tokens(m["content"]) for m in msg_copy)
                    if output_tokens == 0:
                        output_tokens = self._estimate_tokens(content)
                    total_tokens = input_tokens + output_tokens
                    rate = MODEL_PRICING.get(current_model, 0.000001)
                    cost = total_tokens * rate
                    self.total_cost   += cost
                    self.total_tokens += total_tokens

                    if agent:
                        self.cost_records.append(CostRecord(
                            task_id=task_id, agent=agent, model=current_model,
                            input_tokens=input_tokens, output_tokens=output_tokens,
                            cost_usd=round(cost, 6)
                        ))

                    answer     = content
                    confidence = 0.7
                    if json_mode:
                        try:
                            cleaned = content.strip()
                            if cleaned.startswith("```"):
                                cleaned = "\n".join(cleaned.split("\n")[1:-1])
                            parsed     = json.loads(cleaned)
                            answer     = parsed.get("answer", parsed) if isinstance(parsed, dict) else parsed
                            confidence = float(parsed.get("confidence", 0.7)) if isinstance(parsed, dict) else 0.7
                        except Exception:
                            answer = content

                    # ── Fix #3: validate expected JSON keys ────────────────────
                    if json_mode and isinstance(answer, dict):
                        if "deliverable" not in answer and "answer" not in answer:
                            # LLM returned JSON but missing required keys — treat as text
                            answer = content

                    res = {
                        "model":       current_model,
                        "answer":      answer,
                        "confidence":  confidence,
                        "tokens_used": total_tokens,
                        "cost_usd":    round(cost, 6),
                        "latency":     latency,
                        "status":      "success",
                        "final_status":"success",
                    }
                    self.update_model_memory(current_model, score=confidence,
                                             cost=cost, success=True, reward=confidence)
                    self.cache[cache_key] = res
                    return res

                except httpx.TimeoutException:
                    logger.warning(f"Timeout attempt {attempt + 1} for {current_model}")
                    if attempt == max_retries - 1:
                        break
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[ERROR] {current_model}: {e}")
                    last_error = str(e)
                    break

            self.update_model_memory(current_model, score=0, cost=0,
                                     success=False, reward=0.0)
            logger.warning(f"Model {current_model} failed, trying next...")

        raise ValueError(f"All models failed. Last error: {last_error}")

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
        primary = await self.call(
            messages=messages, model=primary_model, agent=agent,
            task_id=task_id, json_mode=json_mode, stream_callback=stream_callback,
        )
        if not primary or primary.get("status") != "success":
            return primary

        primary_answer = primary.get("answer", "")
        val_prompt = (
            f"You are a quality validator. Review this response.\n\n"
            f"ORIGINAL TASK:\n{messages[-1].get('content', '') if messages else ''}\n\n"
            f"RESPONSE TO VALIDATE:\n"
            f"{json.dumps(primary_answer) if isinstance(primary_answer, dict) else str(primary_answer)}\n\n"
            "Evaluate for correctness, completeness, and quality.\n"
            'Output JSON: {"is_valid": true/false, "quality_score": 0.0-1.0, '
            '"issues": [], "improved_answer": "only if is_valid is false"}'
        )
        validator = await self.call(
            messages=[{"role": "user", "content": val_prompt}],
            model=validator_model, agent=AgentType.EVALUATOR,
            task_id=task_id, json_mode=True,
        )
        if validator and isinstance(validator, dict) and validator.get("status") == "success":
            val_answer = validator.get("answer", {})
            if isinstance(val_answer, str):
                try:
                    val_answer = json.loads(val_answer)
                except Exception:
                    val_answer = {}
            if isinstance(val_answer, dict):
                if not val_answer.get("is_valid", True) and val_answer.get("improved_answer"):
                    primary["answer"] = val_answer["improved_answer"]
                    primary["confidence"] = max(primary.get("confidence", 0.7) - 0.1, 0.3)
                else:
                    q = float(val_answer.get("quality_score", 0.7))
                    primary["confidence"] = min((primary.get("confidence", 0.7) + q) / 2, 1.0)
            primary["tokens_used"] += validator.get("tokens_used", 0)
            primary["cost_usd"]    += validator.get("cost_usd", 0.0)
            primary["validation"]   = val_answer
        primary["validator_model"]  = validator_model
        primary["execution_mode"]   = "validation"
        return primary

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
        models = self.select_models(tier, complexity, task_type)
        tasks  = [
            self.call(messages, model=m, agent=agent, task_id=task_id, json_mode=json_mode)
            for m in models
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        clean = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"[MULTI_CALL] {models[i]}: {r}")
                clean.append({"model": models[i], "error": str(r), "status": "error"})
            else:
                clean.append(r)
        return clean

    def get_cost_summary(self) -> dict:
        by_agent = {}
        by_model = {}
        for r in self.cost_records:
            by_agent[r.agent.value] = by_agent.get(r.agent.value, 0) + r.cost_usd
            by_model[r.model]       = by_model.get(r.model, 0) + r.cost_usd
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "total_tokens":   self.total_tokens,
            "by_agent":       by_agent,
            "by_model":       by_model,
        }

    def reset(self):
        self.cost_records.clear()
        self.total_cost   = 0.0
        self.total_tokens = 0


llm_client = LLMClient()
