"""Executive Strategy Agent — Plans and sequences multi-department work.

STRICT SEPARATION OF CONCERNS:
  • The Executive Agent NEVER uses LLM.
  • It ONLY creates structured plans using deterministic, rule-based logic.
  • It does NOT re-analyze the task — it executes structured directives.
  • All intelligence lives in Employee Agents.

Pipeline position:
  Classification → **Executive Agent (plan)** → Departments (execute)
"""
import json
import logging
import time
import uuid
from agents.base import BaseAgent
from core.models import AgentResult, AgentType

logger = logging.getLogger(__name__)

# Canonical department labels
VALID_DEPARTMENTS = {
    "IT",
    "HR",
    "Finance",
    "Marketing",
    "Customer Service",
    "Operations",
}


# Mapping handles to departments for label resolution
_HANDLE_TO_DEPARTMENT = {
    "@cto": "IT",
    "@cmo": "Marketing",
    "@coo": "Operations",
    "@cfo": "Finance",
    "@chro": "HR",
}


class ExecutiveAgent(BaseAgent):
    """Strategy planner that converts high-level directives into a linear execution plan.
    
    PURE RULE-BASED — NO LLM, NO RE-ANALYSIS.
    """

    agent_type = AgentType.EXECUTIVE  # Strategy tier

    def __init__(self):
        super().__init__()
        self.system_prompt = ""

    def _build_plan(self, delegations: list[dict], original_task: str) -> dict:
        """
        Pure worker: Maps incoming delegations directly to plan steps.
        Automatically selects the best employee sequence within each department using keywords.
        """
        from core.department_classifier import classify_department
        from core.workflow_engine import get_workflow
        from agents.department_agents import resolve_department
        from agents.employee_agents import EMPLOYEE_REGISTRY
        
        steps = []

        for i, d in enumerate(delegations, start=1):
            payload = d.get("payload", {})
            sub_task = payload.get("sub_task", original_task)
            
            # 1. Deterministic Department Classification
            dept_raw = classify_department(sub_task)
            if dept_raw == "Operations":
                dept_raw = payload.get("department", "Operations")
            
            dept_label = resolve_department(dept_raw)

            # 2. Get Employee Workflow (Sequence of employees for this task)
            # This expands a single delegation into 1 or more sequential steps
            emp_workflow = get_workflow(sub_task, dept_label)
            
            print(f"\n[DEBUG] Department: {dept_label}")
            print(f"[DEBUG] Selected Workflow: {emp_workflow}")
            
            for emp_id in emp_workflow:
                emp_data = EMPLOYEE_REGISTRY.get(emp_id, {})
                emp_handle = emp_data.get("handle", f"@{emp_id}")

                steps.append({
                    "department": dept_label,
                    "employee": emp_handle,
                    "task": sub_task
                })

        return {"steps": steps}

    async def execute(self, context: dict) -> AgentResult:
        """Builds a structured plan from the provided context."""
        from core.execution_tracker import execution_tracker
        
        task_id = context.get("task_id", "unknown")
        task_desc = context.get("task", "")
        delegations = context.get("delegations", [])
        
        t0 = time.time()
        logger.info(f"[Executive] Received delegation for task: {task_id}")
        
        execution_tracker.log_step(
            task_id, "Executive", self.agent_type.value, "started",
            f"Executive creating structured strategy plan...",
            model="deterministic"
        )

        # ── Map directives to plan ──
        plan = self._build_plan(delegations, task_desc)

        latency = time.time() - t0
        logger.info(f"[Executive] Created plan with {len(plan['steps'])} steps")

        execution_tracker.log_step(
            task_id, "Executive", self.agent_type.value, "completed",
            f"Plan generated: {len(plan['steps'])} steps. Decision logic: deterministic.",
            model="deterministic"
        )

        return AgentResult(
            agent=self.agent_type,
            success=True,
            output=json.dumps(plan),
            tokens_used=0,
            cost_usd=0.0,
            model_used="deterministic",
        )
