from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from app.tools.browser_tools import create_browser_tools
from app.services.browser_client import BrowserClient
from app.config import settings


SYSTEM_PROMPT = """You are a browser automation agent. You help users 
find information on the web by browsing pages programmatically.

You have access to tools that let you:
- Create browser sessions
- Navigate to URLs
- Read page content (HTML)
- Execute JavaScript on pages
- Take screenshots
- Close pages and sessions

WORKFLOW:
1. Always start by creating a session with create_session
2. Navigate to the relevant URL
3. Get page content or execute JS to extract information
4. Analyze the content to answer the user's query
5. ALWAYS clean up by deleting the session when done

Be methodical. If a page is too large, use execute_js to extract
specific elements rather than reading the entire HTML.

Always delete the session when you're finished, even if you 
encountered errors during the task."""


def _build_llm():
    if settings.llm_provider == "ollama":
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

    elif settings.llm_provider == "openai":
        openai_kwargs: dict = {
            "model": settings.llm_model,
            "temperature": 0,
        }

        if settings.llm_api_key:
            openai_kwargs["api_key"] = settings.llm_api_key

        return ChatOpenAI(**openai_kwargs)

    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        anthropic_kwargs: dict = {
            "model_name": settings.llm_model,
            "temperature": 0,
            "timeout": None,
            "stop": None,
        }

        if settings.llm_api_key:
            anthropic_kwargs["api_key"] = settings.llm_api_key
        return ChatAnthropic(**anthropic_kwargs)
    
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def build_agent(client: BrowserClient):
    llm = _build_llm()
    tools = create_browser_tools(client)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent
