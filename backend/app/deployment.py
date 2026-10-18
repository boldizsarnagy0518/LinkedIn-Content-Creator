"""One ASGI process for the web API, MCP transport and OAuth discovery."""

from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Mount


def create_deployment_app(api: Starlette, mcp: Starlette) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with api.router.lifespan_context(api), mcp.router.lifespan_context(mcp):
            yield

    return Starlette(routes=[Mount("/api", app=api), Mount("/", app=mcp)], lifespan=lifespan)


def create_app() -> Starlette:
    from app.main import app as api_app
    from app.mcp_server import app as mcp_app

    return create_deployment_app(api_app, mcp_app)
