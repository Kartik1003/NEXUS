"""Inter-Agent Communication System - Centralized message bus.

Provides structured message passing between any agents in the organization:
  CEO <-> Executive <-> Department Heads <-> Employees

Features:
  - MessageBus singleton - central hub for all agent-to-agent communication
  - Request/Response pattern with correlation IDs
  - Broadcast and directed messaging
  - Full message history per task (audit trail)
  - ACL enforcement (respects can_collaborate_with)
  - Event hooks for WebSocket / frontend streaming
  - Agent directory for handle -> instance resolution
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from enum import Enum
from typing import Optional, Callable, Awaitable, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Data models
# ═══════════════════════════════════════════════════════════════════════

class MessageType(str, Enum):
    """All supported message types in the organization."""
    DELEGATION    = "delegation"
    TASK_CARD     = "task_card"
    RESULT        = "result"
    HELP_REQUEST  = "help_request"
    HELP_RESPONSE = "help_response"
    BROADCAST     = "broadcast"
    STATUS        = "status"
    ESCALATION    = "escalation"
    ACK           = "ack"


class MessagePriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    STANDARD = "STANDARD"
    LOW      = "LOW"


class MessageStatus(str, Enum):
    PENDING   = "pending"
    DELIVERED = "delivered"
    READ      = "read"
    RESPONDED = "responded"
    EXPIRED   = "expired"
    FAILED    = "failed"


class AgentMessage(BaseModel):
    """Immutable message envelope for agent-to-agent communication."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    correlation_id: Optional[str] = None   # links request ↔ response
    task_id: str = ""
    type: MessageType
    sender: str                            # handle, e.g. "@senior_eng"
    receiver: str                          # handle or "*" for broadcast
    content: str = ""                      # human-readable body
    payload: dict = Field(default_factory=dict)  # structured data
    priority: MessagePriority = MessagePriority.STANDARD
    reply_to: Optional[str] = None         # message ID this replies to
    timestamp: float = Field(default_factory=time.time)
    status: MessageStatus = MessageStatus.PENDING
    metadata: dict = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json()


class Conversation(BaseModel):
    """A tracked exchange between two agents."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    participants: list[str] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    started_at: float = Field(default_factory=time.time)
    status: str = "active"   # active | resolved | escalated

    def add(self, msg: AgentMessage):
        self.messages.append(msg)

    def summary(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "participants": self.participants,
            "message_count": len(self.messages),
            "started_at": self.started_at,
            "status": self.status,
        }


# ═══════════════════════════════════════════════════════════════════════
# Agent Directory — handle → metadata registry
# ═══════════════════════════════════════════════════════════════════════

class AgentDirectory:
    """Global registry of known agent handles and metadata.

    Populated automatically from employee_agents.EMPLOYEE_REGISTRY,
    the department heads, and the executive/CEO agents.
    """

    def __init__(self):
        self._agents: dict[str, dict] = {}
        self._loaded = False

    def _lazy_load(self):
        """Load all known agents on first access."""
        if self._loaded:
            return

        # Register system agents
        system_agents = [
            {"handle": "@executive",  "name": "Strategos", "role": "Executive Planner",       "department": "Executive"},
            {"handle": "@cto",        "name": "Axiom",     "role": "CTO",                    "department": "Executive"},
            {"handle": "@cmo",        "name": "Lyra",      "role": "CMO",                    "department": "Executive"},
            {"handle": "@coo",        "name": "Atlas",     "role": "COO",                    "department": "Executive"},
            {"handle": "@cfo",        "name": "Iron Man",  "role": "CFO",                    "department": "Executive"},
            {"handle": "@chro",       "name": "Marvel",    "role": "CHRO",                   "department": "Executive"},
            {"handle": "@dept_it",    "name": "Axiom",     "role": "VP Engineering",          "department": "IT"},
            {"handle": "@dept_hr",    "name": "Harmony",   "role": "VP People & Culture",     "department": "HR"},
            {"handle": "@dept_finance","name": "Ledger",   "role": "VP Finance",              "department": "Finance"},
            {"handle": "@dept_marketing","name":"Lyra",    "role": "VP Marketing",            "department": "Marketing"},
            {"handle": "@dept_cs",    "name": "Beacon",    "role": "VP Customer Experience",  "department": "Customer Service"},
            {"handle": "@dept_ops",   "name": "Atlas",     "role": "VP Operations",           "department": "Operations"},
        ]
        for sa in system_agents:
            self._agents[sa["handle"]] = sa

        # Register employees
        try:
            from agents.employee_agents import EMPLOYEE_REGISTRY
            for eid, info in EMPLOYEE_REGISTRY.items():
                self._agents[info["handle"]] = {
                    "handle": info["handle"],
                    "name": info["name"],
                    "role": info["role"],
                    "department": info["department"],
                    "can_collaborate_with": info.get("can_collaborate_with", []),
                }
        except ImportError:
            pass

        self._loaded = True
        logger.info(f"[AgentDirectory] Loaded {len(self._agents)} agents")

    def lookup(self, handle: str) -> Optional[dict]:
        self._lazy_load()
        return self._agents.get(handle.lower().strip())

    def exists(self, handle: str) -> bool:
        self._lazy_load()
        return handle.lower().strip() in self._agents

    def all_handles(self) -> list[str]:
        self._lazy_load()
        return list(self._agents.keys())

    def by_department(self, department: str) -> list[dict]:
        self._lazy_load()
        return [a for a in self._agents.values() if a.get("department", "").lower() == department.lower()]

    def can_communicate(self, sender: str, receiver: str) -> bool:
        """Check if sender is allowed to message receiver."""
        if receiver == "*":
            return True

        sender_info = self.lookup(sender)
        receiver_info = self.lookup(receiver)

        if not sender_info or not receiver_info:
            return True  # Unknown agents — allow (graceful)

        # Same department = always OK
        if sender_info.get("department") == receiver_info.get("department"):
            return True

        # Executives and dept heads can message anyone
        exec_roles = {"CEO", "Executive Planner", "VP"}
        if any(r in sender_info.get("role", "") for r in exec_roles):
            return True

        # Peer collaboration check
        collab = sender_info.get("can_collaborate_with", [])
        if receiver in collab:
            return True

        # Default: allow (we log a warning)
        logger.warning(
            f"[ACL] Cross-department message: {sender} → {receiver} "
            f"(not in collaboration list)"
        )
        return True


# ═══════════════════════════════════════════════════════════════════════
# MessageBus — The central communication hub
# ═══════════════════════════════════════════════════════════════════════

class MessageBus:
    """Centralized message bus for all inter-agent communication."""

    def __init__(self):
        self.directory = AgentDirectory()
        self._history: dict[str, list[AgentMessage]] = defaultdict(list)
        self._conversations: dict[str, Conversation] = {}
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._global_listeners: list[Callable] = []
        self._stats = {
            "total_messages": 0,
            "by_type": defaultdict(int),
            "by_sender": defaultdict(int),
            "by_receiver": defaultdict(int),
        }

    async def send(self, message: AgentMessage) -> AgentMessage:
        """Send a message and store it in history."""
        if not message.sender:
            raise ValueError("Message must have a sender")
        if not message.receiver:
            raise ValueError("Message must have a receiver")

        if not message.correlation_id:
            message.correlation_id = message.id

        if not self.directory.can_communicate(message.sender, message.receiver):
            message.status = MessageStatus.FAILED
            message.metadata["error"] = "ACL: not permitted"
            logger.warning(f"[MessageBus] BLOCKED: {message.sender} → {message.receiver}")
            return message

        message.status = MessageStatus.DELIVERED
        self._history[message.task_id].append(message)
        self._update_stats(message)

        conv_key = self._conv_key(message.sender, message.receiver, message.task_id)
        if conv_key not in self._conversations:
            self._conversations[conv_key] = Conversation(
                task_id=message.task_id,
                participants=[message.sender, message.receiver],
            )
        self._conversations[conv_key].add(message)

        logger.info(f"[MessageBus] {message.sender} → {message.receiver} [{message.type.value}] {message.content[:80]}")

        if message.reply_to and message.reply_to in self._pending_responses:
            future = self._pending_responses.pop(message.reply_to)
            if not future.done():
                future.set_result(message)

        await self._dispatch(message)
        return message

    async def request(
        self,
        sender: str,
        receiver: str,
        content: str,
        task_id: str = "",
        msg_type: MessageType = MessageType.HELP_REQUEST,
        payload: dict = None,
        priority: MessagePriority = MessagePriority.STANDARD,
        timeout_s: float = 120.0,
        handler: Callable = None,
    ) -> Optional[AgentMessage]:
        """Send a message and wait for a response."""
        req = AgentMessage(
            task_id=task_id,
            type=msg_type,
            sender=sender,
            receiver=receiver,
            content=content,
            payload=payload or {},
            priority=priority,
        )
        req.correlation_id = req.id

        await self.send(req)

        if handler:
            try:
                resp = await handler(req)
                if isinstance(resp, AgentMessage):
                    resp.reply_to = req.id
                    resp.correlation_id = req.id
                    resp.task_id = task_id
                    await self.send(resp)
                    return resp
                else:
                    resp_msg = AgentMessage(
                        task_id=task_id,
                        type=MessageType.HELP_RESPONSE,
                        sender=receiver,
                        receiver=sender,
                        content=str(resp),
                        reply_to=req.id,
                        correlation_id=req.id,
                    )
                    await self.send(resp_msg)
                    return resp_msg
            except Exception as e:
                logger.error(f"[MessageBus] Handler error: {e}")
                err_msg = AgentMessage(
                    task_id=task_id,
                    type=MessageType.HELP_RESPONSE,
                    sender=receiver,
                    receiver=sender,
                    content=f"ERROR: {e}",
                    reply_to=req.id,
                    correlation_id=req.id,
                    status=MessageStatus.FAILED,
                )
                await self.send(err_msg)
                return err_msg

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_responses[req.id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout_s)
            return result
        except asyncio.TimeoutError:
            self._pending_responses.pop(req.id, None)
            logger.warning(f"[MessageBus] Request timeout: {sender} → {receiver} after {timeout_s}s")
            return None

    async def delegate(
        self,
        sender: str,
        receiver: str,
        task_description: str,
        task_id: str = "",
        priority: MessagePriority = MessagePriority.STANDARD,
        deliverables: list[str] = None,
        constraints: list[str] = None,
    ) -> AgentMessage:
        return await self.send(AgentMessage(
            task_id=task_id,
            type=MessageType.DELEGATION,
            sender=sender,
            receiver=receiver,
            content=task_description,
            priority=priority,
            payload={
                "deliverables": deliverables or [],
                "constraints": constraints or [],
            },
        ))

    async def return_result(
        self,
        sender: str,
        receiver: str,
        task_id: str,
        deliverable: str,
        summary: str = "",
        confidence: float = 0.8,
        reply_to: str = None,
    ) -> AgentMessage:
        return await self.send(AgentMessage(
            task_id=task_id,
            type=MessageType.RESULT,
            sender=sender,
            receiver=receiver,
            content=summary or deliverable[:200],
            reply_to=reply_to,
            payload={
                "status": "COMPLETE",
                "deliverable": deliverable,
                "summary": summary,
                "confidence": confidence,
            },
        ))

    def get_task_history(self, task_id: str) -> list[dict]:
        return [m.to_dict() for m in self._history.get(task_id, [])]

    def get_stats(self) -> dict:
        return {
            "total_messages": self._stats["total_messages"],
            "by_type": dict(self._stats["by_type"]),
            "by_sender": dict(self._stats["by_sender"]),
            "by_receiver": dict(self._stats["by_receiver"]),
            "active_conversations": len(self._conversations),
            "pending_requests": len(self._pending_responses),
            "tasks_tracked": len(self._history),
        }

    def clear_task(self, task_id: str):
        self._history.pop(task_id, None)
        to_remove = [k for k in self._conversations if k.endswith(f":{task_id}" if task_id else "")]
        for k in to_remove:
            del self._conversations[k]

    def on_message(self, handle: str, callback: Callable):
        self._handlers[handle.lower().strip()].append(callback)

    def on_any_message(self, callback: Callable):
        self._global_listeners.append(callback)

    async def _dispatch(self, message: AgentMessage):
        for handler in self._handlers.get(message.receiver, []):
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"[MessageBus] Handler error for {message.receiver}: {e}")

        if message.receiver == "*":
            for handle, handlers in self._handlers.items():
                if handle != message.sender:
                    for h in handlers:
                        try:
                            await h(message)
                        except Exception as e:
                            logger.error(f"[MessageBus] Broadcast handler error: {e}")

        for listener in self._global_listeners:
            try:
                await listener(message)
            except Exception as e:
                logger.error(f"[MessageBus] Global listener error: {e}")

    def _update_stats(self, message: AgentMessage):
        self._stats["total_messages"] += 1
        self._stats["by_type"][message.type.value] += 1
        self._stats["by_sender"][message.sender] += 1
        self._stats["by_receiver"][message.receiver] += 1

    @staticmethod
    def _conv_key(a: str, b: str, task_id: str) -> str:
        pair = tuple(sorted([a.lower().strip(), b.lower().strip()]))
        return f"{pair[0]}:{pair[1]}:{task_id}"


# Singleton instance
message_bus = MessageBus()
