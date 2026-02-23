"""Base Agent for document processing pipeline."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging
from dataclasses import dataclass, field
from enum import Enum
import json


class AgentRole(Enum):
    """Agent role types."""
    ORCHESTRATOR = "orchestrator"
    LOADER = "loader"
    PROCESSOR = "processor"
    TRANSFORMER = "transformer"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    STORAGE = "storage"
    MCP_BRIDGE = "mcp_bridge"


class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    WAITING = "waiting"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    sender: str
    recipient: str
    action: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None
    correlation_id: Optional[str] = None


@dataclass
class AgentCapability:
    """Defines what an agent can do."""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all processing agents."""
    
    def __init__(
        self,
        name: str,
        role: AgentRole,
        capabilities: Optional[List[AgentCapability]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize base agent.
        
        Args:
            name: Agent identifier
            role: Agent's primary role
            capabilities: List of agent capabilities
            config: Agent configuration
        """
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"agent.{name}")
        self.message_queue: List[AgentMessage] = []
        self.context: Dict[str, Any] = {}
        
    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process incoming message.
        
        Args:
            message: Incoming agent message
            
        Returns:
            Response message
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize agent resources.
        
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Clean up agent resources.
        
        Returns:
            Success status
        """
        pass
    
    def can_handle(self, message: AgentMessage) -> bool:
        """Check if agent can handle the message.
        
        Args:
            message: Message to check
            
        Returns:
            True if agent can handle the message
        """
        for capability in self.capabilities:
            if capability.name == message.action:
                return True
        return False
    
    def add_capability(self, capability: AgentCapability):
        """Add a capability to the agent.
        
        Args:
            capability: Capability to add
        """
        self.capabilities.append(capability)
        
    def update_status(self, status: AgentStatus):
        """Update agent status.
        
        Args:
            status: New status
        """
        self.logger.info(f"Status change: {self.status} -> {status}")
        self.status = status
        
    def enqueue_message(self, message: AgentMessage):
        """Add message to processing queue.
        
        Args:
            message: Message to enqueue
        """
        self.message_queue.append(message)
        
    def create_response(
        self,
        recipient: str,
        action: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """Create response message.
        
        Args:
            recipient: Target agent
            action: Action to perform
            payload: Message payload
            correlation_id: Optional correlation ID
            
        Returns:
            Agent message
        """
        import time
        return AgentMessage(
            sender=self.name,
            recipient=recipient,
            action=action,
            payload=payload,
            timestamp=time.time(),
            correlation_id=correlation_id
        )
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get agent status report.
        
        Returns:
            Status information
        """
        return {
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "capabilities": [cap.name for cap in self.capabilities],
            "queue_size": len(self.message_queue),
            "context": self.context
        }