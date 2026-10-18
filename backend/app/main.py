from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.content.api import profile_router
from app.content.api import router as content_router
from app.content.dependencies import _get_content_workflow_service
from app.content.repository import ConflictError, NotFoundError, WorkflowError
from app.models import ApiErrorResponse, HealthResponse

app = FastAPI(
    title="ContentOps API",
    description="Durable workflow state shared by the ContentOps MCP server and web application.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(content_router)
app.include_router(profile_router)


def get_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate[:100] if candidate else uuid4().hex


@app.exception_handler(WorkflowError)
async def workflow_error_handler(request: Request, exc: WorkflowError) -> JSONResponse:
    request_id = get_request_id(request.headers.get("X-Request-ID"))
    if isinstance(exc, NotFoundError):
        status_code, code = 404, "content_item_not_found"
    elif isinstance(exc, ConflictError):
        status_code, code = 409, "content_workflow_conflict"
    else:
        status_code, code = 400, "content_workflow_error"

    payload = ApiErrorResponse(error=str(exc), code=code, request_id=request_id)
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers={"X-Request-ID": request_id},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database = "postgres" if settings.contentops_database_url else "sqlite"
    return HealthResponse(status="ok", service="contentops-api", database=database)


@app.get("/ready", include_in_schema=False)
def ready() -> JSONResponse:
    try:
        _get_content_workflow_service().get_writing_context(max_examples=0)
    except Exception:
        # Do not expose database connection details through a public health probe.
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ready"})
