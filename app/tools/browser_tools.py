import httpx
from langchain_core.tools import tool
from app.services.browser_client import BrowserClient


def create_browser_tools(client: BrowserClient) -> list:
  
    @tool
    async def create_session(agent_id: str, session_name: str | None = None) -> str:
        """
        Create a new browser session for web browsing tasks.

        Call this FIRST before any browsing operations. Returns a session_id
        that you must use for all subsequent operations (navigate, execute,
        screenshot, etc.).

        Args:
            agent_id: A unique identifier for this agent instance.
            session_name: Optional human-readable name for tracking.

        Returns:
            A message containing the session_id you need for further operations.
        """
        try:
            result = await client.create_session(agent_id, session_name)
            return f"Session created. session_id: {result.session_id}, session_name: {result.session_name}"
        except httpx.HTTPStatusError as e:
            return f"Error creating session: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error creating session: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error creating session: {str(e)}"

    @tool
    async def navigate(session_id: str, url: str) -> str:
        """
        Navigate to a URL in an existing browser session.

        This opens a webpage and returns a page_id. You need this page_id
        for all page-level operations (getting content, executing JavaScript,
        taking screenshots).

        You MUST have a session_id from create_session before calling this.

        Args:
            session_id: The session ID from create_session.
            url: The full URL to navigate to (must include https://).

        Returns:
            A message containing the page_id and the final URL after any redirects.
        """
        try:
            result = await client.navigate(session_id, url)
            return f"Navigated successfully. page_id: {result.page_id}, url: {result.url}"
        except httpx.HTTPStatusError as e:
            return f"Error navigating to {url}: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error navigating: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error navigating to {url}: {str(e)}"

    @tool
    async def get_page_content(session_id: str, page_id: str) -> str:
        """
        Get the full HTML content of a page.

        Use this to read the content of a webpage after navigating to it.
        Returns the raw HTML which you can analyze to find information.

        For very large pages, consider using execute_js to extract specific
        elements instead of reading the entire HTML.

        Args:
            session_id: The session ID from create_session.
            page_id: The page ID from navigate.

        Returns:
            The HTML content of the page.
        """
        try:
            result = await client.get_page_content(session_id, page_id)
            return f"Page content (length: {result.length}):\n{result.content}"
        except httpx.HTTPStatusError as e:
            return f"Error getting page content: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error getting page content: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error getting page content: {str(e)}"

    @tool
    async def execute_js(session_id: str, page_id: str, script: str) -> str:
        """
        Execute JavaScript on a page to interact with it or extract specific data.

        Use this for:
        - Clicking buttons or links
        - Filling in forms
        - Scrolling the page
        - Extracting specific elements (e.g., document.querySelector('.job-listing').innerText)
        - Any DOM manipulation

        The script runs in the page's browser context and has access to the
        full DOM API.

        Args:
            session_id: The session ID from create_session.
            page_id: The page ID from navigate.
            script: JavaScript code to execute. Should return a value.

        Returns:
            The result of the JavaScript execution as a string.
        """
        try:
            result = await client.execute_js(session_id, page_id, script)
            return f"JavaScript executed successfully. result: {result.result}"
        except httpx.HTTPStatusError as e:
            return f"Error executing JavaScript: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error executing JavaScript: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error executing JavaScript: {str(e)}"

    @tool
    async def capture_screenshot(session_id: str, page_id: str) -> str:
        """
        Capture a screenshot of the current page state.

        Use this when you need to visually inspect a page, for example
        to verify navigation worked correctly or to see rendered content
        that isn't in the HTML (like canvas elements or images).

        Args:
            session_id: The session ID from create_session.
            page_id: The page ID from navigate.

        Returns:
            A message confirming the screenshot was captured, with its size.
            The actual image data is base64 encoded.
        """
        try:
            result = await client.capture_screenshot(session_id, page_id)
            return f"Screenshot captured successfully. size: {result.size}, format: {result.format}"
        except httpx.HTTPStatusError as e:
            return f"Error capturing screenshot: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error capturing screenshot: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error capturing screenshot: {str(e)}"

    @tool
    async def close_page(session_id: str, page_id: str) -> str:
        """
        Close a specific page in a session.

        Call this when you're done with a page to free browser resources.
        The page_id will no longer be usable after this.

        Args:
            session_id: The session ID from create_session.
            page_id: The page ID from navigate.

        Returns:
            Confirmation that the page was closed.
        """
        try:
            await client.close_page(session_id, page_id)
            return f"Page closed successfully. page_id: {page_id}"
        except httpx.HTTPStatusError as e:
            return f"Error closing page: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error closing page: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error closing page: {str(e)}"

    @tool
    async def close_session(session_id: str) -> str:
        """
        Close a browser session. Session data is preserved and can be resumed later.

        Call this when the task is complete but you might want to
        resume later. All pages will be disposed.

        Args:
            session_id: The session ID from create_session.

        Returns:
            Confirmation that the session was closed.
        """
        try:
            result = await client.close_session(session_id)
            return f"Session closed successfully. session_id: {result.session_id}, session_name: {result.session_name}"
        except httpx.HTTPStatusError as e:
            return f"Error closing session: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error closing session: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error closing session: {str(e)}"

    @tool
    async def delete_session(session_id: str) -> str:
        """
        Permanently delete a browser session and all its data.

        Call this for final cleanup when you're completely done with a task
        and don't need to resume. This is irreversible.

        Args:
            session_id: The session ID from create_session.

        Returns:
            Confirmation that the session was deleted.
        """
        try:
            await client.delete_session(session_id)
            return f"Session deleted successfully. session_id: {session_id}"
        except httpx.HTTPStatusError as e:
            return f"Error deleting session: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error deleting session: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error deleting session: {str(e)}"

    return [
        create_session,
        navigate,
        get_page_content,
        execute_js,
        capture_screenshot,
        close_page,
        close_session,
        delete_session,
    ]