from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.services.browser_client import BrowserClient
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
  
    #Manages the lifecycle of application-wide resources

    #Everything before 'yield' runs during startup.
    app.state.browser_client = BrowserClient(
        base_url=str(settings.infrastructure_url)
    )

    yield

    # Everything after 'yield' runs during shutdown.
    await app.state.browser_client.close()


app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    lifespan=lifespan,
)

app.include_router(router)