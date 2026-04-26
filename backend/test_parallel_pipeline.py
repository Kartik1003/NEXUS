"""
Unit test runner — simulates the new parallel orchestrator pipeline.

Run from the backend/ directory:
    python test_parallel_pipeline.py

Checks:
1. DepartmentDetector correctly identifies multiple departments
2. PromptTemplates renders correctly per department
3. Comparator correctly ranks outputs
4. Full orchestrator.solve() produces a result with teammate_runs,
   comparison_scores, and aggregation keys
"""

import asyncio
import sys
import os

# Ensure backend/  is on the path
sys.path.insert(0, os.path.dirname(__file__))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def test_department_detector():
    print("\n─── 1. DepartmentDetector ───────────────────────────────")
    from core.department_detector import department_detector

    task = "Build a login system with JWT auth and write the API specs"
    result = department_detector.detect(task)
    print(f"   Task: {task!r}")
    print(f"   Detected: {result}")

    assert len(result) >= 1, "No departments detected!"
    dept_names = [d for d, _ in result]
    assert "information_technology" in dept_names, \
        f"Expected IT dept for coding task, got: {dept_names}"
    print(f"   {PASS} IT department detected. Total: {len(result)} dept(s)")


def test_prompt_templates():
    print("\n─── 2. PromptTemplates ──────────────────────────────────")
    from agents.prompt_templates import get_prompt, list_departments

    depts = list_departments()
    print(f"   Templates defined for: {depts}")
    assert len(depts) >= 6, "Expected at least 6 department templates"

    task = "Create an authentication module"
    for dept in depts:
        prompt = get_prompt(dept, task)
        assert task in prompt, f"Task not injected into {dept} prompt!"
        assert len(prompt) > 100, f"Prompt for {dept} too short"
    print(f"   {PASS} All {len(depts)} department prompts render correctly")


def test_comparator():
    print("\n─── 3. Comparator ───────────────────────────────────────")
    from agents.comparator import Comparator
    from core.parallel_executor import TeammateResult

    comp = Comparator()
    task = "Write a login module with JWT authentication"

    # Create mock results
    good_result = TeammateResult(
        department="information_technology",
        model="qwen/qwen3-coder",
        role="Senior Software Engineer",
        answer=(
            "# JWT Authentication Module\n\n"
            "Here is a complete implementation:\n\n"
            "```python\nimport jwt\n\ndef create_token(user_id):\n    return jwt.encode({'user': user_id}, SECRET)\n```\n\n"
            "## Notes\n- Store secrets in env vars\n- Use HTTPS always\n- Rotate keys periodically"
        ),
        tokens_used=500,
        success=True,
    )

    weak_result = TeammateResult(
        department="customer_service",
        model="google/gemma-3-4b-it",
        role="Customer Experience Director",
        answer="I can't help with that.",
        tokens_used=20,
        success=True,
    )

    failed_result = TeammateResult(
        department="finance",
        model="nvidia/nemotron-nano-9b-v2",
        role="CFO",
        answer="",
        tokens_used=0,
        success=False,
        error="Timeout",
    )

    scored = comp.rank([good_result, weak_result, failed_result], task)

    assert len(scored) == 2, f"Expected 2 valid results (1 failed), got {len(scored)}"
    assert scored[0].result.department == "information_technology", \
        f"Expected IT to rank highest, got {scored[0].result.department}"
    assert scored[0].total > scored[1].total, "Higher score should be first"

    print(f"   {PASS} Ranked {len(scored)} results correctly")
    for s in scored:
        print(f"      {s.result.department}: {s.total:.3f} "
              f"(rel={s.relevance:.2f} comp={s.completeness:.2f} qual={s.quality:.2f})")


async def test_orchestrator_integration():
    print("\n─── 4. OrchestratorIntegration (live API call) ──────────")
    from core.orchestrator import Orchestrator

    orch = Orchestrator()
    task = "Build a login system with JWT auth and write the API documentation"

    print(f"   Task: {task!r}")
    print("   Running solve() — this makes real API calls, may take 30–60s…")

    result = await orch.solve(task)

    assert result.get("status") == "success", \
        f"Expected success, got: {result.get('status')} — {result.get('message')}"

    assert "departments" in result, "Missing 'departments' key in result"
    assert "teammate_runs" in result, "Missing 'teammate_runs' key"
    assert "comparison_scores" in result, "Missing 'comparison_scores' key"
    assert "aggregation" in result, "Missing 'aggregation' key"

    depts = result["departments"]
    runs  = result["teammate_runs"]
    scores = result["comparison_scores"]
    agg   = result["aggregation"]

    print(f"   {PASS} Departments detected: {depts}")
    print(f"   {PASS} Teammate runs: {len(runs)} (success={sum(1 for r in runs if r.get('success'))})")
    print(f"   {PASS} Comparison scores: {len(scores)}")
    print(f"   {PASS} Aggregation model: {agg.get('aggregator_model')}")
    print(f"   {PASS} Final output length: {len(result.get('final_output', ''))} chars")


def main():
    print("=======================================================")
    print("   AegisOps AI — Parallel Pipeline Unit Tests")
    print("=======================================================")

    errors = []

    # Non-async tests
    for test_fn in [test_department_detector, test_prompt_templates, test_comparator]:
        try:
            test_fn()
        except AssertionError as e:
            print(f"   {FAIL} ASSERTION FAILED: {e}")
            errors.append(str(e))
        except Exception as e:
            print(f"   {FAIL} UNEXPECTED ERROR: {e}")
            errors.append(str(e))

    # Integration test (live API)
    try:
        asyncio.run(test_orchestrator_integration())
    except AssertionError as e:
        print(f"   {FAIL} INTEGRATION ASSERTION: {e}")
        errors.append(str(e))
    except Exception as e:
        print(f"   {WARN} Integration test skipped/errored (likely no API key): {e}")

    print("\n=======================================================")
    if errors:
        print(f"   {FAIL} {len(errors)} test(s) failed:")
        for err in errors:
            print(f"      - {err}")
        sys.exit(1)
    else:
        print(f"   {PASS} All tests passed!")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
