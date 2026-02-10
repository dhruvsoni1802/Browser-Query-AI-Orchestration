from fastapi import APIRouter, Request
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    
)
from app.config import settings

router = APIRouter()


def get_browser_client(request: Request):
    return request.app.state.browser_client


def get_agent_service(request: Request):
    return request.app.state.agent_service


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    client = get_browser_client(request)
    infra_reachable = await client.ping()

    return HealthResponse(
        version=settings.project_version,
        infrastructure_reachable=infra_reachable,
    )

#Submit a natural language query for the AI agent to process.
@router.post("/query", response_model=QueryResponse)
async def submit_query(query_request: QueryRequest, request: Request):
   
    agent_service = get_agent_service(request)

    return await agent_service.execute_query(
        query=query_request.query,
        agent_id=query_request.agent_id,
        session_name=query_request.session_name,
    )