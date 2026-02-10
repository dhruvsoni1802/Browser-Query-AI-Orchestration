from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from typing import List

class SessionStatus(str, Enum):
    active = "active"
    idle = "idle"
    closed = "closed"

# Request schema from frontend to orchestration service
class QueryRequest(BaseModel):
    query: str = Field(..., description="The natural language query from the user")
    agent_id: str = Field(..., description="The ID of the AI agent handling this query")
    session_name: Optional[str] = Field(default=None, description="Optional session name for that AI Agent")

# Internal schemas from orchestration service to infrastructure layer
# These schemas mirror the Go backend service's responses
class SessionInfo(BaseModel):
    session_id: str
    session_name: str
    agent_id: str
    context_id: str
    created_at: str

class SessionDetail(SessionInfo):
    page_ids: Optional[List[str]] = None
    page_count: int = 0
    last_activity: str
    status: SessionStatus

class SessionSummary(BaseModel):
    session_id: str
    session_name: str
    agent_id: Optional[str] = None
    context_id: Optional[str] = None
    page_count: int = 0
    created_at: str
    last_activity: str
    status: SessionStatus

class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
    count: int

class AgentSessionSummary(BaseModel):
    session_id: str
    session_name: str
    status: SessionStatus
    page_count: int = 0
    created_at: str
    last_activity: str

class AgentSessionListResponse(BaseModel):
    agent_id: str
    sessions: List[AgentSessionSummary]
    count: int

class NavigateResponse(BaseModel):
    session_id: str
    page_id: str
    url: str

class ExecuteJsResponse(BaseModel):
    session_id: str
    page_id: str
    result: Optional[str] = None

class ScreenshotResponse(BaseModel):
    session_id: str
    page_id: str
    screenshot: str  # base64 encoded
    format: str
    size: int

class PageContentResponse(BaseModel):
    session_id: str
    page_id: str
    content: str
    length: int

class CloseSessionResponse(BaseModel):
    message: str
    session_id: str
    session_name: str
    status: SessionStatus

class ResumeSessionResponse(BaseModel):
    session_id: str
    session_name: str
    resumed: bool
    created_at: str

# Response schema from orchestration service to frontend
class WorkflowStep(BaseModel):
    step_number: int
    action: str = Field(..., description="What the agent did, e.g. 'navigate', 'extract', 'reason'")
    detail: str = Field(..., description="Human-readable description of this step")
    success: bool = True

class QueryResponse(BaseModel):
    query: str = Field(..., description="The original query echoed back")
    agent_id: str
    session_id: Optional[str] = None
    answer: str = Field(..., description="The agent's synthesized response to the query")
    steps: List[WorkflowStep] = Field(default_factory=list, description="The workflow steps the agent took")
    success: bool = True
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orchestrator"
    version: str
    infrastructure_reachable: bool

# Streaming Event Schemas

class StreamEventType(str, Enum):
    step_start = "step_start"
    step_complete = "step_complete"
    step_error = "step_error"
    thinking = "thinking"
    answer_complete = "answer_complete"
    answer_chunk = "answer_chunk"
    done = "done"
    error = "error"

class StreamEvent(BaseModel):
    event: StreamEventType
    data: dict