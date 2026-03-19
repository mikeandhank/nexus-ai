"""
A-01: Structured Log Schema
Canonical JSON schema for all events
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum


class EventType(str, Enum):
    # Authentication
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    
    # Transactions
    CREDIT_PURCHASE = "credit.purchase"
    CREDIT_CONSUMPTION = "credit.consumption"
    CREDIT_REFUND = "credit.refund"
    CREDIT_EXPIRY = "credit.expiry"
    
    # API
    API_REQUEST = "api.request"
    API_RESPONSE = "api.response"
    API_ERROR = "api.error"
    
    # Admin
    ADMIN_ACCESS = "admin.access"
    CONFIG_CHANGE = "config.change"
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    
    # System
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    ADMIN = "admin"


class ResourceType(str, Enum):
    USER = "user"
    TRANSACTION = "transaction"
    CREDIT = "credit"
    AGENT = "agent"
    API_KEY = "api_key"
    CONFIG = "config"


class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"


class Outcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class StructuredLog(BaseModel):
    """Canonical JSON log schema - A-01"""
    
    # Required fields
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: EventType
    actor_id: str
    actor_type: ActorType
    resource_type: ResourceType
    resource_id: Optional[str] = None
    action: Action
    outcome: Outcome
    
    # Optional fields
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> "StructuredLog":
        """Create from dictionary"""
        return cls(**data)


def create_log(
    event_type: EventType,
    actor_id: str,
    actor_type: ActorType,
    resource_type: ResourceType,
    action: Action,
    outcome: Outcome,
    resource_id: str = None,
    ip_address: str = None,
    session_id: str = None,
    metadata: dict = None
) -> StructuredLog:
    """Helper to create a structured log entry"""
    return StructuredLog(
        event_type=event_type,
        actor_id=actor_id,
        actor_type=actor_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        outcome=outcome,
        ip_address=ip_address,
        session_id=session_id,
        metadata=metadata or {}
    )


# Example usage
if __name__ == "__main__":
    # Example: User purchased credits
    log = create_log(
        event_type=EventType.CREDIT_PURCHASE,
        actor_id="user_123",
        actor_type=ActorType.USER,
        resource_type=ResourceType.CREDIT,
        action=Action.CREATE,
        outcome=Outcome.SUCCESS,
        resource_id="txn_456",
        ip_address="192.168.1.1",
        session_id="sess_789",
        metadata={"amount_cents": 5000, "credits": 1000}
    )
    print(log.to_json())
