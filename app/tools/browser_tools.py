import httpx
import json
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
            if result.length > 50000:
                result.content = result.content[:50000] + f"\n\n... [TRUNCATED — full page is {result.length} chars. Use execute_js for targeted extraction.]"
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
            output = result.result
            if isinstance(output, (dict, list)):
                output = json.dumps(output)
            return f"JavaScript executed successfully. result: {output}"
        except httpx.HTTPStatusError as e:
            return f"Error executing JavaScript: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error executing JavaScript: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error executing JavaScript: {str(e)}"

    @tool
    async def search_text(session_id: str, page_id: str, query: str, limit: int = 20) -> str:
        """
        Search for a keyword in the page text and return matching lines.

        This avoids brittle CSS selectors by scanning visible text content.

        Args:
            session_id: The session ID from create_session.
            page_id: The page ID from navigate.
            query: The keyword to search for (case-insensitive).
            limit: Max number of matching lines to return.

        Returns:
            Matching lines containing the query term.
        """
        try:
            q = json.dumps(query)
            script = f"""
            (function() {{
              const query = {q}.toLowerCase();
              const lines = document.body.innerText.split('\\n')
                .map(l => l.trim())
                .filter(Boolean);
              const matches = lines.filter(l => l.toLowerCase().includes(query));
              return matches.slice(0, {limit});
            }})()
            """
            result = await client.execute_js(session_id, page_id, script)
            output = result.result
            if isinstance(output, (dict, list)):
                output = json.dumps(output)
            return f"Search results: {output}"
        except httpx.HTTPStatusError as e:
            return f"Error searching text: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error searching text: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error searching text: {str(e)}"

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
    
    @tool
    async def analyze_page(session_id: str, page_id: str) -> str:
        """
        Analyze the structure of a page — CSS classes, IDs, headings,
        interactive elements, and text snippets.

        Use this to understand a page's structure BEFORE attempting
        to extract data with execute_js. This tells you what CSS
        classes and IDs actually exist on the page.

        Results are cached — calling this multiple times for the
        same page is free.

        Args:
            session_id: The session ID.
            page_id: The page ID from navigate.

        Returns:
            A structural overview of the page.
        """
        try:
            result = await client.analyze_page(session_id, page_id)
            analysis = result.analysis
            structure = analysis.structure

            parts = [f"Page: {analysis.title} ({analysis.url})"]

            if structure.headings:
                for tag, texts in structure.headings.items():
                    parts.append(f"  {tag}: {', '.join(texts[:5])}")

            if structure.classes:
                parts.append(f"CSS classes: {', '.join(structure.classes[:30])}")

            if structure.ids:
                parts.append(f"IDs: {', '.join(structure.ids[:20])}")

            if structure.interactive:
                for elem_type, items in structure.interactive.items():
                    if items:
                        parts.append(f"{elem_type}: {', '.join(items[:10])}")

            if structure.semantic_sections:
                section_summaries = []
                for section in structure.semantic_sections[:10]:
                    classes = ", ".join(section.class_name[:5]) if section.class_name else ""
                    selectors = ", ".join(section.selectors[:3]) if section.selectors else ""
                    summary = section.type
                    if classes:
                        summary += f" [{classes}]"
                    if selectors:
                        summary += f" ({selectors})"
                    section_summaries.append(summary)
                parts.append(f"Sections: {', '.join(section_summaries)}")

            if structure.data_attributes:
                parts.append(f"Data attributes: {', '.join(structure.data_attributes[:15])}")

            if structure.text_snippets:
                parts.append(f"Text snippets: {' | '.join(structure.text_snippets[:5])}")

            return "\n".join(parts)

        except httpx.HTTPStatusError as e:
            return f"Error analyzing page: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error analyzing page: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error analyzing page: {str(e)}"

    @tool
    async def get_accessibility_tree(session_id: str, page_id: str) -> str:
        """
        Get the accessibility tree of a page — the semantic structure
        that screen readers see.

        This shows roles (heading, button, link, list), names, and
        hierarchy WITHOUT any CSS noise. Useful for understanding
        the meaning and organization of page content.

        Use this when analyze_page doesn't give enough context,
        or when you need to understand the semantic hierarchy of
        content on the page.

        Args:
            session_id: The session ID.
            page_id: The page ID from navigate.

        Returns:
            The accessibility tree as a formatted string.
        """
        try:
            result = await client.get_accessibility_tree(session_id, page_id)

            def format_node(node, depth=0) -> str:
                indent = "  " * depth
                line = f"{indent}[{node.role}]"
                if node.name:
                    # Truncate long names
                    name = node.name[:80] + "..." if len(node.name) > 80 else node.name
                    line += f" \"{name}\""
                lines = [line]
                for child in node.children[:50]:  # Limit children to avoid huge output
                    lines.append(format_node(child, depth + 1))
                return "\n".join(lines)

            formatted = "\n".join(format_node(node) for node in result.nodes[:20])
            return f"Accessibility tree:\n{formatted}"

        except httpx.HTTPStatusError as e:
            return f"Error getting accessibility tree: HTTP {e.response.status_code} — {e.response.text}"
        except httpx.ConnectError:
            return f"Error getting accessibility tree: Could not connect to browser infrastructure"
        except Exception as e:
            return f"Error getting accessibility tree: {str(e)}"

    return [
        navigate,
        analyze_page,
        get_accessibility_tree,
        get_page_content,
        execute_js,
        search_text,
        capture_screenshot,
        close_page,
    ]
