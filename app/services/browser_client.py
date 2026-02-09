import httpx
from app.config import settings
from app.models.schemas import (
    SessionInfo,
    SessionDetail,
    SessionListResponse,
    AgentSessionListResponse,
    NavigateResponse,
    ExecuteJsResponse,
    ScreenshotResponse,
    PageContentResponse,
    CloseSessionResponse,
    ResumeSessionResponse,
)
from typing import Optional


class BrowserClient:

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def ping(self) -> bool:
        #Check if the Go backend is reachable.We use list_sessions as a lightweight check — if it responds, the backend is up.
        try:
            response = await self.client.get("/sessions")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # Session Management APIs

    async def create_session(self, agent_id: str, session_name: Optional[str] = None) -> SessionInfo:
        payload = {"agent_id": agent_id}
        if session_name is not None:
            payload["session_name"] = session_name

        response = await self.client.post("/sessions", json=payload)
        response.raise_for_status()
        return SessionInfo(**response.json())

    async def get_session(self, session_id: str) -> SessionDetail:
        response = await self.client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return SessionDetail(**response.json())

    async def list_sessions(self) -> SessionListResponse:
        response = await self.client.get("/sessions")
        response.raise_for_status()
        return SessionListResponse(**response.json())

    async def list_agent_sessions(self, agent_id: str) -> AgentSessionListResponse:
        response = await self.client.get(f"/agents/{agent_id}/sessions")
        response.raise_for_status()
        return AgentSessionListResponse(**response.json())

    async def close_session(self, session_id: str) -> CloseSessionResponse:
        response = await self.client.put(f"/sessions/{session_id}/close")
        response.raise_for_status()
        return CloseSessionResponse(**response.json())

    async def delete_session(self, session_id: str) -> None:
        response = await self.client.delete(f"/sessions/{session_id}")
        response.raise_for_status()

    async def resume_session(self, agent_id: str, session_name: str) -> ResumeSessionResponse:
        payload = {"agent_id": agent_id, "session_name": session_name}
        response = await self.client.post("/sessions/resume", json=payload)
        response.raise_for_status()
        return ResumeSessionResponse(**response.json())

    # Page Operations APIs

    async def navigate(self, session_id: str, url: str) -> NavigateResponse:
        payload = {"url": url}
        response = await self.client.post(f"/sessions/{session_id}/navigate", json=payload)
        response.raise_for_status()
        return NavigateResponse(**response.json())

    async def execute_js(self, session_id: str, page_id: str, script: str) -> ExecuteJsResponse:
        payload = {"page_id": page_id, "script": script}
        response = await self.client.post(f"/sessions/{session_id}/execute", json=payload)
        response.raise_for_status()
        return ExecuteJsResponse(**response.json())

    async def capture_screenshot(self, session_id: str, page_id: str) -> ScreenshotResponse:
        payload = {"page_id": page_id}
        response = await self.client.post(f"/sessions/{session_id}/screenshot", json=payload)
        response.raise_for_status()
        return ScreenshotResponse(**response.json())

    async def get_page_content(self, session_id: str, page_id: str) -> PageContentResponse:
        response = await self.client.get(f"/sessions/{session_id}/pages/{page_id}/content")
        response.raise_for_status()
        return PageContentResponse(**response.json())

    async def close_page(self, session_id: str, page_id: str) -> None:
        response = await self.client.delete(f"/sessions/{session_id}/pages/{page_id}")
        response.raise_for_status()