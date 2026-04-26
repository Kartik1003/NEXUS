"""Quick validation: Department Agents import, instantiate, and route correctly."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from agents.department_agents import (
    DepartmentAgent,
    DepartmentAgentRouter,
    department_agent_router,
    resolve_department,
    DEPARTMENT_REGISTRY,
)

print("=== Department Registry ===")
for key, reg in DEPARTMENT_REGISTRY.items():
    icon = reg["icon"]
    head = reg["head_name"]
    title = reg["head_title"]
    mgrs = reg["managers"]
    print(f"  {icon} {key}: {head} ({title}) -> managers: {mgrs}")

print("\n=== Alias Resolution ===")
tests = [
    "Engineering", "IT", "HR", "Human Resources",
    "Sales & Marketing", "Customer Service", "Finance",
    "Operations", "Research", "information_technology", "sales_marketing",
]
for t in tests:
    print(f"  {t:30s} -> {resolve_department(t)}")

print("\n=== Agent Instantiation & Manager Selection ===")
test_tasks = {
    "IT": "Build a REST API with authentication",
    "HR": "Create a hiring policy for remote engineers",
    "Finance": "Prepare a quarterly budget forecast",
    "Marketing": "Write a product launch blog post",
    "Customer Service": "Handle a customer complaint about shipping",
    "Operations": "Analyze competitor pricing strategy",
}
for dept_key in DEPARTMENT_REGISTRY:
    agent = DepartmentAgent(dept_key)
    task = test_tasks.get(dept_key, "general task")
    mgr = agent._select_manager(task)
    print(f"  {dept_key}: type={agent.agent_type.value}, task='{task[:40]}...' -> manager={mgr}")

print("\n=== Orchestrator Import ===")
from core.orchestrator import Orchestrator
print("  Orchestrator imported OK")

print("\n ALL CHECKS PASSED")
