# graph/workflow.py

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from app.graph.state import AgentState
from app.graph.nodes import GraphNodes
from app.tools.browser_tools import create_browser_tools
from app.services.browser_client import BrowserClient
from app.config import settings


SYSTEM_PROMPT = """You are a browser automation agent."""  # Moved to initialize node


def _build_llm():
    if settings.llm_provider == "ollama":
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )
    elif settings.llm_provider == "openai":
        openai_kwargs: dict = {"model": settings.llm_model, "temperature": 0}
        if settings.llm_api_key:
            openai_kwargs["api_key"] = settings.llm_api_key
        return ChatOpenAI(**openai_kwargs)
    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        anthropic_kwargs: dict = {
            "model_name": settings.llm_model, "temperature": 0,
            "timeout": None, "stop": None,
        }
        if settings.llm_api_key:
            anthropic_kwargs["api_key"] = settings.llm_api_key
        return ChatAnthropic(**anthropic_kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def should_continue(state: AgentState) -> str:
    """
    Conditional edge after the agent node.

    Decides whether to:
    - Call tools (agent wants to use a tool)
    - Go to cleanup (agent is done or we hit max iterations)
    """
    # Check for initialization errors
    if state.get("error"):
        return "cleanup"

    # Check iteration limit
    if state["iteration_count"] >= state["max_iterations"]:
        return "cleanup"

    # Check the last message
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # No tool calls = agent is done
    return "cleanup"


def build_agent(client: BrowserClient):
    """Build and compile the custom agent graph."""

    llm = _build_llm()
    tools = create_browser_tools(client)
    nodes = GraphNodes(client=client, llm=llm, tools=tools)

    # Build the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("initialize", nodes.initialize)
    graph.add_node("agent", nodes.agent)
    graph.add_node("tools", nodes.tools)
    graph.add_node("post_process", nodes.post_process)
    graph.add_node("cleanup", nodes.cleanup)

    # Set entry point
    graph.set_entry_point("initialize")

    # Add edges
    graph.add_edge("initialize", "agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "cleanup": "cleanup",
    })
    graph.add_edge("tools", "post_process")
    graph.add_edge("post_process", "agent")
    graph.add_edge("cleanup", END)

    return graph.compile()