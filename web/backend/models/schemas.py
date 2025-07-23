#!/usr/bin/env python3
"""
Pydantic models for Beehive Web Dashboard API
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Agent types in the hive"""

    QUEEN = "queen"
    DEVELOPER = "developer"
    QA = "qa"
    ANALYST = "analyst"


class AgentStatus(str, Enum):
    """Agent status states"""

    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    OFFLINE = "offline"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Task status states"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Agent Models
class AgentStatusResponse(BaseModel):
    """Agent status information"""

    name: AgentType
    status: AgentStatus
    current_task_id: str | None = None
    current_task_title: str | None = None
    last_activity: datetime
    last_heartbeat: datetime
    workload_score: float = Field(ge=0.0, le=100.0)
    performance_score: float = Field(ge=0.0, le=100.0)
    capabilities: list[str] = []
    metadata: dict[str, Any] = {}


class AgentListResponse(BaseModel):
    """List of all agents"""

    agents: list[AgentStatusResponse]
    total_count: int
    active_count: int
    timestamp: datetime


# Task Models
class TaskResponse(BaseModel):
    """Task information"""

    task_id: str
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None
    created_by: str = "human"
    metadata: dict[str, Any] = {}


class TaskListResponse(BaseModel):
    """List of tasks with pagination"""

    tasks: list[TaskResponse]
    total_count: int
    page: int = 1
    per_page: int = 50
    timestamp: datetime


class TaskCreateRequest(BaseModel):
    """Request to create a new task"""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    priority: Priority = Priority.MEDIUM
    assigned_to: AgentType | None = None
    estimated_hours: float | None = Field(ge=0.0, le=1000.0)


# Instruction Models
class InstructionRequest(BaseModel):
    """Request to send instruction to agents"""

    content: str = Field(min_length=1, max_length=2000)
    target_agent: AgentType | str = Field(description="Target agent or 'all'")
    priority: Priority = Priority.MEDIUM
    create_task: bool = True
    subject: str | None = Field(max_length=200)


class InstructionResponse(BaseModel):
    """Response after sending instruction"""

    instruction_id: int
    content: str
    target_agent: str
    priority: Priority
    created_at: datetime
    task_created: bool = False
    task_id: str | None = None


# Communication Models
class MessageResponse(BaseModel):
    """Bee message information"""

    message_id: int
    from_bee: str
    to_bee: str
    message_type: str
    subject: str | None = None
    content: str
    task_id: str | None = None
    priority: Priority
    processed: bool
    processed_at: datetime | None = None
    created_at: datetime
    sender_cli_used: bool
    conversation_id: str | None = None


class MessageListResponse(BaseModel):
    """List of messages"""

    messages: list[MessageResponse]
    total_count: int
    page: int = 1
    per_page: int = 50
    timestamp: datetime


# System Status Models
class SystemHealthResponse(BaseModel):
    """Overall system health status"""

    status: str = Field(description="overall|degraded|error")
    tmux_session_active: bool
    database_connection: bool
    agents_responsive: dict[str, bool]
    active_tasks_count: int
    pending_messages_count: int
    uptime_seconds: float
    timestamp: datetime


class ConversationStatsResponse(BaseModel):
    """Conversation statistics"""

    total_messages: int
    beekeeper_instructions: int
    bee_conversations: int
    sender_cli_usage_rate: float
    active_conversations: int
    timestamp: datetime


# WebSocket Models
class WebSocketMessage(BaseModel):
    """WebSocket message format"""

    type: str = Field(description="agent_status|task_update|message|system_health")
    data: dict[str, Any]
    timestamp: datetime


class WebSocketResponse(BaseModel):
    """WebSocket response wrapper"""

    success: bool
    message: str
    data: dict[str, Any] | None = None


# Dashboard Summary Models
class DashboardSummary(BaseModel):
    """Complete dashboard summary"""

    agents: list[AgentStatusResponse]
    recent_tasks: list[TaskResponse]
    recent_messages: list[MessageResponse]
    system_health: SystemHealthResponse
    conversation_stats: ConversationStatsResponse
    timestamp: datetime


# Error Models
class ErrorResponse(BaseModel):
    """API Error response"""

    error: str
    detail: str
    timestamp: datetime


class ValidationError(BaseModel):
    """Validation error details"""

    field: str
    message: str
    value: Any
