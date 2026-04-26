from pydantic import BaseModel, Field
from typing import Optional, Union, List, Any, Dict
from datetime import datetime, timezone
import uuid
from enum import Enum

class MessageType(str, Enum):
    DELEGATION = "delegation"
    TASK_CARD = "task_card"
    RESULT = "result"
    BLOCKER = "blocker"
    QUESTION = "question"
    UPDATE = "update"

class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    STANDARD = "STANDARD"
    LOW = "LOW"

def get_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class Message(BaseModel):
    """Standardized JSON envelope for all agent-to-agent messages."""
    from_handle: str = Field(alias="from")
    to: Union[str, List[str]]
    task_id: str
    type: MessageType
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=get_iso_now)
    priority: Priority = Priority.STANDARD
    reply_to: Optional[str] = None
    
    class Config:
        populate_by_name = True
        
    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True)
