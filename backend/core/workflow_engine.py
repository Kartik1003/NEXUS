"""Workflow Engine — Dynamic employee selection and task sequence management."""

from agents.employee_agents import EMPLOYEE_REGISTRY

def get_department_employees(department: str):
    """
    Returns a list of employee IDs (registry keys) for a given department.
    """
    return [
        emp_id for emp_id, data in EMPLOYEE_REGISTRY.items()
        if data.get("department") == department
    ]

def get_employee_by_specialty(specialty: str):
    """
    Returns the first employee matching a specific specialty.
    """
    for emp_id, data in EMPLOYEE_REGISTRY.items():
        if data.get("specialty") == specialty:
            return emp_id
    return None

def get_workflow(task: str, department: str):
    """
    Deterministic workflow selection based on task keywords and department.
    Returns a list of employee IDs in execution order.
    """
    task_lower = task.lower()

    _BUILD_KEYWORDS = [
        "website", "web app", "application", "app", "platform", "portal",
        "dashboard", "build", "develop", "create", "make", "full stack",
        "landing page", "responsive", "login", "complete", "feature"
    ]
    _is_build_task = any(kw in task_lower for kw in _BUILD_KEYWORDS)

    # --- IT Department ---
    if department == "IT":
        if _is_build_task:
            return ["frontend_dev", "backend_dev", "qa_tester"]
        if any(kw in task_lower for kw in ["frontend", "ui", "ux", "design", "css", "html", "react"]):
            return ["frontend_dev"]
        if any(kw in task_lower for kw in ["backend", "api", "database", "server", "endpoint", "script"]):
            return ["backend_dev"]
        if any(kw in task_lower for kw in ["test", "bug", "debugging", "quality", "qa"]):
            return ["qa_tester"]
        if any(kw in task_lower for kw in ["security", "auth", "vulnerability", "owasp"]):
            return ["sec_engineer"]
        if any(kw in task_lower for kw in ["cloud", "aws", "azure", "devops", "infra"]):
            return ["cloud_arch"]
        if any(kw in task_lower for kw in ["mobile", "ios", "android", "flutter"]):
            return ["mobile_dev"]
        # Default: full stack
        return ["frontend_dev", "backend_dev", "qa_tester"]

    # --- Marketing Department ---
    elif department == "Marketing":
        if any(kw in task_lower for kw in ["campaign", "launch", "promotion", "full"]):
            return ["content_creator", "seo_specialist", "social_manager"]
        if "content" in task_lower or "copy" in task_lower:
            return ["content_creator"]
        if "seo" in task_lower or "search" in task_lower:
            return ["seo_specialist"]
        if "social" in task_lower:
            return ["social_manager"]
        return ["content_creator"]

    # --- Finance Department ---
    elif department == "Finance":
        if any(kw in task_lower for kw in ["audit", "compliance", "tax"]):
            return ["auditor"]
        return ["fin_analyst"]

    # --- HR Department ---
    elif department == "HR":
        if any(kw in task_lower for kw in [
            "hire", "recruit", "talent", "interview", "job posting",
            "resume", "candidate", "onboard",
        ]):
            return ["recruiter"]
        if any(kw in task_lower for kw in [
            "policy", "policies", "compliance", "handbook", "toolkit", "toolkits",
            "procedure", "procedures", "disciplinary", "grievance", "sop",
            "standard operating procedure", "leave request", "formal process",
            "step-by-step", "managers to follow", "hr workflow", "people process",
            "performance review", "termination", "employee rights",
        ]):
            return ["policy_expert"]
        if any(kw in task_lower for kw in [
            "compensation", "benefit", "payroll", "equity", "bonus", "salary",
        ]):
            return ["comp_expert"]
        # Default: policy_expert (most HR tasks that aren't pure recruiting are policy-related)
        return ["policy_expert"]

    # --- Customer Service ---
    elif department == "Customer Service":
        if any(kw in task_lower for kw in ["escalat", "critical", "urgent", "sla"]):
            return ["escalation_agent"]
        return ["support_agent"]

    # --- Operations Department ---
    elif department == "Operations":
        if _is_build_task:
            # Planning first, then full IT implementation chain
            return ["chrono", "frontend_dev", "backend_dev", "qa_tester"]
        if any(kw in task_lower for kw in ["project", "plan", "roadmap", "timeline", "milestone"]):
            return ["chrono"]
        if any(kw in task_lower for kw in ["data", "analytics", "analysis", "report", "insight"]):
            return ["prism"]
        if any(kw in task_lower for kw in ["market", "research", "trend", "competitive"]):
            return ["trend"]
        return ["chrono"]

    # --- Fallback ---
    dept_emps = get_department_employees(department)
    return [dept_emps[0]] if dept_emps else ["backend_dev"]

def get_specialized_staff(department: str, specialty: str = None):
    """
    Advanced lookup: finds employees in a department, optionally filtering by specialty.
    """
    emps = [
        (emp_id, data) for emp_id, data in EMPLOYEE_REGISTRY.items()
        if data.get("department") == department
    ]
    
    if specialty:
        # Try specifically for that specialty
        for emp_id, data in emps:
            if data.get("specialty") == specialty:
                return [emp_id]
                
    return [emp_id for emp_id, data in emps]