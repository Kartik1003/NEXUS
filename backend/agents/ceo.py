"""Nova CEO Agent — Autonomous AI organization leader.

STRICT SEPARATION OF CONCERNS:
  • The CEO NEVER uses LLM.
  • The CEO ONLY classifies tasks via keyword rules and delegates.
  • All intelligence lives in Employee Agents.
"""
import json
import logging
import time
import uuid
from agents.base import BaseAgent
from core.models import AgentResult, AgentType

logger = logging.getLogger(__name__)

# ─── Task Classification Constants ──────────────────────────────────────────

TASK_TYPES = [
    "coding", "debugging", "analysis", "content",
    "finance", "hr", "planning", "customer_support", "general",
]

_CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    ("debugging", [
        "debug", "bug", "fix", "error", "traceback", "exception", "crash",
        "stacktrace", "stack trace", "broken", "failing", "issue", "fault",
        "not working", "doesn't work",
    ]),
    ("coding", [
        "code", "build", "implement", "create app", "write a script",
        "function", "class", "api", "endpoint", "server", "deploy",
        "refactor", "database", "schema", "migrate", "test", "unit test",
        "architecture", "microservice", "frontend", "backend", "fullstack",
        "html", "css", "javascript", "python", "react", "node",
        "login page", "login form", "sign in page", "registration page",
        "employee portal", "staff portal", "employee details form",
        "employee management system", "hr system", "hr portal",
    ]),
    ("finance", [
        "budget", "revenue", "profit", "loss", "forecast", "financial",
        "invoice", "expense", "roi", "cash flow", "balance sheet",
        "accounting", "tax", "payroll", "cost analysis", "pricing",
    ]),
    ("analysis", [
        "analyze", "analyse", "research", "compare", "competitor",
        "market research", "data analysis", "insight", "report",
        "benchmark", "metrics", "statistics", "trend", "evaluate data",
        "survey", "study",
    ]),
    ("content", [
        "blog", "post", "article", "campaign", "ad", "brand", "social",
        "seo", "email", "copywriting", "newsletter", "tweet", "linkedin",
        "content calendar", "marketing copy", "press release", "tagline",
    ]),
    ("hr", [
        "hire", "hiring", "recruit", "recruitment", "onboard", "employee",
        "talent", "policy", "policies", "compliance", "training", "performance review",
        "benefits", "compensation", "culture", "diversity", "inclusion",
        "workforce", "retention", "termination", "leave", "payroll",
        "toolkit", "toolkits", "procedure", "procedures", "disciplinary",
        "grievance", "hr process", "step-by-step", "managers to follow",
        "leave request", "formal process", "employee handbook", "sop",
        "standard operating procedure", "hr workflow", "people process",
    ]),
    ("planning", [
        "plan", "roadmap", "strategy", "okr", "milestone", "timeline",
        "workflow", "process", "project plan", "sprint", "backlog",
        "prioritize", "prioritise", "schedule", "resource allocation",
    ]),
    ("customer_support", [
        "customer", "support", "ticket", "complaint", "feedback",
        "help desk", "satisfaction", "nps", "churn",
        "user issue", "escalation", "sla",
    ]),
    ("website", [
        "website", "web app", "web application", "landing page",
        "portal", "dashboard", "responsive site", "build a site",
        "create a website", "build a website", "develop a site",
    ]),
]

_COMPLEXITY_THRESHOLDS = {"low": 1, "medium": 3, "high": 6}
_PLANNING_TYPES = {"coding", "planning", "analysis", "finance", "hr"}

from core.department_classifier import classify_department

_EXEC_ROUTING: dict[str, str] = {
    "coding":           "@cto",
    "debugging":        "@cto",
    "analysis":         "@coo",
    "content":          "@cmo",
    "finance":          "@cfo",
    "hr":               "@chro",
    "planning":         "@coo",
    "customer_support": "@coo",
    "general":          "@coo",
}

_EXEC_DEPARTMENT: dict[str, str] = {
    "coding":           "IT",
    "debugging":        "IT",
    "analysis":         "Operations",
    "content":          "Marketing",
    "finance":          "Finance",
    "hr":               "HR",
    "planning":         "Operations",
    "customer_support": "Customer Service",
    "general":          "Operations",
}

# ── Fix #11: added hr, finance, customer_support multi-dept workflows ─────────
_MULTI_DEPT_WORKFLOWS: dict[str, list[tuple[str, str]]] = {
    "analysis": [
        ("Operations", "Conduct deep research and gather critical data/insights on the subject."),
        ("Operations", "Analyze research outputs and synthesize into actionable strategy."),
    ],
    "planning": [
        ("Operations", "Develop comprehensive project roadmap with milestones and resource allocation."),
        ("Finance",    "Perform financial risk assessment and budget validation for the proposed plan."),
    ],
    "coding": [
        ("IT", "Design, build, and deliver the complete working implementation as specified."),
    ],
    "website": [
        ("Operations", "Create a detailed project plan, technical spec, and implementation roadmap."),
        ("IT",         "Implement the complete website: frontend, backend, and QA testing."),
    ],
    # ── NEW: previously missing workflows ──────────────────────────────────
    "hr": [
        ("HR",      "Develop the complete HR policy, process, or talent strategy as specified."),
        ("Finance", "Review compensation implications, budget impact, and financial compliance of the HR initiative."),
    ],
    "finance": [
        ("Finance",    "Produce the full financial analysis, model, or report as specified."),
        ("Operations", "Validate operational feasibility and cross-department impact of the financial recommendation."),
    ],
    "customer_support": [
        ("Customer Service", "Resolve the customer issue, draft the response, or build the support process."),
        ("Operations",       "Identify root-cause process improvements to prevent recurrence."),
    ],
}


class CEOAgent(BaseAgent):
    """Nova — the CEO.  Classifies, delegates, never solves.  NO LLM."""

    agent_type = AgentType.CEO
    system_prompt = ""

    @staticmethod
    def classify_task(description: str) -> dict:
        text = description.lower()

        matched_type = "general"
        total_hits = 0
        type_hits: dict[str, int] = {}

        for ttype, keywords in _CLASSIFICATION_RULES:
            hits = sum(1 for kw in keywords if kw in text)
            if hits > 0:
                type_hits[ttype] = hits
                total_hits += hits

        if type_hits:
            matched_type = max(type_hits, key=type_hits.get)

        word_count = len(text.split())
        if total_hits >= _COMPLEXITY_THRESHOLDS["high"] or word_count > 200:
            complexity = "high"
        elif total_hits >= _COMPLEXITY_THRESHOLDS["medium"] or word_count > 80:
            complexity = "medium"
        else:
            complexity = "low"

        requires_planning = (matched_type in _PLANNING_TYPES or complexity == "high")
        assigned_to = _EXEC_ROUTING.get(matched_type, "@coo")

        return {
            "task_type":         matched_type,
            "complexity":        complexity,
            "requires_planning": requires_planning,
            "assigned_to":       assigned_to,
        }

    @staticmethod
    def _build_delegation(task_desc: str, task_id: str, classification: dict) -> dict:
        """Build the full CEO delegation JSON deterministically.
        Fix #4: removed stray code fragment that was copy-pasted from orchestrator.
        """
        assigned_to = classification["assigned_to"]
        task_type   = classification["task_type"]

        delegations = []

        if task_type in _MULTI_DEPT_WORKFLOWS and classification["complexity"] != "low":
            workflow = _MULTI_DEPT_WORKFLOWS[task_type]
            for i, (dept, directive) in enumerate(workflow, start=1):
                delegations.append({
                    "from":     "@ceo",
                    "to":       assigned_to,
                    "task_id":  f"{task_id}_d{i}",
                    "type":     "delegation",
                    "priority": "HIGH" if i == 1 else "STANDARD",
                    "payload":  {
                        "department":       dept,
                        "sub_task":         f"{directive} Task: {task_desc}",
                        "expected_output":  f"Deliverable for {dept} phase",
                        "deadline":         "end_of_day",
                    },
                })
        else:
            department = classify_department(task_desc)
            if department == "Operations":
                department = _EXEC_DEPARTMENT.get(task_type, "Operations")

            delegations.append({
                "from":     "@ceo",
                "to":       assigned_to,
                "task_id":  f"{task_id}_d1",
                "type":     "delegation",
                "priority": "STANDARD",
                "payload":  {
                    "department":      department,
                    "sub_task":        task_desc,
                    "expected_output": f"Complete deliverable for: {task_desc[:100]}",
                    "deadline":        "end_of_day",
                },
            })

        dept_summary = ", ".join(sorted({d["payload"]["department"] for d in delegations}))
        ceo_summary  = (
            f"Task classified as '{task_type}' ({classification['complexity']}). "
            f"Mandating {len(delegations)} phase(s) across {dept_summary}. "
            f"Delegating strategy to {assigned_to}."
        )

        urgency_map = {"high": "CRITICAL", "medium": "STANDARD", "low": "BACKGROUND"}
        urgency = urgency_map.get(classification["complexity"], "STANDARD")

        return {
            "task_id":          task_id,
            "original_request": task_desc,
            "task_type":        task_type,
            "complexity":       classification["complexity"],
            "requires_planning":classification["requires_planning"],
            "assigned_to":      assigned_to,
            "ceo_summary":      ceo_summary,
            "urgency":          urgency,
            "delegations":      delegations,
            "synthesis_needed": len(delegations) > 1,
            "final_deliverable":f"Complete deliverable for: {task_desc[:100]}",
        }

    async def execute(self, context: dict) -> AgentResult:
        from core.execution_tracker import execution_tracker

        task_desc = context.get("task", "")
        task_id   = context.get("task_id", uuid.uuid4().hex[:12])
        t0 = time.time()

        execution_tracker.log_step(task_id, "CEO", self.agent_type.value, "started",
            f"CEO analyzing task: {task_desc[:50]}...", model="deterministic")

        classification = self.classify_task(task_desc)
        logger.info(
            f"[CEO] type={classification['task_type']} "
            f"complexity={classification['complexity']} "
            f"→ {classification['assigned_to']}"
        )
        execution_tracker.log_step(task_id, "CEO", self.agent_type.value, "in_progress",
            f"Classification: {classification['task_type']} / {classification['complexity']}",
            model="deterministic")

        delegation = self._build_delegation(task_desc, task_id, classification)

        latency = time.time() - t0
        logger.info(f"[CEO] Delegation done in {latency:.3f}s → {classification['assigned_to']}")

        execution_tracker.log_step(task_id, "CEO", self.agent_type.value, "completed",
            f"Delegated to {classification['assigned_to']}", model="deterministic")

        return AgentResult(
            agent=self.agent_type,
            success=True,
            output=json.dumps(delegation),
            tokens_used=0,
            cost_usd=0.0,
            model_used="deterministic",
        )
