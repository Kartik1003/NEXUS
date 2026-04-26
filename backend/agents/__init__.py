# Agents package — strict CEO → Executive → Department → Employee pipeline
from agents.ceo import CEOAgent
from agents.executive_agent import ExecutiveAgent
from agents.department_agents import DepartmentAgent, DEPARTMENT_REGISTRY, resolve_department
from agents.employee_agents import SpecializedEmployee, create_employee, EMPLOYEE_REGISTRY
from agents.memory import MemoryAgent
from agents.prompt_templates import get_prompt

__all__ = [
    "CEOAgent", 
    "ExecutiveAgent",
    "DepartmentAgent",
    "SpecializedEmployee", 
    "create_employee", 
    "EMPLOYEE_REGISTRY",
    "MemoryAgent",
    "get_prompt",
]
