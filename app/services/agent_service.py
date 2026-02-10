from app.graph.workflow import build_agent
from app.graph.state import AgentState
from app.services.browser_client import BrowserClient
from app.models.schemas import QueryResponse, WorkflowStep
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.models.schemas import StreamEvent, StreamEventType
import logging
import json
from typing import cast, AsyncGenerator

logger = logging.getLogger(__name__)


#Bridge between FastAPI and LangGraph.
class AgentService:

    def __init__(self, client: BrowserClient):
        self.agent = build_agent(client)

    async def execute_query(self, query: str, agent_id: str, session_name: str | None = None) -> QueryResponse:
        inputs: AgentState = {
            "messages": [HumanMessage(
                content=f"Agent ID: {agent_id}\n"
                        f"{'Session name: ' + session_name if session_name else ''}"
                        f"Task: {query}"
            )]
        }

        try:
            result = await self.agent.ainvoke(inputs)
            messages = result["messages"]

            # Extract workflow steps and final answer from the message history
            steps = self._extract_steps(messages)
            answer = self._extract_answer(messages)

            # Try to find the session_id from the tool messages
            session_id = self._extract_session_id(messages)

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
            "messages": [HumanMessage(
                content=f"Agent ID: {agent_id}\n"
                        f"{'Session name: ' + session_name + chr(10) if session_name else ''}"
                        f"Task: {query}"
            )]
        }

        step_number = 0
        current_answer = ""

        try:
            async for event in self.agent.astream_events(inputs, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")
                event_data = event.get("data", {})

                #Agent decided to call a tool
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

                #Tool finished: got a result back
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
                
                #LLM is generating tokens (the final answer)
                elif event_type == "on_chat_model_stream":
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Only stream text content, not tool call tokens
                        if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                            current_answer += chunk.content

                            #TODO: Uncomment this to see LLM generating tokens (the final answer)
                            # yield self._format_sse(StreamEvent(
                            #     event=StreamEventType.answer_chunk,
                            #     data={"chunk": chunk.content}
                            # ))

                #Agent is reasoning
                elif event_type == "on_chat_model_start":
                    if step_number > 0:
                        yield self._format_sse(StreamEvent(
                            event=StreamEventType.thinking,
                            data={"detail": "Agent is reasoning..."}
                        ))

            #Agent finished
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

    #Helper method to extract workflow steps from the message history.
    def _extract_steps(self, messages: list) -> list[WorkflowStep]:
        steps = []
        step_number = 1

        for message in messages:
            # AIMessage with tool_calls means the agent decided to call a tool
            if isinstance(message, AIMessage) and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})

                    # Build a human-readable description of what happened
                    detail = self._format_tool_detail(tool_name, tool_args)

                    steps.append(WorkflowStep(
                        step_number=step_number,
                        action=tool_name,
                        detail=detail,
                        success=True,
                    ))
                    step_number += 1

            # ToolMessage means the result from a tool execution
            # Check if it was an error and update the last step accordingly
            if isinstance(message, ToolMessage) and steps:
                content = message.content
                if isinstance(content, str) and content.startswith("Error"):
                    steps[-1].success = False
                    steps[-1].detail += f" → {content}"

        return steps

    #Helper method to extract the final answer from the message history.
    def _extract_answer(self, messages: list) -> str:

        # Walk backwards through messages to find the last AIMessage without tool calls
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                content = message.content
                if isinstance(content, str):
                    return content
                # If content is a list, convert to string
                return str(content)

        return "The agent completed but did not produce a final answer."

    #Helper method to extract the session_id from the tool messages.
    def _extract_session_id(self, messages: list) -> str | None:
        for message in messages:
            if isinstance(message, ToolMessage) and isinstance(message.content, str):
                if "session_id:" in message.content:
                    try:
                        # Parse "session_id: sess_xxx" from the tool output
                        part = message.content.split("session_id:")[1]
                        session_id = part.split(",")[0].strip()
                        return session_id
                    except (IndexError, ValueError):
                        continue
        return None

    #Helper method to format the tool detail for the workflow visualization.
    def _format_tool_detail(self, tool_name: str, tool_args: dict) -> str:
        match tool_name:
            case "create_session":
                agent_id = tool_args.get("agent_id", "unknown")
                return f"Creating browser session for agent '{agent_id}'"
            case "navigate":
                url = tool_args.get("url", "unknown")
                return f"Navigating to {url}"
            case "get_page_content":
                return "Extracting page content"
            case "execute_js":
                script = tool_args.get("script", "")
                # Truncate long scripts for readability
                preview = script[:80] + "..." if len(script) > 80 else script
                return f"Executing JavaScript: {preview}"
            case "capture_screenshot":
                return "Capturing screenshot of current page"
            case "close_page":
                return "Closing page"
            case "close_session":
                return "Closing session (preserving data)"
            case "delete_session":
                return "Deleting session (final cleanup)"
            case _:
                return f"Calling {tool_name} with {tool_args}"