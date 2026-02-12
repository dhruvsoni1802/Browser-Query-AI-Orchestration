from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, Any
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
    result: Optional[Any] = None

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
    cleanup = "cleanup"
    done = "done"
    error = "error"

class StreamEvent(BaseModel):
    event: StreamEventType
    data: dict

class PageAnalysisStructure(BaseModel):
    """The structural breakdown of a page."""
    classes: list[str] = []
    ids: list[str] = []
    headings: dict[str, list[str]] = {}
    interactive: dict[str, list[str]] = {}
    semantic_sections: list["SemanticSection"] = []
    data_attributes: list[str] = []
    text_snippets: list[str] = []

class SemanticSection(BaseModel):
    """A semantic section element description."""
    type: str
    class_name: list[str] = Field(default_factory=list, validation_alias="class")
    selectors: list[str] = []

    class Config:
        extra = "allow"

    @field_validator("class_name", mode="before")
    @classmethod
    def _coerce_class_name(cls, value):
        # Backend may return a single class string instead of list.
        if isinstance(value, str):
            return [value]
        return value

class PageAnalysisDetail(BaseModel):
    """Inner analysis object."""
    page_id: str
    url: str
    title: str
    structure: PageAnalysisStructure

class PageAnalysisResponse(BaseModel):
    """Response from POST /sessions/{id}/analyze."""
    session_id: str
    page_id: str
    analysis: PageAnalysisDetail

class AccessibilityNode(BaseModel):
    """A single node in the accessibility tree."""
    role: str
    name: str = ""
    focusable: bool = False
    children: list["AccessibilityNode"] = []

class AccessibilityTreeResponse(BaseModel):
    """Response from POST /sessions/{id}/accessibility-tree."""
    session_id: str
    page_id: str
    nodes: list[AccessibilityNode]
