"""DAG execution engine — builds and executes dependency graphs."""
from __future__ import annotations
import asyncio
import logging
from typing import Callable, Awaitable
from collections import defaultdict
from core.models import Step, DAGPlan, StepStatus

logger = logging.getLogger(__name__)


class DAGExecutor:
    """Executes DAG steps in topological order, parallelizing independent steps."""

    def __init__(self, plan: DAGPlan):
        self.plan = plan
        self.steps = {s.id: s for s in plan.steps}
        self.results: dict[str, str] = {}

    def _topological_sort(self) -> list[list[str]]:
        """Return layers of step IDs that can run in parallel."""
        in_degree = {s.id: 0 for s in self.plan.steps}
        children = defaultdict(list)

        for step in self.plan.steps:
            for dep in step.depends_on:
                if dep in in_degree:
                    children[dep].append(step.id)
                    in_degree[step.id] += 1

        layers = []
        queue = [sid for sid, deg in in_degree.items() if deg == 0]

        while queue:
            layers.append(queue[:])
            next_queue = []
            for sid in queue:
                for child in children[sid]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue

        return layers

    async def execute(
        self,
        step_executor: Callable[[Step, dict], Awaitable[str]],
        on_step_start: Callable[[Step], Awaitable[None]] | None = None,
        on_step_done: Callable[[Step], Awaitable[None]] | None = None,
        on_step_error: Callable[[Step], Awaitable[None]] | None = None,
    ) -> DAGPlan:
        """Execute all steps respecting dependencies."""
        layers = self._topological_sort()

        for layer in layers:
            tasks = []
            for step_id in layer:
                step = self.steps[step_id]
                # Check if all dependencies succeeded
                deps_ok = all(
                    self.steps[d].status == StepStatus.DONE
                    for d in step.depends_on
                    if d in self.steps
                )
                if not deps_ok:
                    step.status = StepStatus.SKIPPED
                    step.error = "Dependency failed"
                    if on_step_error:
                        await on_step_error(step)
                    continue

                tasks.append(self._run_step(
                    step, step_executor, on_step_start, on_step_done, on_step_error
                ))

            if tasks:
                await asyncio.gather(*tasks)

        # Update plan totals
        self.plan.total_tokens = sum(s.tokens_used for s in self.plan.steps)
        self.plan.total_cost = sum(s.cost_usd for s in self.plan.steps)
        return self.plan

    async def _run_step(
        self,
        step: Step,
        step_executor: Callable[[Step, dict], Awaitable[str]],
        on_step_start,
        on_step_done,
        on_step_error,
    ):
        """Execute a single step."""
        step.status = StepStatus.RUNNING
        if on_step_start:
            await on_step_start(step)

        try:
            # Gather dependency results
            dep_context = {
                d: self.results.get(d, "")
                for d in step.depends_on
                if d in self.steps
            }
            result = await step_executor(step, dep_context)
            step.result = result
            step.status = StepStatus.DONE
            self.results[step.id] = result
            if on_step_done:
                await on_step_done(step)
        except Exception as e:
            step.status = StepStatus.ERROR
            step.error = str(e)
            logger.error(f"Step {step.name} failed: {e}")
            if on_step_error:
                await on_step_error(step)
