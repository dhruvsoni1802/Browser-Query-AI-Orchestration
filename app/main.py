from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.services.browser_client import BrowserClient
from app.services.agent_service import AgentService
from app.api.routes import router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize shared resources
    logger.info("Initializing browser client...")
    app.state.browser_client = BrowserClient(
        base_url=str(settings.infrastructure_url)
    )

    logger.info("Building agent service...")
    app.state.agent_service = AgentService(
        client=app.state.browser_client
    )

    logger.info("Orchestrator ready.")
    yield

    # Shutdown: clean up resources
    logger.info("Shutting down browser client...")
    await app.state.browser_client.close()


app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    lifespan=lifespan,
)

app.include_router(router)