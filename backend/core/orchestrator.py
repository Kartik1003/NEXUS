"""Main orchestrator — strict linear pipeline.

EXECUTION FLOW (no exceptions):
    User Task → CEO → Executive → Department(s) → Employee(s) → Final Output

RULES:
    • No levels are ever skipped.
    • No parallel random agents.
    • No Judge, Reflect, Debate, or any extra agents.
    • LLM calls happen ONLY inside Employee agents.
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
from agents.department_agents import (
    DEPARTMENT_REGISTRY,
    resolve_department,
)
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
    """Lightweight state bag for a single task run."""

    def __init__(self):
        self.task_id = f"task_{int(time.time())}"
        self.models_used: set[str] = set()
        self.total_tokens = 0
        self.total_cost = 0.0
        self.steps: list[dict] = []
        self.task_type = "general"


class Orchestrator:
    """Coordinates the strict CEO → Executive → Department → Employee pipeline."""

    def __init__(self):
        self._event_callback: Optional[Callable[[WSEvent], Awaitable[None]]] = None
        self.aggregator = ResultAggregator()

    # ── Event helpers ─────────────────────────────────────────────

    def set_event_callback(self, callback: Callable[[WSEvent], Awaitable[None]]):
        self._event_callback = callback
        # Bridge inter-agent messages to the frontend
        async def _bus_to_ws(msg):
            if not msg.task_id:
                return

            try:
                payload = {
                    "event": "agent_message",
                    "message_id": msg.id,
                    "type": msg.type.value,
                    "sender": msg.sender,
                    "receiver": msg.receiver,
                    "content": msg.content,
                    "task_id": msg.task_id,
                    "priority": msg.priority.value,
                    "timestamp": msg.timestamp,
                }
                # Log to tracker for persistence in OutputPage
                execution_tracker.log_event(msg.task_id, "agent_message", payload)
                
                # Broadcast to global dashboard (/ws)
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
                
                # We skip manual ws_manager broadcast here if it's an execution log,
                # because execution_tracker.log_step() already handles it via bridge.
                # However, for non-log events (like 'token' or 'result'), we still need broadcasting.
                if task_id and event not in ["step_start", "step_done", "dept_step_start", "dept_step_done"]:
                    from core.websocket_handler import ws_manager
                    await ws_manager.broadcast_log(task_id, payload)
            except Exception as e:
                logger.error(f"Failed to emit event {event}: {e}")

    async def _emit_step_start(self, agent: str, step_id: str = None):
        step_val = step_id if step_id else agent
        await self._emit("step_start", agent, {"step": step_val, "timestamp": time.time()})

    async def _emit_step_done(self, agent: str, data: Any, context: ExecutionContext, step_id: str = None, **kwargs):
        step_val = step_id if step_id else agent
        context.steps.append({
            "agent": agent,
            "event": "step_done",
            "output": data,
            "timestamp": time.time(),
            "task_type": context.task_type,
        })
        payload = {"step": step_val, "output": data, "timestamp": time.time()}
        payload.update(kwargs)
        await self._emit("step_done", agent, payload)

    async def _emit_metrics(self, context: ExecutionContext):
        await self._emit("metrics", "system", {
            "models_used": list(context.models_used),
            "tokens": context.total_tokens,
            "cost": context.total_cost,
        })

    async def _stream_token(self, token: str):
        await self._emit("token", "system", {"data": token})

    # ──────────────────────────────────────────────────────────────
    # MAIN PIPELINE:  CEO → Executive → Department → Employee
    # ──────────────────────────────────────────────────────────────

    async def solve(self, task_description: str, task_id: str = None) -> dict:
        """
        STRICT LINEAR PIPELINE:
        User Task → CEO → Executive → Department → Employee → Final Output
        """
        context = ExecutionContext()
        if task_id: context.task_id = task_id
        llm_client.reset()

        try:
            # ── 1. CEO (Nova) ──
            print(f"\n[DEBUG] CEO: Received task: {task_description[:100]}...")
            logger.info(f"--- CEO RECEIVED TASK: {context.task_id} ---")
            execution_tracker.log_step(context.task_id, "CEO", "Nova CEO", "started", "CEO received task. Analyzing...")
            await self._emit("step_start", "ceo", {"message": "CEO received task"}, task_id=context.task_id)

            ceo_agent = CEOAgent()
            ceo_res = await ceo_agent.execute({"task": task_description, "task_id": context.task_id})
            
            try:
                delegation = json.loads(ceo_res.output)
            except:
                delegation = {"delegations": [{"payload": {"department": "Operations", "sub_task": task_description}}]}

            execution_tracker.log_step(context.task_id, "CEO", "Nova CEO", "completed", "CEO analyzed task and delegated work.")
            await self._emit_step_done("ceo", "CEO analyzed and delegated.", context)

            # ── 2. EXECUTIVE (Strategy) ──
            logger.info(f"--- EXECUTIVE CREATING PLAN: {context.task_id} ---")
            execution_tracker.log_step(context.task_id, "Executive", "Strategy Planner", "started", "Executive received directives. Creating plan...")
            await self._emit_step_start("executive")

            exec_agent = ExecutiveAgent()
            exec_res = await exec_agent.execute({
                "task": task_description, 
                "task_id": context.task_id,
                "delegations": delegation.get("delegations", [])
            })
            
            try:
                exec_plan = json.loads(exec_res.output)
            except:
                # Emergency fallback plan
                exec_plan = {"steps": [{"department": "Operations", "employee": "@chrono", "task": task_description}]}

            print(f"[DEBUG] Executive: Plan created with {len(exec_plan.get('steps', []))} steps")
            logger.info(f"Executive created plan with {len(exec_plan.get('steps', []))} steps")
            execution_tracker.log_step(context.task_id, "Executive", "Strategy Planner", "completed", f"Plan finalized with {len(exec_plan.get('steps', []))} steps.")
            await self._emit_step_done("executive", exec_plan, context)

            # ── 3. DEPARTMENT & EMPLOYEE (Execution) ──
            all_worker_results = []
            
            for i, step in enumerate(exec_plan.get("steps", []), 1):
                dept_name = step.get("department", "Operations")
                emp_handle = step.get("employee", "@worker")
                step_task = step.get("task", task_description)

                # Department Routing
                print(f"[DEBUG] Department: Assigned to employee: {emp_handle} (Dept: {dept_name})")
                logger.info(f"--- DEPARTMENT ROUTING: {dept_name} → {emp_handle} ---")
                execution_tracker.log_step(context.task_id, "Department", dept_name, "started", f"Department {dept_name} routing task to {emp_handle}")
                await self._emit("dept_step_start", dept_name, {"step": i, "employee": emp_handle}, task_id=context.task_id)

                # Employee Execution (LLM call here)
                from agents.employee_agents import EMPLOYEE_REGISTRY
                # Resolve name from handle/id
                emp_id = emp_handle.lstrip("@")
                emp_name = EMPLOYEE_REGISTRY.get(emp_id, {}).get("name", emp_id)
                print(f"[DEBUG] {emp_name} ({emp_handle}) executing...")
                
                logger.info(f"--- EMPLOYEE EXECUTION: {emp_handle} ---")
                from agents.department_agents import DepartmentAgent
                dept_agent = DepartmentAgent(dept_name)
                
                # Use data from previous step as context
                upstream = all_worker_results[-1]["result"] if all_worker_results else ""

                # Look ahead to find the next employee's name
                steps_list = exec_plan.get("steps", [])
                next_step = steps_list[i] if i < len(steps_list) else None  # i is 1-based, index i is next
                next_emp_handle = next_step.get("employee") if next_step else None
                next_emp_name = None
                if next_emp_handle:
                    next_emp_id = next_emp_handle.lstrip("@")
                    next_emp_data = EMPLOYEE_REGISTRY.get(next_emp_id, {})
                    next_emp_name = next_emp_data.get("name") or next_emp_id

                emp_context = {
                    "task": step_task,
                    "task_id": context.task_id,
                    "step_index": i,
                    "employee_handle": emp_handle,
                    "upstream_data": upstream,
                    "next_employee_name": next_emp_name,
                    "complexity": context.task_type,
                }

                try:
                    # Robust execution with 120s timeout limit for the whole employee agent cycle
                    worker_res = await asyncio.wait_for(
                        dept_agent.execute(emp_context),
                        timeout=120.0
                    )
                    # Safety check: if something still returns a dict, convert it
                    if isinstance(worker_res, dict):
                        worker_res = AgentResult(
                            agent=AgentType.OPERATIONS,
                            success=worker_res.get("success", False),
                            output=str(worker_res.get("output", "")),
                            tokens_used=0,
                            cost_usd=0.0,
                            model_used="unknown"
                        )
                except asyncio.TimeoutError:
                    logger.error(f"[TIMEOUT] Employee {emp_handle} timed out after 120s.")
                    worker_res = AgentResult(
                        agent=AgentType.OPERATIONS,
                        success=False,
                        output=f"Employee {emp_handle} timed out while processing this task. LLM connection issues.",
                        error="Department agent timed out after 120 seconds",
                        tokens_used=0,
                        cost_usd=0.0,
                        model_used="none"
                    )
                except Exception as e:
                    logger.error(f"dept_agent.execute crashed for {emp_handle}: {e}",
                                 exc_info=True)
                    worker_res = AgentResult(
                        agent=AgentType.OPERATIONS,
                        success=False,
                        output=f"Employee {emp_handle} encountered an error: {str(e)}",
                        error=str(e),
                        tokens_used=0,
                        cost_usd=0.0,
                        model_used="none"
                    )

                deliverable = ""
                worker_data = {}
                files_produced = []
                message_to_next = None
                upstream_for_next = ""

                if not worker_res.success:
                    deliverable = f"[FAILED] This phase encountered an error: {worker_res.error or worker_res.output}"
                    upstream_for_next = deliverable
                else:
                    try:
                        worker_data = json.loads(worker_res.output)
                        deliverable  = worker_data.get("deliverable", worker_res.output)
                        files_produced = worker_data.get("files_produced", [])
                        message_to_next = worker_data.get("message_to_next")
                        # ── Dynamic cross-department handoff ──────────────────────────────────
                        requires_impl  = worker_data.get("requires_implementation", False)
                        impl_dept      = worker_data.get("implementation_department")

                        if requires_impl and impl_dept and impl_dept != current_step.get("department"):
                            from core.workflow_engine import get_workflow
                            from agents.employee_agents import EMPLOYEE_REGISTRY

                            impl_employees = get_workflow(task_desc, impl_dept)

                            # Only inject steps that are not already in the remaining plan
                            existing_handles = {s.get("employee") for s in remaining_steps}
                            injected = []
                            for emp_id in impl_employees:
                                emp_data  = EMPLOYEE_REGISTRY.get(emp_id, {})
                                emp_handle = emp_data.get("handle", f"@{emp_id}")
                                if emp_handle not in existing_handles:
                                    injected.append({
                                        "department": impl_dept,
                                        "employee":   emp_handle,
                                        "task":       task_desc
                                    })

                            if injected:
                                remaining_steps = injected + remaining_steps  # prepend so they run next
                                logger.info(
                                    f"[Orchestrator] Injected {len(injected)} implementation step(s) "
                                    f"for department '{impl_dept}' after handoff signal from {current_step.get('employee')}"
                                )
                    except Exception:
                        deliverable = worker_res.output

                # Store each file in the execution tracker
                for f in files_produced:
                    if f.get("filename") and f.get("content"):
                        execution_tracker.store_file(
                            context.task_id, emp_handle,
                            f["filename"], f["content"]
                        )

                # Log the chat message if present
                if message_to_next:
                    execution_tracker.log_agent_chat(
                        context.task_id,
                        from_handle=emp_handle,
                        from_name=emp_name,
                        to_name=next_emp_name or "next colleague",
                        message=message_to_next,
                    )

                # For the next employee's upstream: prefer the message_to_next
                # (it's richer — tells them what was built AND what to do next)
                # Fall back to deliverable if no message was written
                upstream_for_next = message_to_next or deliverable

                print(f"[DEBUG] Employee: Result summary: {deliverable[:75]}...")
                upstream = upstream_for_next if all_worker_results else upstream_for_next
                all_worker_results.append({
                    "step": i,
                    "department": dept_name,
                    "employee": emp_handle,
                    "result": deliverable,
                    "files": files_produced,
                    "message_to_next": message_to_next,
                    "success": worker_res.success
                })
                
                execution_tracker.log_step(context.task_id, "Department", dept_name, "completed" if worker_res.success else "failed", f"Department {dept_name} routing finished.")
                await self._emit("dept_step_done", dept_name, {"step": i, "employee": emp_handle, "success": worker_res.success}, task_id=context.task_id)

            # ── 4. STACK DATA & AGGREGATE ──
            print("[DEBUG] Final: Aggregating worker results")
            logger.info(f"--- AGGREGATING RESULTS: {context.task_id} ---")
            
            aggregated = self.aggregator.aggregate(task_description, all_worker_results)
            final_markdown = self.aggregator.to_markdown(aggregated)
            
            await self._stream_token(final_markdown)
            
            # Store in memory
            cost_summary = llm_client.get_cost_summary()
            memory_agent.store_task(
                task_id=context.task_id,
                description=task_description,
                status="success" if aggregated["success_rate"] > 0 else "failed",
                cost=cost_summary["total_cost_usd"],
                tokens=cost_summary["total_tokens"],
                inputs={"task": task_description},
                outputs={"final_text": final_markdown, "aggregated": aggregated}
            )

            all_files = execution_tracker.get_files(context.task_id)
            all_chats = execution_tracker.get_agent_chats(context.task_id)

            res = {
                "status": "success" if aggregated["success_rate"] > 0.5 else "partial_success",
                "result": final_markdown,
                "aggregated": aggregated,
                "task_id": context.task_id,
                "steps": all_worker_results,
                "files": all_files,
                "agent_chats": all_chats,
                "metrics": cost_summary
            }
            
            await self._emit("result", "system", res, task_id=context.task_id)
            await self._emit("task_complete", "system", res, task_id=context.task_id)
            return res

        except Exception as e:
            logger.error(f"PIPELINE CRITICAL ERROR: {e}", exc_info=True)
            fallback_res = {
                "status": "error",
                "result": f"The mission failed due to a critical system error: {str(e)}",
                "task_id": context.task_id,
                "error": str(e)
            }
            await self._emit("task_complete", "system", fallback_res, task_id=context.task_id)
            return fallback_res


