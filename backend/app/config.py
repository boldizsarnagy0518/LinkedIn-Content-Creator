from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONTENTOPS_DB_PATH = Path(__file__).resolve().parents[1] / ".data" / "contentops.db"


class Settings(BaseSettings):
    app_env: Literal["development", "production"] = "development"
    frontend_origin: str = "http://localhost:3000"
    contentops_db_path: Path = DEFAULT_CONTENTOPS_DB_PATH
    contentops_database_url: str | None = None
    auth_mode: Literal["local", "supabase"] = "local"
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    contentops_owner_user_id: str | None = None
    mcp_public_url: str | None = None
    mcp_oauth_client_id: str | None = None
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8001, ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_deployment(self) -> "Settings":
        if self.app_env == "production":
            if self.auth_mode != "supabase" or not self.contentops_database_url:
                raise ValueError("Production requires Supabase auth and CONTENTOPS_DATABASE_URL.")
            if not self.contentops_owner_user_id or not self.mcp_oauth_client_id:
                raise ValueError("Production requires CONTENTOPS_OWNER_USER_ID and MCP_OAUTH_CLIENT_ID.")
            for name in ("frontend_origin", "supabase_url", "mcp_public_url"):
                value = urlsplit(getattr(self, name) or "")
                if value.scheme != "https" or not value.hostname or value.username or value.query or value.fragment:
                    raise ValueError(f"Production requires a canonical HTTPS URL for {name}.")
                if name == "mcp_public_url" and value.path != "/mcp":
                    raise ValueError("MCP_PUBLIC_URL must end in /mcp without a trailing slash.")
        return self


settings = Settings()
