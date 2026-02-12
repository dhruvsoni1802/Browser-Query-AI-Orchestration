from app.graph.workflow import build_agent
from app.graph.state import AgentState
from app.services.browser_client import BrowserClient
from app.models.schemas import QueryResponse, WorkflowStep
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.models.schemas import StreamEvent, StreamEventType
import logging
import json
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class AgentService:

    def __init__(self, client: BrowserClient):
        self.agent = build_agent(client)

    async def execute_query(self, query: str, agent_id: str, session_name: str | None = None) -> QueryResponse:
        inputs: AgentState = {
            "messages": [HumanMessage(content=query)],
            "agent_id": agent_id,
            "query": query,
            "session_id": None,
            "current_page_id": None,
            "page_analysis": None,
            "iteration_count": 0,
            "max_iterations": 15,
            "error": None,
        }

        try:
            result = await self.agent.ainvoke(inputs)
            messages = result["messages"]

            steps = self._extract_steps(messages)
            answer = self._extract_answer(messages)
            session_id = result.get("session_id")

            return QueryResponse(
                query=query,
                agent_id=agent_id,
                session_id=session_id,
                answer=answer,
                steps=steps,
                success=True,
            )

        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            return QueryResponse(
                query=query,
                agent_id=agent_id,
                answer=f"I encountered an error while processing your request: {str(e)}",
                steps=[],
                success=False,
                error=str(e),
            )

    async def stream_query(self, query: str, agent_id: str, session_name: str | None = None) -> AsyncGenerator[str, None]:
        inputs = {
            "messages": [HumanMessage(content=query)],
            "agent_id": agent_id,
            "query": query,
            "session_id": None,
            "current_page_id": None,
            "page_analysis": None,
            "iteration_count": 0,
            "max_iterations": 15,
            "error": None,
        }

        step_number = 0
        current_answer = ""

        try:
            async for event in self.agent.astream_events(inputs, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")
                event_data = event.get("data", {})

                # Agent decided to call a tool
                if event_type == "on_tool_start":
                    step_number += 1
                    tool_input = event_data.get("input", {})

                    detail = self._format_tool_detail(event_name, tool_input)

                    yield self._format_sse(StreamEvent(
                        event=StreamEventType.step_start,
                        data={
                            "step_number": step_number,
                            "action": event_name,
                            "detail": detail,
                        }
                    ))

                # Tool finished
                elif event_type == "on_tool_end":
                    output = event_data.get("output", "")
                    is_error = isinstance(output, str) and output.startswith("Error")

                    if is_error:
                        yield self._format_sse(StreamEvent(
                            event=StreamEventType.step_error,
                            data={
                                "step_number": step_number,
                                "action": event_name,
                                "error": output,
                            }
                        ))
                    else:
                        yield self._format_sse(StreamEvent(
                            event=StreamEventType.step_complete,
                            data={
                                "step_number": step_number,
                                "action": event_name,
                            }
                        ))

                # LLM generating tokens
                elif event_type == "on_chat_model_stream":
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                            yield self._format_sse(StreamEvent(
                                event=StreamEventType.answer_chunk,
                                data={"chunk": chunk.content}
                            ))
                            current_answer += chunk.content

                # Agent is reasoning
                elif event_type == "on_chat_model_start":
                    if step_number > 0:
                        yield self._format_sse(StreamEvent(
                            event=StreamEventType.thinking,
                            data={"detail": "Agent is reasoning..."}
                        ))
                # Cleanup node finished
                elif event_type == "on_chain_end" and event_name == "cleanup":
                    yield self._format_sse(StreamEvent(
                        event=StreamEventType.cleanup,
                        data={"detail": "Cleaning up session"}
                    ))

            # Agent finished
            yield self._format_sse(StreamEvent(
                event=StreamEventType.answer_complete,
                data={"answer": current_answer}
            ))

            yield self._format_sse(StreamEvent(
                event=StreamEventType.done,
                data={"success": True}
            ))

        except Exception as e:
            logger.error(f"Streaming execution failed: {str(e)}", exc_info=True)
            yield self._format_sse(StreamEvent(
                event=StreamEventType.error,
                data={"error": str(e)}
            ))

    def _format_sse(self, stream_event: StreamEvent) -> str:
        return f"event: {stream_event.event.value}\ndata: {json.dumps(stream_event.data)}\n\n"

    def _extract_steps(self, messages: list) -> list[WorkflowStep]:
        steps = []
        step_number = 1

        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    detail = self._format_tool_detail(tool_name, tool_args)

                    steps.append(WorkflowStep(
                        step_number=step_number,
                        action=tool_name,
                        detail=detail,
                        success=True,
                    ))
                    step_number += 1

            if isinstance(message, ToolMessage) and steps:
                content = message.content
                if isinstance(content, str) and content.startswith("Error"):
                    steps[-1].success = False
                    steps[-1].detail += f" → {content}"

        return steps

    def _extract_answer(self, messages: list) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                content = message.content
                if isinstance(content, str):
                    return content
                return str(content)

        return "The agent completed but did not produce a final answer."

    def _extract_session_id(self, messages: list) -> str | None:
        for message in messages:
            if isinstance(message, ToolMessage) and isinstance(message.content, str):
                if "session_id:" in message.content:
                    try:
                        part = message.content.split("session_id:")[1]
                        session_id = part.split(",")[0].strip()
                        return session_id
                    except (IndexError, ValueError):
                        continue
        return None

    def _format_tool_detail(self, tool_name: str, tool_args: dict) -> str:
        match tool_name:
            case "create_session":
                return "Creating browser session"
            case "navigate":
                url = tool_args.get("url", "unknown")
                return f"Navigating to {url}"
            case "analyze_page":
                return "Analyzing page structure"
            case "get_accessibility_tree":
                return "Getting accessibility tree"
            case "get_page_content":
                return "Extracting page content"
            case "execute_js":
                script = tool_args.get("script", "")
                preview = script[:80] + "..." if len(script) > 80 else script
                return f"Executing JavaScript: {preview}"
            case "search_text":
                query = tool_args.get("query", "")
                return f"Searching page text for \"{query}\""
            case "capture_screenshot":
                return "Capturing screenshot of current page"
            case "close_page":
                return "Closing page"
            case "analyze_page":
                return "Analyzing page structure"
            case "get_accessibility_tree":
                return "Getting accessibility tree"
            case _:
                return f"Calling {tool_name} with {tool_args}"
