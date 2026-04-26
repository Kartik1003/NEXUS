"""Specialized Employee Agents — Domain-expert individual contributors.

ONLY Employee agents are allowed to use LLM.
They receive a task, use their expertise, and return a structured JSON result.
NO collaboration or sub-tasking logic inside employees.
"""
import json
import logging
import time
from typing import Optional

from agents.base import BaseAgent
from core.models import AgentResult, AgentType

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Employee Registry — Every named employee in the organization
# ═══════════════════════════════════════════════════════════════════════

EMPLOYEE_REGISTRY: dict[str, dict] = {
    # IT Department
    "frontend_dev": {
        "name": "Volt", "role": "Senior Frontend Developer", "handle": "@frontend_dev",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "frontend",
        "expertise_prompt": "You are a senior frontend developer specializing in React, UI/UX, and CSS aesthetics."
    },
    "backend_dev": {
        "name": "Byte", "role": "Senior Backend Developer", "handle": "@backend_dev",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "backend",
        "expertise_prompt": "You are a senior backend developer specializing in APIs, databases, and system logic."
    },
    "qa_tester": {
        "name": "Scope", "role": "QA Automation Engineer", "handle": "@qa_tester",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "qa",
        "expertise_prompt": "You specialize in QA automation, testing strategies, and bug identification."
    },
    "sec_engineer": {
        "name": "Shield", "role": "Security Engineer", "handle": "@sec_engineer",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "security",
        "expertise_prompt": "You are a specialized security engineer focused on penetration testing, vulnerability assessment, and zero-trust architecture."
    },
    # Marketing
    "content_creator": {
        "name": "Quill", "role": "Senior Content Creator", "handle": "@content_creator",
        "team": "Marketing", "department": "Marketing", "agent_type": AgentType.SALES_MARKETING,
        "specialty": "content",
        "expertise_prompt": "You are a senior content creator specializing in copywriting and brand messaging."
    },
    "seo_specialist": {
        "name": "Flux", "role": "SEO & Growth Specialist", "handle": "@seo_specialist",
        "team": "Marketing", "department": "Marketing", "agent_type": AgentType.SALES_MARKETING,
        "specialty": "seo",
        "expertise_prompt": "You specialize in SEO, growth hacking, and ranking strategies."
    },
    "social_manager": {
        "name": "Wave", "role": "Social Media Manager", "handle": "@social_manager",
        "team": "Marketing", "department": "Marketing", "agent_type": AgentType.SALES_MARKETING,
        "specialty": "social",
        "expertise_prompt": "You specialize in social media engagement and community management."
    },
    # Finance
    "fin_analyst": {
        "name": "Mint", "role": "Financial Analyst", "handle": "@fin_analyst",
        "team": "Finance", "department": "Finance", "agent_type": AgentType.FINANCE,
        "specialty": "budget",
        "expertise_prompt": "You specialize in financial analysis, budgeting, and ROI modeling."
    },
    "auditor": {
        "name": "Vault", "role": "Financial Auditor", "handle": "@fin_auditor",
        "team": "Finance", "department": "Finance", "agent_type": AgentType.FINANCE,
        "specialty": "audit",
        "expertise_prompt": "You specialize in financial auditing and regulatory compliance."
    },
    # HR
    "recruiter": {
        "name": "Talent", "role": "Recruitment Specialist", "handle": "@recruiter",
        "team": "Human Resources", "department": "HR", "agent_type": AgentType.HUMAN_RESOURCES,
        "specialty": "recruit",
        "expertise_prompt": "You specialize in talent acquisition and recruitment strategy."
    },
    "policy_expert": {
        "name": "Compliance", "role": "HR Policy Specialist", "handle": "@hr_policy",
        "team": "Human Resources", "department": "HR", "agent_type": AgentType.HUMAN_RESOURCES,
        "specialty": "policy",
        "expertise_prompt": "You specialize in HR policy, compliance, and workplace culture."
    },
    # Customer Service
    "support_agent": {
        "name": "Echo", "role": "Senior Support Specialist", "handle": "@support_agent",
        "team": "Customer Success", "department": "Customer Service", "agent_type": AgentType.CUSTOMER_SERVICE,
        "specialty": "support",
        "expertise_prompt": "You are a senior support specialist focused on user satisfaction and quick resolution of technical issues."
    },
    "escalation_agent": {
        "name": "Siren", "role": "Escalation Manager", "handle": "@escalation_agent",
        "team": "Customer Success", "department": "Customer Service", "agent_type": AgentType.CUSTOMER_SERVICE,
        "specialty": "escalation",
        "expertise_prompt": "You specialize in handling difficult customer cases, crisis management, and ensuring SLA compliance for critical tickets."
    },
    # Operations
    "chrono": {
        "name": "Chrono", "role": "Project Manager", "handle": "@project_manager",
        "team": "Operations", "department": "Operations", "agent_type": AgentType.OPERATIONS,
        "specialty": "project",
        "expertise_prompt": "You specialize in project management, timelines, and milestones."
    },
    "prism": {
        "name": "Prism", "role": "Data Analyst", "handle": "@data_analyst",
        "team": "Operations", "department": "Operations", "agent_type": AgentType.OPERATIONS,
        "specialty": "data",
        "expertise_prompt": "You specialize in data analysis and business intelligence."
    },
    "trend": {
        "name": "Oracle", "role": "Market Research Analyst", "handle": "@market_researcher",
        "team": "Operations", "department": "Operations", "agent_type": AgentType.OPERATIONS,
        "specialty": "research",
        "expertise_prompt": "You specialize in market research, competitor analysis, and identifying industry trends."
    },
    "drive": {
        "name": "Impact", "role": "Process Optimizer", "handle": "@process_optimizer",
        "team": "Operations", "department": "Operations", "agent_type": AgentType.OPERATIONS,
        "specialty": "process",
        "expertise_prompt": "You specialize in business process optimization, workflow design, and operational efficiency."
    },
    "cloud_arch": {
        "name": "Nimbus", "role": "Cloud Solutions Architect", "handle": "@cloud_arch",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "cloud",
        "expertise_prompt": "You specialize in cloud infrastructure, AWS/Azure architecture, and scalable systems."
    },
    "mobile_dev": {
        "name": "Swift", "role": "Mobile App Developer", "handle": "@mobile_dev",
        "team": "Engineering", "department": "IT", "agent_type": AgentType.INFORMATION_TECHNOLOGY,
        "specialty": "mobile",
        "expertise_prompt": "You specialize in iOS and Android development using React Native and Flutter."
    },
    "comp_expert": {
        "name": "Equity", "role": "Compensation & Benefits Lead", "handle": "@hr_comp",
        "team": "Human Resources", "department": "HR", "agent_type": AgentType.HUMAN_RESOURCES,
        "specialty": "compensation",
        "expertise_prompt": "You specialize in compensation structures, employee benefits, and payroll strategy."
    },
    "tax_pro": {
        "name": "Ledger", "role": "Corporate Tax Specialist", "handle": "@tax_specialist",
        "team": "Finance", "department": "Finance", "agent_type": AgentType.FINANCE,
        "specialty": "tax",
        "expertise_prompt": "You specialize in corporate tax compliance, strategy, and international accounting."
    },
    "pr_lead": {
        "name": "Vocal", "role": "PR & Communications Manager", "handle": "@pr_lead",
        "team": "Marketing", "department": "Marketing", "agent_type": AgentType.SALES_MARKETING,
        "specialty": "pr",
        "expertise_prompt": "You specialize in public relations, brand reputation, and corporate communications."
    },
    "growth_hacker": {
        "name": "Viral", "role": "Growth Marketing Lead", "handle": "@growth_marketer",
        "team": "Marketing", "department": "Marketing", "agent_type": AgentType.SALES_MARKETING,
        "specialty": "growth",
        "expertise_prompt": "You specialize in growth hacking, viral loops, and customer acquisition funnels."
    },
    "trainer": {
        "name": "Mentor", "role": "Customer Training Specialist", "handle": "@cs_trainer",
        "team": "Customer Success", "department": "Customer Service", "agent_type": AgentType.CUSTOMER_SERVICE,
        "specialty": "training",
        "expertise_prompt": "You specialize in customer onboarding, product training, and educational content."
    },
    "sc_manager": {
        "name": "Link", "role": "Supply Chain Manager", "handle": "@sc_manager",
        "team": "Operations", "department": "Operations", "agent_type": AgentType.OPERATIONS,
        "specialty": "supply_chain",
        "expertise_prompt": "You specialize in supply chain logistics, vendor management, and procurement efficiency."
    }
}

def get_employee_by_handle(handle: str) -> Optional[dict]:
    handle = handle.lower().strip()
    for emp in EMPLOYEE_REGISTRY.values():
        if emp["handle"].lower() == handle:
            return emp
    return None

# ═══════════════════════════════════════════════════════════════════════
# SpecializedEmployee — Solo LLM Worker
# ═══════════════════════════════════════════════════════════════════════

class SpecializedEmployee(BaseAgent):
    """
    An individual contributor that executes a task using their domain expertise.
    Calls LLM exactly once.
    """

    def __init__(self, employee_id: str):
        super().__init__()
        emp_id = employee_id.lower().strip().lstrip("@")

        if emp_id in EMPLOYEE_REGISTRY:
            self.profile = EMPLOYEE_REGISTRY[emp_id]
        else:
            found = get_employee_by_handle(f"@{emp_id}")
            if found:
                self.profile = found
            else:
                # Fallback to key lookup if handle doesn't work
                for k, v in EMPLOYEE_REGISTRY.items():
                    if k.lower() == emp_id:
                        self.profile = v
                        break
                else:
                    raise ValueError(f"Unknown employee: {employee_id}")

        self.agent_type = self.profile["agent_type"]
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        dept = self.profile["department"]

        # Department-specific output instruction
        if dept == "IT":
            output_instruction = (
                "You MUST write complete, working, runnable code. "
                "No placeholders. No truncation. No '...'. No examples. "
                "Write every file in full as if deploying to production today."
            )
        elif dept == "Marketing":
            output_instruction = (
                "You MUST write the complete final copy, campaign, or content. "
                "No drafts. No outlines. Final versions ready to publish."
            )
        elif dept == "Finance":
            output_instruction = (
                "You MUST produce a complete analysis with real numbers, "
                "formulas, projections, and conclusions. No summaries only."
            )
        elif dept == "HR":
            output_instruction = (
                "You MUST write the complete policy, job description, or plan. "
                "Final version, not a template."
            )
        else:
            output_instruction = (
                "You MUST produce a complete, detailed, final deliverable. "
                "Not an outline. Not a summary. The actual finished work product."
            )

        return f"""You are {self.profile['name']}, a {self.profile['role']}.
Department: {self.profile['department']}
Handle: {self.profile['handle']}

{self.profile['expertise_prompt']}

{output_instruction}

RETURN FORMAT — you MUST return ONLY this exact JSON structure, nothing else:
{{
  "deliverable": "Your complete prose, analysis, plan, or explanation here. For non-code tasks this is the main output.",
  "files_produced": [
    {{ "filename": "relative/path/filename.ext", "content": "COMPLETE FILE CONTENT — every line, no truncation" }}
  ],
  "message_to_next": "Direct first-person message to the next colleague. Be specific: what you built, what they need to do, any important details they must know. Write null if you are the last in chain.",
  "summary": "One sentence summary of what you completed.",
  "confidence": 0.85
}}

RULES:
- files_produced must contain at least one file for every task.
- For code tasks: each file is a separate entry with its full content.
- For non-code tasks: produce one .md file containing your complete deliverable.
- When writing the message_to_next, you must ONLY use the exact name of the next colleague provided to you if employees communicate. Do NOT invent or assume human names.
- Never truncate file content. If it is long, include all of it.
"""

    async def execute(self, context: dict) -> AgentResult:
        from core.model_selector import select_model, get_manual_override
        from core.execution_tracker import execution_tracker

        task_desc = context.get("task", "")
        task_id   = context.get("task_id", "task_worker")
        upstream  = context.get("upstream_data")
        next_employee = context.get("next_employee_name")  # NEW: passed by orchestrator

        complexity = context.get("complexity", "medium")
        specialty  = self.profile.get("specialty", self.profile["department"].lower())
        model = (
            get_manual_override(self.profile["handle"])
            or context.get("model")
            or select_model(specialty, complexity)
        )

        execution_tracker.log_step(
            task_id, "Employee", self.profile["handle"], "started",
            f"{self.profile['name']} is working on: {task_desc[:80]}...",
            model=model
        )

        # Build user prompt
        upstream_section = ""
        if upstream:
            upstream_section = f"""
CONTEXT FROM PREVIOUS COLLEAGUE:
{upstream}

Use this as your starting point. Build on it, don't repeat it.
"""

        next_section = ""
        if next_employee:
            next_section = f"\nThe next colleague who will receive your work is: {next_employee}. Address your message_to_next to them specifically."

        user_prompt = f"""Your task: {task_desc}
{upstream_section}{next_section}

Remember: return ONLY the JSON structure defined in your system prompt.
Every file must be complete. No truncation."""

        # Single LLM call
        llm_res = await self.call_llm(
            user_prompt, task_id=task_id, model=model, json_mode=True
        )

        # Parse the structured answer
        raw_answer = llm_res.get("answer", {})
        if isinstance(raw_answer, str):
            try:
                import json as _json
                raw_answer = _json.loads(raw_answer)
            except Exception:
                raw_answer = {"deliverable": raw_answer, "files_produced": [], "message_to_next": None, "summary": raw_answer[:100]}

        # Extract fields
        deliverable    = raw_answer.get("deliverable", "") if isinstance(raw_answer, dict) else str(raw_answer)
        files_produced = raw_answer.get("files_produced", []) if isinstance(raw_answer, dict) else []
        message_to_next = raw_answer.get("message_to_next") if isinstance(raw_answer, dict) else None
        summary        = raw_answer.get("summary", deliverable[:100]) if isinstance(raw_answer, dict) else deliverable[:100]

        # Guarantee at least one file
        if not files_produced:
            dept = self.profile["department"].lower()
            ext = "md"
            filename = f"{self.profile['name'].lower()}_output.{ext}"
            files_produced = [{"filename": filename, "content": deliverable}]

        # Normalize files_produced: ensure every entry is a dict with 'filename' and 'content'
        normalized_files = []
        for f in files_produced:
            if isinstance(f, dict):
                normalized_files.append(f)
            elif isinstance(f, str):
                normalized_files.append({"filename": f, "content": ""})
            # else skip invalid entries
        files_produced = normalized_files

        execution_tracker.log_step(
            task_id, "Employee", self.profile["handle"], "completed",
            summary, model=model
        )

        # Broadcast employee output event for frontend
        from core.websocket_handler import ws_manager
        import asyncio
        asyncio.create_task(ws_manager.broadcast_log(task_id, {
            "event": "employee_output",
            "employee_name": self.profile["name"],
            "handle": self.profile["handle"],
            "department": self.profile["department"],
            "task_completed": summary,
            "deliverable_preview": deliverable[:300],
            "files_produced": [
                {"filename": f.get("filename", "unknown"), "size": len(f.get("content", ""))}
                for f in files_produced
            ],
            "message_to_next": message_to_next,
            "task_id": task_id,
        }))

        # If there is a message_to_next, broadcast it as an agent_chat event
        if message_to_next:
            asyncio.create_task(ws_manager.broadcast_log(task_id, {
                "event": "agent_chat",
                "from_handle": self.profile["handle"],
                "from_name": self.profile["name"],
                "to_name": next_employee or "next colleague",
                "message": message_to_next,
                "task_id": task_id,
            }))

        import json as _json
        return AgentResult(
            agent=self.agent_type,
            success=True,
            output=_json.dumps({
                "deliverable": deliverable,
                "summary": summary,
                "files_produced": files_produced,
                "message_to_next": message_to_next,
            }),
            model_used=llm_res.get("model", model),
            tokens_used=llm_res.get("tokens_used", 0),
            cost_usd=llm_res.get("cost_usd", 0.0),
            files_produced=files_produced,
            message_to_next=message_to_next,
        )


# ═══════════════════════════════════════════════════════════════════════
# Employee Factory — Used by DepartmentAgent to instantiate the right agent
# ═══════════════════════════════════════════════════════════════════════

def create_employee(handle: str) -> SpecializedEmployee:
    """Factory function: create a SpecializedEmployee from a handle."""
    return SpecializedEmployee(handle)
