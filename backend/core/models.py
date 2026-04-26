"""Pydantic data models for structured agent communication."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import time
import uuid


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentType(str, Enum):
    CEO = "CEO"
    EXECUTIVE = "Executive"
    DEPARTMENT = "Department"
    MANAGER = "Manager"
    EMPLOYEE = "Employee"
    MEMORY = "Memory"
    SYSTEM = "System"
    # Department Types
    INFORMATION_TECHNOLOGY = "Information Technology"
    HUMAN_RESOURCES = "Human Resources"
    FINANCE = "Finance"
    SALES_MARKETING = "Sales & Marketing"
    CUSTOMER_SERVICE = "Customer Service"
    OPERATIONS = "Operations"
    # Legacy / Utility types for tracking
    ROUTER = "Router"
    EVALUATOR = "Evaluator"
    RESEARCHER = "Researcher"


# ─── Agent Results ───────────────────────────────────────────────

class AgentResult(BaseModel):
    model_config = {'protected_namespaces': ()}

    agent: AgentType
    success: bool
    output: str
    code: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    model_used: str = ""
    files_produced: list[dict] = Field(default_factory=list)
    # Each dict: { "filename": "App.jsx", "content": "full file content" }
    message_to_next: Optional[str] = None
    # The direct message this employee writes to the next one


class CostRecord(BaseModel):
    task_id: str
    agent: AgentType
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: float = Field(default_factory=time.time)


# ─── WebSocket Events ───────────────────────────────────────────

class WSEvent(BaseModel):
    event: str  # "step_start", "step_done", "step_error", "task_complete", "metrics", "agent_message"
    data: dict = Field(default_factory=dict)


# ─── New Linear Pipeline Models ──────────────────────────────────

class ExecutionStep(BaseModel):
    agent_name: str
    role: str
    status: str  # "started", "in_progress", "completed", "failed"
    message: str
    timestamp: float = Field(default_factory=time.time)


class Reflection(BaseModel):
    """Kept for database compatibility in MemoryAgent, but unused in main pipeline."""
    task_id: str
    successes: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    key_learnings: list[str] = Field(default_factory=list)
    strategy_improvement: str = ""
    confidence_score: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    created_at: float = Field(default_factory=time.time)


class Learning(BaseModel):
    """Kept for database compatibility in MemoryAgent, but unused in main pipeline."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    category: str
    insight: str
    source_task_id: str
    relevance_score: float = 1.0
    times_applied: int = 0
    created_at: float = Field(default_factory=time.time)
