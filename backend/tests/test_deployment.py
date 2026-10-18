import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp.server.auth.settings import AuthSettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.auth import SupabaseJwtVerifier
from app.config import Settings
from app.deployment import create_deployment_app
from app.mcp_server import create_mcp_server


def test_production_rejects_missing_auth_or_database():
    with pytest.raises(ValueError, match="Production requires"):
        Settings(_env_file=None, app_env="production")


def test_readiness_checks_storage_without_exposing_connection_errors(monkeypatch, tmp_path):
    from app import main
    from app.content.repository import SQLiteContentRepository
    from app.content.service import ContentWorkflowService

    service = ContentWorkflowService(SQLiteContentRepository(tmp_path / "ready.db"))
    monkeypatch.setattr(main, "_get_content_workflow_service", lambda: service)
    with TestClient(main.app) as client:
        assert client.get("/ready").json() == {"status": "ready"}

        def unavailable():
            raise RuntimeError("private-database-connection-details")

        monkeypatch.setattr(main, "_get_content_workflow_service", unavailable)
        result = client.get("/ready")
        assert result.status_code == 503
        assert "private" not in result.text


def test_mcp_accepts_only_resource_bound_owner_tokens_for_its_client():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = SupabaseJwtVerifier(
        supabase_url="https://project.supabase.co", audience="https://backend.test/mcp",
        owner_user_id="owner", oauth_client_id="contentops-client",
    )
    verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key()))
    claims = {
        "iss": "https://project.supabase.co/auth/v1", "sub": "owner", "aud": "https://backend.test/mcp",
        "client_id": "contentops-client", "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    assert asyncio.run(verifier.verify_token(jwt.encode(claims, key, algorithm="RS256"))) is not None
    for patch in ({"aud": "authenticated"}, {"sub": "stranger"}, {"client_id": "another-app"}, {"exp": 1}):
        token = jwt.encode({**claims, **patch}, key, algorithm="RS256")
        assert asyncio.run(verifier.verify_token(token)) is None


def test_combined_deployment_serves_discovery_challenge_and_api(tmp_path):
    started = []

    @asynccontextmanager
    async def api_lifespan(app):
        started.append(True)
        yield
        started.append(False)

    api = Starlette(routes=[Route("/health", lambda request: JSONResponse({"status": "ok"}))], lifespan=api_lifespan)
    verifier = SupabaseJwtVerifier(
        supabase_url="https://project.supabase.co", audience="https://backend.test/mcp", owner_user_id="owner",
        oauth_client_id="contentops-client",
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key()))
    token = jwt.encode({
        "iss": "https://project.supabase.co/auth/v1", "sub": "owner", "aud": "https://backend.test/mcp",
        "client_id": "contentops-client", "exp": datetime.now(UTC) + timedelta(minutes=5),
    }, key, algorithm="RS256")
    server = create_mcp_server(tmp_path / "deploy.db", auth=AuthSettings(
        issuer_url="https://project.supabase.co/auth/v1", resource_server_url="https://backend.test/mcp",
    ), token_verifier=verifier)
    mcp = server.streamable_http_app(stateless_http=True, json_response=True, host="backend.test")
    with TestClient(create_deployment_app(api, mcp), base_url="https://backend.test") as client:
        assert started == [True]
        assert client.get("/api/health").json() == {"status": "ok"}
        denied = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert denied.status_code == 401
        assert "resource_metadata=" in denied.headers["www-authenticate"]
        metadata_url = denied.headers["www-authenticate"].split('resource_metadata="')[1].split('"')[0]
        metadata = client.get(metadata_url).json()
        assert metadata["resource"] == "https://backend.test/mcp"
        assert metadata["authorization_servers"] == ["https://project.supabase.co/auth/v1"]
        authorized = client.post("/mcp", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream",
        }, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert authorized.status_code == 200
        assert any(tool["name"] == "contentops_capture_idea" for tool in authorized.json()["result"]["tools"])
    assert started == [True, False]
