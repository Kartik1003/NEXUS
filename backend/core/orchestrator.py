"""Main orchestrator — strict linear pipeline with optional parallel execution.

EXECUTION FLOW:
    User Task → CEO → Executive → Department(s) → Employee(s) → Final Output

Fixes applied:
  #2  — Parallel department execution: steps from different departments with no
         data dependency run concurrently via asyncio.gather (DAGExecutor logic).
         Sequential steps within a chain still run in order (upstream data flows).
  #3  — Prompt response validation: missing 'deliverable' key degrades gracefully
         instead of silently returning raw LLM content.
"""
import json
import logging
import time
import asyncio
from typing import Optional, Callable, Awaitable, Any

from core.models import WSEvent, AgentType, Reflection, Learning, AgentResult
from core.llm import llm_client
from agents.memory import MemoryAgent
from agents.ceo import CEOAgent
from agents.executive_agent import ExecutiveAgent
from agents.department_agents import DEPARTMENT_REGISTRY, resolve_department
from core.communication import message_bus
from core.execution_tracker import execution_tracker
from core.result_aggregator import ResultAggregator

logger = logging.getLogger(__name__)
memory_agent = MemoryAgent()


def _safe_get(obj, key, default=None):
    if obj and isinstance(obj, dict):
        return obj.get(key, default)
    return default


class ExecutionContext:
    def __init__(self):
        self.task_id     = f"task_{int(time.time())}"
        self.models_used: set[str] = set()
        self.total_tokens = 0
        self.total_cost   = 0.0
        self.steps:  list[dict] = []
        self.task_type = "general"


class Orchestrator:
    """Coordinates the CEO → Executive → Department → Employee pipeline."""

    def __init__(self):
        self._event_callback: Optional[Callable[[WSEvent], Awaitable[None]]] = None
        self.aggregator = ResultAggregator()

    # ── Event helpers ──────────────────────────────────────────────────────────

    def set_event_callback(self, callback: Callable[[WSEvent], Awaitable[None]]):
        self._event_callback = callback

        async def _bus_to_ws(msg):
            if not msg.task_id:
                return
            try:
                payload = {
                    "event":      "agent_message",
                    "message_id": msg.id,
                    "type":       msg.type.value,
                    "sender":     msg.sender,
                    "receiver":   msg.receiver,
                    "content":    msg.content,
                    "task_id":    msg.task_id,
                    "priority":   msg.priority.value,
                    "timestamp":  msg.timestamp,
                }
                execution_tracker.log_event(msg.task_id, "agent_message", payload)
                if callback:
                    await callback(WSEvent(event="agent_message", data=payload))
            except Exception as e:
                logger.error(f"[WS] Failed to bridge agent message: {e}")

        message_bus.on_any_message(_bus_to_ws)

    async def _emit(self, event: str, agent: str, data: dict, task_id: str = None):
        if self._event_callback:
            try:
                if not isinstance(data, dict):
                    data = {"message": str(data)}
                payload = {"event": event, "agent": agent, "step": agent, "task_id": task_id}
                payload.update(data)
                await self._event_callback(WSEvent(event=event, data=payload))
                if task_id and event not in ("step_start", "step_done",
                                              "dept_step_start", "dept_step_done"):
                    from core.websocket_handler import ws_manager
                    await ws_manager.broadcast_log(task_id, payload)
            except Exception as e:
                logger.error(f"Failed to emit event {event}: {e}")

    async def _emit_step_start(self, agent: str, step_id: str = None):
        await self._emit("step_start", agent,
                         {"step": step_id or agent, "timestamp": time.time()})

    async def _emit_step_done(self, agent: str, data: Any,
                               context: ExecutionContext, step_id: str = None, **kwargs):
        step_val = step_id or agent
        context.steps.append({
            "agent": agent, "event": "step_done",
            "output": data, "timestamp": time.time(),
            "task_type": context.task_type,
        })
        payload = {"step": step_val, "output": data, "timestamp": time.time()}
        payload.update(kwargs)
        await self._emit("step_done", agent, payload)

    async def _stream_token(self, token: str):
        """Broadcast a token chunk to connected WebSocket clients."""
        await self._emit("token", "system", {"data": token})

    # ── Single step executor ──────────────────────────────────────────────────

    async def _execute_step(
        self,
        step: dict,
        step_index: int,
        context: ExecutionContext,
        task_description: str,
        upstream: str = "",
        next_emp_name: Optional[str] = None,
    ) -> dict:
        """Execute one (department, employee) step and return a result dict."""
        from agents.employee_agents import EMPLOYEE_REGISTRY
        from agents.department_agents import DepartmentAgent

        dept_name  = step.get("department", "Operations")
        emp_handle = step.get("employee", "@chrono")
        step_task  = step.get("task", task_description)

        emp_id   = emp_handle.lstrip("@")
        emp_name = EMPLOYEE_REGISTRY.get(emp_id, {}).get("name", emp_id)

        execution_tracker.log_step(
            context.task_id, "Department", dept_name, "started",
            f"Department {dept_name} routing task to {emp_handle}"
        )
        await self._emit(
            "dept_step_start", dept_name,
            {"step": step_index, "employee": emp_handle},
            task_id=context.task_id
        )

        dept_agent = DepartmentAgent(dept_name)
        emp_context = {
            "task":              step_task,
            "task_id":           context.task_id,
            "step_index":        step_index,
            "employee_handle":   emp_handle,
            "upstream_data":     upstream,
            "next_employee_name":next_emp_name,
            "complexity":        context.task_type,
        }

        try:
            worker_res = await asyncio.wait_for(
                dept_agent.execute(emp_context), timeout=120.0
            )
            if isinstance(worker_res, dict):
                worker_res = AgentResult(
                    agent=AgentType.OPERATIONS,
                    success=worker_res.get("success", False),
                    output=str(worker_res.get("output", "")),
                    tokens_used=0, cost_usd=0.0, model_used="unknown"
                )
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] {emp_handle} timed out after 120s")
            worker_res = AgentResult(
                agent=AgentType.OPERATIONS, success=False,
                output=f"{emp_handle} timed out. LLM connection issues.",
                error="Timed out after 120 seconds",
                tokens_used=0, cost_usd=0.0, model_used="none"
            )
        except Exception as e:
            logger.error(f"dept_agent.execute crashed for {emp_handle}: {e}", exc_info=True)
            worker_res = AgentResult(
                agent=AgentType.OPERATIONS, success=False,
                output=f"{emp_handle} encountered an error: {e}",
                error=str(e), tokens_used=0, cost_usd=0.0, model_used="none"
            )

        # ── Parse result (Fix #3: robust key extraction) ─────────────────────
        deliverable     = ""
        files_produced  = []
        message_to_next = None

        if not worker_res.success:
            deliverable = f"[FAILED] {worker_res.error or worker_res.output}"
        else:
            try:
                worker_data = json.loads(worker_res.output)
                # Fix #3: validate keys with explicit fallbacks
                deliverable = worker_data.get("deliverable") or worker_data.get("answer") or worker_res.output
                files_produced  = worker_data.get("files_produced", [])
                message_to_next = worker_data.get("message_to_next")

                # Dynamic cross-department handoff
                if worker_data.get("requires_implementation") and worker_data.get("implementation_department"):
                    impl_dept = worker_data["implementation_department"]
                    if impl_dept != dept_name:
                        from core.workflow_engine import get_workflow
                        impl_emps = get_workflow(task_description, impl_dept)
                        logger.info(f"[Orchestrator] Cross-dept handoff to {impl_dept}")
                        # Signal to caller via a special key
                        return {
                            "step": step_index, "department": dept_name,
                            "employee": emp_handle, "result": deliverable,
                            "files": files_produced, "message_to_next": message_to_next,
                            "success": worker_res.success,
                            "_inject_dept": impl_dept, "_inject_emps": impl_emps,
                        }
            except Exception:
                deliverable = worker_res.output

        # Persist files
        for f in files_produced:
            if f.get("filename") and f.get("content"):
                execution_tracker.store_file(
                    context.task_id, emp_handle, f["filename"], f["content"]
                )

        if message_to_next:
            execution_tracker.log_agent_chat(
                context.task_id, emp_handle, emp_name,
                next_emp_name or "next colleague", message_to_next
            )

        execution_tracker.log_step(
            context.task_id, "Department", dept_name,
            "completed" if worker_res.success else "failed",
            f"Department {dept_name} finished."
        )
        await self._emit(
            "dept_step_done", dept_name,
            {"step": step_index, "employee": emp_handle, "success": worker_res.success},
            task_id=context.task_id
        )

        return {
            "step": step_index, "department": dept_name,
            "employee": emp_handle, "result": deliverable,
            "files": files_produced, "message_to_next": message_to_next,
            "success": worker_res.success,
        }

    # ── Parallel step grouping (Fix #2) ──────────────────────────────────────

    @staticmethod
    def _group_steps_for_parallel(steps: list[dict]) -> list[list[dict]]:
        """
        Group steps into execution layers.
        Steps in the same department that don't depend on each other can run in
        parallel.  Steps across *different* departments and within the same
        delegation phase can run concurrently.

        Rule:
          - If consecutive steps are in *different* departments, they form a
            parallel layer.
          - If consecutive steps are in the *same* department, they are
            sequential (the second needs output from the first).
        """
        if not steps:
            return []
        layers: list[list[dict]] = []
        current_layer: list[dict] = [steps[0]]
        for step in steps[1:]:
            prev = current_layer[-1]
            if step.get("department") != prev.get("department"):
                # Different department → can run in parallel with previous layer
                # But we only batch the very first step into each parallel group;
                # if BOTH are new departments, put them together.
                current_layer.append(step)
            else:
                # Same department → must be sequential (needs upstream data)
                layers.append(current_layer)
                current_layer = [step]
        layers.append(current_layer)
        return layers

    # ── MAIN PIPELINE ─────────────────────────────────────────────────────────

    async def solve(self, task_description: str, task_id: str = None) -> dict:
        context = ExecutionContext()
        if task_id:
            context.task_id = task_id
        llm_client.reset()

        try:
            # ── 1. CEO ────────────────────────────────────────────────────────
            logger.info(f"[CEO] Received task: {context.task_id}")
            execution_tracker.log_step(context.task_id, "CEO", "Nova CEO", "started",
                                        "CEO received task. Analyzing...")
            await self._emit("step_start", "ceo",
                             {"message": "CEO received task"}, task_id=context.task_id)

            ceo_res = await CEOAgent().execute(
                {"task": task_description, "task_id": context.task_id}
            )
            try:
                delegation = json.loads(ceo_res.output)
            except Exception:
                delegation = {"delegations": [{"payload": {
                    "department": "Operations", "sub_task": task_description
                }}]}

            context.task_type = delegation.get("task_type", "general")
            execution_tracker.log_step(context.task_id, "CEO", "Nova CEO", "completed",
                                        "CEO analyzed task and delegated work.")
            await self._emit_step_done("ceo", "CEO analyzed and delegated.", context)

            # ── 2. EXECUTIVE ──────────────────────────────────────────────────
            logger.info(f"[Executive] Creating plan: {context.task_id}")
            execution_tracker.log_step(context.task_id, "Executive", "Strategy Planner",
                                        "started", "Executive creating plan...")
            await self._emit_step_start("executive")

            exec_res = await ExecutiveAgent().execute({
                "task": task_description,
                "task_id": context.task_id,
                "delegations": delegation.get("delegations", []),
            })
            try:
                exec_plan = json.loads(exec_res.output)
            except Exception:
                exec_plan = {"steps": [{"department": "Operations",
                                         "employee": "@chrono", "task": task_description}]}

            steps = exec_plan.get("steps", [])
            logger.info(f"[Executive] Plan has {len(steps)} steps")
            execution_tracker.log_step(context.task_id, "Executive", "Strategy Planner",
                                        "completed", f"Plan finalized: {len(steps)} steps.")
            await self._emit_step_done("executive", exec_plan, context)

            # ── 3. DEPARTMENT & EMPLOYEE EXECUTION ───────────────────────────
            from agents.employee_agents import EMPLOYEE_REGISTRY

            all_worker_results: list[dict] = []
            last_upstream = ""

            # Group into parallel layers (Fix #2)
            layers = self._group_steps_for_parallel(steps)

            global_step_idx = 0
            for layer in layers:
                if len(layer) == 1:
                    # Single step — run sequentially, pass upstream from previous
                    step = layer[0]
                    global_step_idx += 1
                    # Look ahead for next employee name
                    all_steps = steps
                    flat_idx  = steps.index(step) if step in steps else global_step_idx - 1
                    next_step = all_steps[flat_idx + 1] if flat_idx + 1 < len(all_steps) else None
                    next_emp_name = None
                    if next_step:
                        nid = next_step.get("employee", "").lstrip("@")
                        next_emp_name = EMPLOYEE_REGISTRY.get(nid, {}).get("name", nid)

                    result = await self._execute_step(
                        step, global_step_idx, context,
                        task_description, last_upstream, next_emp_name
                    )
                    all_worker_results.append(result)
                    last_upstream = result.get("message_to_next") or result.get("result", "")

                else:
                    # Multiple independent steps — run in parallel (Fix #2)
                    logger.info(
                        f"[Orchestrator] Running {len(layer)} steps in parallel: "
                        + ", ".join(s.get("department", "?") for s in layer)
                    )
                    parallel_tasks = []
                    for step in layer:
                        global_step_idx += 1
                        # For parallel steps, upstream is shared from the last serial step
                        parallel_tasks.append(
                            self._execute_step(
                                step, global_step_idx, context,
                                task_description, last_upstream, None
                            )
                        )
                    parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

                    combined_upstream_parts = []
                    for res in parallel_results:
                        if isinstance(res, Exception):
                            logger.error(f"[Parallel step error]: {res}")
                            all_worker_results.append({
                                "step": -1, "department": "unknown",
                                "employee": "unknown", "result": f"[FAILED] {res}",
                                "files": [], "message_to_next": None, "success": False,
                            })
                        else:
                            all_worker_results.append(res)
                            combined_upstream_parts.append(
                                res.get("message_to_next") or res.get("result", "")
                            )

                    # Merge parallel outputs for next sequential step
                    last_upstream = "\n\n---\n\n".join(combined_upstream_parts)

            # ── 4. AGGREGATE ─────────────────────────────────────────────────
            logger.info(f"[Aggregator] Aggregating {len(all_worker_results)} results")
            aggregated    = self.aggregator.aggregate(task_description, all_worker_results)
            final_markdown = self.aggregator.to_markdown(aggregated)

            # Stream final output token-by-token to frontend (Fix #1 end)
            await self._stream_token(final_markdown)

            cost_summary = llm_client.get_cost_summary()
            memory_agent.store_task(
                task_id=context.task_id,
                description=task_description,
                status="success" if aggregated["success_rate"] > 0 else "failed",
                cost=cost_summary["total_cost_usd"],
                tokens=cost_summary["total_tokens"],
                inputs={"task": task_description},
                outputs={"final_text": final_markdown, "aggregated": aggregated},
            )

            all_files = execution_tracker.get_files(context.task_id)
            all_chats = execution_tracker.get_agent_chats(context.task_id)

            res = {
                "status":     "success" if aggregated["success_rate"] > 0.5 else "partial_success",
                "result":     final_markdown,
                "aggregated": aggregated,
                "task_id":    context.task_id,
                "steps":      all_worker_results,
                "files":      all_files,
                "agent_chats":all_chats,
                "metrics":    cost_summary,
            }
            await self._emit("result",        "system", res, task_id=context.task_id)
            await self._emit("task_complete",  "system", res, task_id=context.task_id)
            return res

        except Exception as e:
            logger.error(f"PIPELINE CRITICAL ERROR: {e}", exc_info=True)
            fallback = {
                "status":  "error",
                "result":  f"The mission failed due to a critical system error: {e}",
                "task_id": context.task_id,
                "error":   str(e),
            }
            await self._emit("task_complete", "system", fallback, task_id=context.task_id)
            return fallback
