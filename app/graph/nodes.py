# graph/nodes.py

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
from app.services.browser_client import BrowserClient
from app.graph.state import AgentState
import logging
import json

logger = logging.getLogger(__name__)


class GraphNodes:
    """
    Node functions for the custom agent graph.

    Each method is a graph node that receives AgentState
    and returns a partial state update.

    We use a class so all nodes share the same BrowserClient
    and LLM instances — same closure pattern as the tools,
    but for graph nodes.
    """

    def __init__(self, client: BrowserClient, llm, tools: list):
        self.client = client
        self.llm = llm.bind_tools(tools)
        self.tools_by_name = {t.name: t for t in tools}

    async def initialize(self, state: AgentState) -> dict:
        """
        First node in the graph. Creates a session and sets up context.

        This runs ONCE at the start — the agent never needs to
        worry about session creation.
        """
        try:
            session = await self.client.create_session(
                agent_id=state["agent_id"],
            )

            # Build the system message with session context
            system_content = f"""You are a browser automation agent. You help users find information on the web.

                                  SESSION CONTEXT:
                                  - session_id: {session.session_id}
                                  - agent_id: {state["agent_id"]}

                                  You MUST use session_id "{session.session_id}" for all tool calls.

                                  AVAILABLE TOOLS:
                                  - navigate: Open a URL (returns a page_id)
                                  - analyze_page: Get page structure (CSS classes, IDs, headings, interactive elements)
                                  - get_accessibility_tree: Get semantic page structure (roles, names, hierarchy)
                                  - get_page_content: Get raw HTML (use sparingly — prefer analyze_page + execute_js)
                                  - execute_js: Run JavaScript on the page
                                  - search_text: Search visible page text for a keyword (use for quick matching)
                                  - capture_screenshot: Take a screenshot
                                  - close_page: Close a page

                                  WORKFLOW:
                                  1. Navigate to the relevant URL
                                  2. ALWAYS call analyze_page after navigating — this shows you what's actually on the page
                                  3. Use the analysis to write informed JavaScript selectors (never guess selectors)
                                  4. If analyze_page isn't enough, use get_accessibility_tree for semantic structure
                                  5. Extract the specific information needed
                                  6. Provide a clear, concise answer

                                  CRITICAL RULES:
                                  - NEVER guess CSS selectors. Always analyze the page first.
                                  - If execute_js fails, check the analysis and try different selectors.
                                  - For keyword matching, prefer search_text before writing custom selectors.
                                  - Keep your responses focused on answering the user's question.
                                  - Do not describe what you're doing step by step in your final answer — just give the information."""

            return {
                "session_id": session.session_id,
                "messages": [SystemMessage(content=system_content)],
                "iteration_count": 0,
            }

        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            return {
                "error": f"Failed to create browser session: {str(e)}",
            }

    async def agent(self, state: AgentState) -> dict:
        """
        The reasoning node. Calls the LLM with the current message
        history and gets back either a tool call or a final response.
        """
        messages = state["messages"]
        response = await self.llm.ainvoke(messages)

        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1,
        }

    async def tools(self, state: AgentState) -> dict:
        """
        Execute tool calls from the last AIMessage.

        Runs each tool and returns the results as ToolMessages.
        """
        last_message = state["messages"][-1]
        tool_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name in self.tools_by_name:
                tool_fn = self.tools_by_name[tool_name]
                result = await tool_fn.ainvoke(tool_args)
            else:
                result = f"Error: Unknown tool '{tool_name}'"

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                )
            )

        # Track current page_id from navigate results
        updates: dict = {"messages": tool_messages}

        for msg in tool_messages:
            if msg.name == "navigate" and "page_id:" in msg.content:
                try:
                    page_id = msg.content.split("page_id:")[1].split(",")[0].strip()
                    updates["current_page_id"] = page_id
                except (IndexError, ValueError):
                    pass

        return updates

    async def post_process(self, state: AgentState) -> dict:
        """
        Runs after every tool execution. Checks what happened
        and takes automatic action.

        Currently no automatic actions are performed here.
        """
        return {}

    async def cleanup(self, state: AgentState) -> dict:
        """
        Final node. Deletes the session regardless of how we got here.

        This is a STRUCTURAL guarantee — it's a graph node,
        not an LLM decision. The session always gets cleaned up.
        """
        session_id = state.get("session_id")

        if session_id:
            try:
                await self.client.delete_session(session_id)
                logger.info(f"Session {session_id} cleaned up successfully")
            except Exception as e:
                # Log but don't fail — cleanup errors shouldn't block the response
                logger.error(f"Failed to cleanup session {session_id}: {e}")

        return {}
