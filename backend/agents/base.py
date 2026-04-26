"""Base agent class — all agents inherit from this."""
from abc import ABC, abstractmethod
from core.models import AgentResult, AgentType
from core.llm import llm_client
from config import AGENT_MODEL_MAP


class BaseAgent(ABC):
    """Abstract base for all agents."""

    agent_type: AgentType
    system_prompt: str = ""

    def __init_subclass__(cls, **kwargs):
        """Automatically instrument the execute() method on all subclasses to track telemetry."""
        super().__init_subclass__(**kwargs)
        if 'execute' in cls.__dict__:
            original_execute = cls.execute
            from core.logger import track_agent_execution
            # Wrap the subclass's execute method natively
            cls.execute = track_agent_execution(original_execute)

    def get_tier(self) -> str:
        return AGENT_MODEL_MAP.get(self.agent_type.value, "cheap")

    async def call_llm(
        self,
        user_prompt: str,
        task_id: str = "",
        tier: str | None = None,
        model: str | None = None,
        json_mode: bool = True,
    ) -> dict:
        """Call LLM with this agent's system prompt."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if model:
            # If explicit model provided, bypass multi-tier selection
            response = await llm_client.call(
                messages=messages,
                model=model,
                agent=self.agent_type,
                task_id=task_id,
                json_mode=json_mode,
            )
            responses = [response] if response else []
        else:
            responses = await llm_client.multi_call(
                messages=messages,
                tier=tier or self.get_tier(),
                agent=self.agent_type,
                task_id=task_id,
                json_mode=json_mode,
            )

        if not responses:
            raise ValueError(f"Agent {self.agent_type.value} failed to get any LLM responses.")

        return responses[0]

    # ─── Memory Integration ──────────────────────────────────────────

    def set_short_term_memory(self, task_id: str, key: str, value: any):
        """Store information for the duration of the current task."""
        from agents.memory import MemoryAgent
        # MemoryAgent manages its own state via singleton pattern in orchestrator,
        # but instantiating it gives access to the same SQLite DB. Short-term memory
        # needs a shared instance if multiple agents access it. 
        # Using a global or retrieving the orchestrated one.
        from core.orchestrator import memory_agent
        memory_agent.set_short_term(task_id, key, value)

    def get_short_term_memory(self, task_id: str, key: str, default: any = None) -> any:
        """Retrieve information stored for the current task."""
        from core.orchestrator import memory_agent
        return memory_agent.get_short_term(task_id, key, default)
        
    def recall_long_term_memory(self, query: str, limit: int = 3) -> list[dict]:
        """Search across all past tasks' descriptions and outputs for semantic matches."""
        from core.orchestrator import memory_agent
        return memory_agent.retrieve_previous_results(query, limit)

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """Execute the agent's task. Must be implemented by subclasses."""
        ...
