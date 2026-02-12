from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


#The state that flows through the agent graph.Every node receives this state and returns updates to it.
class AgentState(TypedDict):

    # This annotation tells LangGraph to append new messages rather than replace the list.
    messages: Annotated[list, add_messages]

    # Session tracking. This is set up by the intial node of the custom graph
    session_id: Optional[str]
    agent_id: str
    query: str

    # Page tracking. This is updated by the post-process node of the custom graph
    current_page_id: Optional[str]
    page_analysis: Optional[str]

    # Control flow. The max iterations stops the agent from looping endlessly.
    #If the agent makes too many tool calls without reaching a conclusion, we force it to stop.
    iteration_count: int
    max_iterations: int
    error: Optional[str]