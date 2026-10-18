# ContentOps Python backend

The backend is the product core. It stores workflow state and exposes the same use cases through FastAPI and MCP; it does not call an LLM.

## Layers

```text
FastAPI routes       MCP tools
       \              /
        ContentWorkflowService
                  |
          ContentRepository
             /         \
         SQLite       Postgres
```

- `app/content/models.py`: domain and response models
- `app/content/ports.py`: repository protocol
- `app/content/service.py`: application use cases
- `app/content/repository.py`: SQL adapters and state invariants
- `app/content/api.py`: HTTP adapter
- `app/mcp_server.py`: MCP adapter
- `app/auth.py`: local identity and Supabase JWT verification

## Run

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run python -m app.mcp_server --transport stdio
```

The HTTP MCP transport defaults to `127.0.0.1:8001/mcp`:

```powershell
uv run python -m app.mcp_server --transport streamable-http
```

## Test

```powershell
uv run ruff check app tests
uv run pytest
```

## Environment

Local defaults need no `.env`. Production uses:

```dotenv
CONTENTOPS_DATABASE_URL=postgresql://...
AUTH_MODE=supabase
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
CONTENTOPS_OWNER_USER_ID=SUPABASE_USER_UUID
MCP_PUBLIC_URL=https://api.example.com/mcp
FRONTEND_ORIGIN=https://app.example.com
```

Both transports must point to the same database. Production requests are accepted only when a valid Supabase token belongs to the configured owner UUID.

For hosted use, follow [the complete deployment guide](../docs/DEPLOYMENT_HU.md). `app.deployment:create_app --factory` combines both transports and preserves their lifespans. The Docker image defaults to `APP_ENV=production` and requires `MCP_OAUTH_CLIENT_ID` in addition to the settings above. MCP validates its own URL as the token audience; the web API keeps the `authenticated` audience. Configure the provided Supabase token hook before connecting ChatGPT.
