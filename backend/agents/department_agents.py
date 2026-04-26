"""Department Agents — Six autonomous department heads that receive tasks
from the Executive Agent's plan, select the right employees, and manage
execution within their domain.

STRICT SEPARATION OF CONCERNS:
  • Department Agents NEVER use LLM.
  • They ONLY route tasks to the correct manager/employee.
  • All intelligence lives in Employee Agents.

Hierarchy:
  CEO -> Executive Agent (plan) -> **Department Agent** -> EmployeeAgent

Departments:
  1. IT (Information Technology)
  2. HR (Human Resources)
  3. Finance
  4. Sales & Marketing
  5. Customer Service
  6. Operations
"""
import json
import logging
import asyncio
import time
from typing import Optional

from agents.base import BaseAgent
from core.models import AgentResult, AgentType
from core.communication import message_bus, AgentMessage, MessageType as CommType, MessagePriority

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Department Registry — Static config for all 6 departments
# ═══════════════════════════════════════════════════════════════════════

DEPARTMENT_REGISTRY: dict[str, dict] = {
    # ─── 1. IT ──────────────────────────────────────────────────
    "IT": {
        "head_name":    "Thor",
        "head_title":   "VP of Engineering",
        "head_handle":  "@dept_it",
        "agent_type":   AgentType.INFORMATION_TECHNOLOGY,
        "icon":         "💻",
        "color":        "#38bdf8",
        "employees":    ["frontend_dev", "backend_dev", "qa_tester", "sec_engineer", "cloud_arch", "mobile_dev"],
        "default_employee": "backend_dev",
        "specialties": {
            "frontend_dev": [
                "frontend", "ui", "ux", "react", "css", "html", "javascript", "interface",
                "component", "styling", "layout", "vibe", "aesthetic",
            ],
            "backend_dev": [
                "backend", "api", "server", "database", "sql", "infrastructure",
                "logic", "script", "python", "service", "endpoint", "architecture",
            ],
            "qa_tester": [
                "test", "qa", "bug", "issue", "automation", "quality", "unit test",
            ],
            "sec_engineer": [
                "security", "audit", "vulnerability", "auth", "encryption", "owasp",
            ],
            "cloud_arch": [
                "cloud", "aws", "azure", "infrastructure", "devops", "scalable", "serverless",
            ],
            "mobile_dev": [
                "mobile", "ios", "android", "flutter", "react native", "app",
            ],
        },
        "system_prompt_extra": (
            "You own all technical execution.\n"
            "Route frontend tasks to @frontend_dev and backend/logic to @backend_dev."
        ),
    },

    # ─── 2. Human Resources ────────────────────────────────────
    "HR": {
        "head_name":    "Loki",
        "head_title":   "VP of People & Culture",
        "head_handle":  "@dept_hr",
        "agent_type":   AgentType.HUMAN_RESOURCES,
        "icon":         "🧑‍💼",
        "color":        "#a78bfa",
        "employees":    ["recruiter", "policy_expert", "comp_expert"],
        "default_employee": "recruiter",
        "specialties": {
            "recruiter": [
                "hire", "recruit", "resume", "interview", "talent",
            ],
            "policy_expert": [
                "policy", "handbook", "compliance", "regulation", "employee rights",
            ],
            "comp_expert": [
                "compensation", "benefit", "payroll", "equity", "bonus",
            ],
        },
        "system_prompt_extra": (
            "You own all people-related decisions.\n"
            "Route hiring to @recruiter and policy/compliance to @policy_expert."
        ),
    },

    # ─── 3. Finance ────────────────────────────────────────────
    "Finance": {
        "head_name":    "Captain america",
        "head_title":   "VP of Finance",
        "head_handle":  "@dept_finance",
        "agent_type":   AgentType.FINANCE,
        "icon":         "💰",
        "color":        "#10b981",
        "employees":    ["fin_analyst", "auditor", "tax_pro"],
        "default_employee": "fin_analyst",
        "specialties": {
            "fin_analyst": [
                "budget", "revenue", "profit", "cost", "expense", "forecast",
            ],
            "auditor": [
                "audit", "compliance", "tax", "accounting", "invoice",
            ],
            "tax_pro": [
                "tax", "irs", "audit", "vat", "gst", "filing",
            ],
        },
        "system_prompt_extra": (
            "You own all financial operations.\n"
            "Route analysis to @fin_analyst and auditing/compliance to @auditor."
        ),
    },

    # ─── 4. Sales & Marketing ──────────────────────────────────
    "Marketing": {
        "head_name":    "Peter",
        "head_title":   "VP of Marketing",
        "head_handle":  "@dept_marketing",
        "agent_type":   AgentType.SALES_MARKETING,
        "icon":         "📣",
        "color":        "#f59e0b",
        "employees":    ["content_creator", "seo_specialist", "social_manager", "pr_lead", "growth_hacker"],
        "default_employee": "content_creator",
        "specialties": {
            "content_creator": [
                "blog", "content", "copywriting", "write", "creative",
            ],
            "seo_specialist": [
                "seo", "growth", "keyword", "analytics", "ranking",
            ],
            "social_manager": [
                "social", "twitter", "linkedin", "instagram", "community",
            ],
            "pr_lead": [
                "pr", "press", "brand", "reputation", "publicity", "media",
            ],
            "growth_hacker": [
                "growth", "viral", "acquisition", "funnel", "optimization",
            ],
        },
        "system_prompt_extra": (
            "You own all marketing and sales.\n"
            "Route content to @content_creator and growth/SEO to @seo_specialist."
        ),
    },

    # ─── 5. Customer Service ───────────────────────────────────
    "Customer Service": {
        "head_name":    "Stephen",
        "head_title":   "VP of Customer Experience",
        "head_handle":  "@dept_cs",
        "agent_type":   AgentType.CUSTOMER_SERVICE,
        "icon":         "🎧",
        "color":        "#22d3ee",
        "employees":    ["support_agent", "escalation_agent", "trainer"],
        "default_employee": "support_agent",
        "specialties": {
            "support_agent": [
                "support", "ticket", "complaint", "feedback", "customer",
                "satisfaction", "nps", "churn", "onboarding", "escalation",
                "help desk", "sla", "user issue", "faq",
            ],
            "escalation_agent": [
                "escalate", "critical", "angry", "refund", "breach",
            ],
            "trainer": [
                "train", "onboarding", "tutorial", "educate", "masterclass",
            ],
        },
        "system_prompt_extra": (
            "You own all customer-facing operations: support, satisfaction, escalation, and feedback.\n"
            "Route tasks to @support_agent for initial handling."
        ),
    },

    # ─── 6. Operations ─────────────────────────────────────────
    "Operations": {
        "head_name":    "Wanda",
        "head_title":   "VP of Operations",
        "head_handle":  "@dept_ops",
        "agent_type":   AgentType.OPERATIONS,
        "icon":         "⚙️",
        "color":        "#6e56ff",
        "employees":    ["prism", "trend", "chrono", "drive", "sc_manager"],
        "default_employee": "chrono",
        "specialties": {
            "prism": [
                "data", "analyze", "analysis", "statistics", "metric",
            ],
            "trend": [
                "research", "market", "competitor", "trend",
            ],
            "chrono": [
                "project", "timeline", "milestone", "schedule", "sprint",
            ],
            "drive": [
                "process", "workflow", "optimize", "logistics", "sop",
            ],
            "sc_manager": [
                "supply chain", "vendor", "procurement", "logistics", "shipping",
            ],
        },
        "system_prompt_extra": (
            "You own all operational execution: planning, research, logistics, and process optimization.\n"
            "Route research tasks to @market_researcher and ops tasks to @project_manager or @logistics_coord."
        ),
    },
}

# Aliases: the Executive Agent may output "Sales & Marketing" or "Research"
DEPARTMENT_ALIASES: dict[str, str] = {
    "IT":                "IT",
    "Information Technology": "IT",
    "information_technology": "IT",
    "Engineering":       "IT",
    "HR":                "HR",
    "Human Resources":   "HR",
    "human_resources":   "HR",
    "Finance":           "Finance",
    "finance":           "Finance",
    "Marketing":         "Marketing",
    "Sales & Marketing": "Marketing",
    "Sales and Marketing": "Marketing",
    "sales_marketing":   "Marketing",
    "Customer Service":  "Customer Service",
    "customer_service":  "Customer Service",
    "Operations":        "Operations",
    "operations":        "Operations",
    "Research":          "Operations",    # Research rolls into Operations dept
    "research":          "Operations",
}


def resolve_department(label: str) -> str:
    """Normalize any department label to a canonical registry key."""
    canonical = DEPARTMENT_ALIASES.get(label)
    if canonical:
        return canonical
    # Fuzzy fallback
    label_lower = label.lower()
    for alias, canon in DEPARTMENT_ALIASES.items():
        if alias.lower() in label_lower or label_lower in alias.lower():
            return canon
    return "Operations"  # safe default


class DepartmentAgent(BaseAgent):
    """
    A deterministic router that passes a task to a specific employee.
    NO LLM CALLS.
    """

    def __init__(self, department_key: str):
        super().__init__()
        self.dept_key = resolve_department(department_key)
        self.profile = DEPARTMENT_REGISTRY.get(self.dept_key, DEPARTMENT_REGISTRY["Operations"])
        self.agent_type = self.profile["agent_type"]
        self.system_prompt = ""

    async def execute(self, context: dict) -> AgentResult:
        """Routes task to employee. No LLM reasoning here."""
        task_desc = context.get("task", "")
        task_id = context.get("task_id", "task_unknown")
        emp_handle = context.get("employee_handle", self.profile["default_employee"])
        dept_name = self.dept_key

        logger.info(f"[{self.profile['head_handle']}] Routing to {emp_handle}")

        # ── Route to Specialist ──
        from agents.employee_agents import SpecializedEmployee
        # Strip @ if handle was passed
        emp_id = emp_handle.lstrip("@")

        employee = SpecializedEmployee(emp_id)
        emp_context = {
            "task": task_desc,
            "task_id": task_id,
            "upstream_data": context.get("upstream_data"),
            "next_employee_name": context.get("next_employee_name"),
            "complexity": context.get("complexity", "medium"),
        }

        logger.info(f"[{dept_name}] Calling employee {emp_handle}...")
        try:
            emp_result = await asyncio.wait_for(
                employee.execute(emp_context),
                timeout=180.0  # 3 min — free models can be slow; LLM client needs room to retry+fallback
            )
        except asyncio.TimeoutError:
            logger.error(f"Employee {emp_handle} timed out after 180s")
            return AgentResult(
                agent=self.agent_type,
                success=False,
                output=f"Employee {emp_handle} timed out",
                error="timeout",
                tokens_used=0,
                cost_usd=0.0,
                model_used="none"
            )
        except Exception as e:
            logger.error(f"Employee {emp_handle} crashed: {e}", exc_info=True)
            return AgentResult(
                agent=self.agent_type,
                success=False,
                output=f"Employee {emp_handle} failed: {str(e)}",
                error=str(e),
                tokens_used=0,
                cost_usd=0.0,
                model_used="none"
            )
        logger.info(f"[{dept_name}] Employee {emp_handle} completed.")

        return emp_result

# All routing logic is now handled in Orchestrator and ExecutiveAgent.
