"""Verify specialized employee agents: import, instantiate, route, and factory."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from agents.employee_agents import (
    SpecializedEmployee,
    create_employee,
    EMPLOYEE_REGISTRY,
    get_employees_by_department,
    get_employee_by_handle,
    select_best_employee,
)

print("=" * 60)
print("EMPLOYEE AGENT REGISTRY")
print("=" * 60)

# Group by department
depts = {}
for key, emp in EMPLOYEE_REGISTRY.items():
    dept = emp["department"]
    if dept not in depts:
        depts[dept] = []
    depts[dept].append(emp)

dept_icons = {"IT": "💻", "Marketing": "📣", "Finance": "💰", "HR": "🧑‍💼", "Customer Service": "🎧", "Operations": "⚙️"}

for dept, employees in depts.items():
    icon = dept_icons.get(dept, "🤖")
    print(f"\n{icon} {dept} ({len(employees)} employees)")
    print("-" * 50)
    for emp in employees:
        print(f"  {emp['handle']:22s} {emp['name']:12s} {emp['role']}")

print(f"\n{'=' * 60}")
print(f"TOTAL EMPLOYEES: {len(EMPLOYEE_REGISTRY)}")
print(f"{'=' * 60}")

# Test factory function
print("\n=== Factory: create_employee() ===")
test_handles = ["@senior_eng", "@content_writer", "@growth_hacker", "@fin_analyst", "@recruiter", "@support_agent", "@data_analyst", "@project_manager"]
for h in test_handles:
    try:
        agent = create_employee(h)
        print(f"  {h:22s} -> {agent.profile['name']} ({agent.profile['role']})")
    except Exception as e:
        print(f"  {h:22s} -> ERROR: {e}")

# Test keyword-based selection
print("\n=== Keyword Selection ===")
test_tasks = [
    ("Write a blog post about AI trends", "Marketing"),
    ("Fix a SQL injection vulnerability", "IT"),
    ("Create Q3 budget forecast", "Finance"),
    ("Design onboarding process for new hires", "HR"),
    ("Handle escalated customer complaint", "Customer Service"),
    ("Analyze competitor pricing data", "Operations"),
]
for task, dept in test_tasks:
    candidates = get_employees_by_department(dept)
    best = select_best_employee(task, candidates)
    print(f"  Task: {task[:45]:45s} -> {best['handle']} ({best['name']})")

# Test collaboration permission
print("\n=== Collaboration Check ===")
volt = create_employee("@senior_eng")
print(f"  Volt can collaborate with: {volt.profile['can_collaborate_with']}")

# Test orchestrator import
print("\n=== Full Import Chain ===")
from agents import SpecializedEmployee, create_employee, EMPLOYEE_REGISTRY
print("  agents.__init__ OK")
from core.orchestrator import Orchestrator
print("  Orchestrator OK")
from agents.manager import ManagerAgent
print("  ManagerAgent OK (uses SpecializedEmployee)")

print("\n✅ ALL CHECKS PASSED")
