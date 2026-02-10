from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


#The state that flows through the agent graph.Every node receives this state and returns updates to it.
class AgentState(TypedDict):

    # This annotation tells LangGraph to append new messages rather than replace the list.
    messages: Annotated[list, add_messages]
