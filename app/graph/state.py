from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from app.models.schemas import WorkflowStep

#The state that flows through the agent graph.Every node receives this state and returns updates to it.
class AgentState(TypedDict):

    # This annotation tells LangGraph to append new messages rather than replace the list.
    messages: Annotated[list, add_messages]

    # Tracking data accumulated during the workflow
    session_id: Optional[str]
    page_id: Optional[str]
    agent_id: str
    query: str

    # Workflow tracking for the frontend
    steps: list[WorkflowStep]