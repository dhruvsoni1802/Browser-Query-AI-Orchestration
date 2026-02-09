import httpx
from app.config import settings
from typing import Optional

#HTTP client for the browser management Go backend service
class BrowserClient:

    def __init__(self, base_url: str):
        # .rstrip("/") removes any trailing slash to avoid double-slash. For example in URLs like "http://localhost:8080//sessions"
        self.base_url = base_url.rstrip("/")

        # This is the shared, long-lived client instance.
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),                  # 30 seconds request timeout
            headers={"Content-Type": "application/json"}, # Set the content type to JSON
            follow_redirects=True,                        # Follow redirects if the request is redirected
        )

    async def close(self):
        #Close the underlying HTTP client and release pooled connections.
        await self.client.aclose()

    # Session Management APIs

    async def create_session(self, agent_id: str, session_name: Optional[str] = None) -> dict:
        payload = {"agent_id": agent_id}
        if session_name is not None:
            payload["session_name"] = session_name

        response = await self.client.post("/sessions", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_session(self, session_id: str) -> dict:
        response = await self.client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    async def list_sessions(self) -> dict:
        response = await self.client.get("/sessions")
        response.raise_for_status()
        return response.json()

    async def list_agent_sessions(self, agent_id: str) -> dict:
        response = await self.client.get(f"/agents/{agent_id}/sessions")
        response.raise_for_status()
        return response.json()

    async def close_session(self, session_id: str) -> dict:
        response = await self.client.put(f"/sessions/{session_id}/close")
        response.raise_for_status()
        return response.json()

    async def delete_session(self, session_id: str) -> None:
        response = await self.client.delete(f"/sessions/{session_id}")
        response.raise_for_status()
        # 204 No Content — no body to parse

    async def resume_session(self, agent_id: str, session_name: str) -> dict:
        payload = {"agent_id": agent_id, "session_name": session_name}
        response = await self.client.post("/sessions/resume", json=payload)
        response.raise_for_status()
        return response.json()

    # Page Operations APIs

    async def navigate(self, session_id: str, url: str) -> dict:
        payload = {"url": url}
        response = await self.client.post(f"/sessions/{session_id}/navigate", json=payload)
        response.raise_for_status()
        return response.json()

    async def execute_js(self, session_id: str, page_id: str, script: str) -> dict:
        payload = {"page_id": page_id, "script": script}
        response = await self.client.post(f"/sessions/{session_id}/execute", json=payload)
        response.raise_for_status()
        return response.json()

    async def capture_screenshot(self, session_id: str, page_id: str) -> dict:
        payload = {"page_id": page_id}
        response = await self.client.post(f"/sessions/{session_id}/screenshot", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_page_content(self, session_id: str, page_id: str) -> dict:
        response = await self.client.get(f"/sessions/{session_id}/pages/{page_id}/content")
        response.raise_for_status()
        return response.json()

    async def close_page(self, session_id: str, page_id: str) -> None:
        response = await self.client.delete(f"/sessions/{session_id}/pages/{page_id}")
        response.raise_for_status()
        # 204 No Content — no body to parse