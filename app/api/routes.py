from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    WorkflowStep,
)
from app.config import settings

router = APIRouter()


 #Helper function to extract the BrowserClient from the application state.
def get_browser_client(request: Request):
    return request.app.state.browser_client


#Health check that verifies both this service and the Go backend.
@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    client = get_browser_client(request)
    infra_reachable = await client.ping()

    return HealthResponse(
        version=settings.project_version,
        infrastructure_reachable=infra_reachable,
    )


#Submit a natural language query for the AI agent to process.
# The logic is a placeholder for now. TODO: Replace with LangGraph agent.
@router.post("/query", response_model=QueryResponse)
async def submit_query(query_request: QueryRequest, request: Request):
    client = get_browser_client(request)
    steps = []

    try:
        # Step 1: Create a session
        session = await client.create_session(
            agent_id=query_request.agent_id,
            session_name=query_request.session_name,
        )
        steps.append(WorkflowStep(
            step_number=1,
            action="create_session",
            detail=f"Created session {session.session_id}",
        ))

        # Step 2: Placeholder.
        steps.append(WorkflowStep(
            step_number=2,
            action="placeholder",
            detail="Agent workflow not yet implemented — this is a stub",
        ))

        # Step 3: Cleanup
        await client.delete_session(session.session_id)
        steps.append(WorkflowStep(
            step_number=3,
            action="delete_session",
            detail=f"Cleaned up session {session.session_id}",
        ))

        return QueryResponse(
            query=query_request.query,
            agent_id=query_request.agent_id,
            session_id=session.session_id,
            answer="Agent workflow not yet implemented. Session was created and cleaned up successfully.",
            steps=steps,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")