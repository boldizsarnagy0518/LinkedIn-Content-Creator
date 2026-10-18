"""Validate deployment env files without connecting or printing their values."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from dotenv import dotenv_values
from psycopg.conninfo import conninfo_to_dict


def validate_configs(backend: dict, frontend: dict) -> list[str]:
    errors = []
    required = {
        "backend": (backend, ["APP_ENV", "AUTH_MODE", "CONTENTOPS_DATABASE_URL", "SUPABASE_URL",
                              "CONTENTOPS_OWNER_USER_ID", "MCP_OAUTH_CLIENT_ID", "MCP_PUBLIC_URL", "FRONTEND_ORIGIN"]),
        "frontend": (frontend, ["PYTHON_BACKEND_URL", "NEXT_PUBLIC_SUPABASE_URL",
                                "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "CONTENTOPS_OWNER_USER_ID",
                                "MCP_OAUTH_CLIENT_ID"]),
    }
    for label, (values, names) in required.items():
        for name in names:
            value = values.get(name)
            if not value or "REPLACE" in value:
                errors.append(f"{label}: {name} is missing or still a placeholder.")
    if errors:
        return errors
    if backend["APP_ENV"] != "production" or backend["AUTH_MODE"] != "supabase":
        errors.append("backend: APP_ENV must be production and AUTH_MODE must be supabase.")
    if backend.get("SUPABASE_JWT_AUDIENCE", "authenticated") != "authenticated":
        errors.append("backend: web JWT audience must be authenticated.")
    for name in ("CONTENTOPS_OWNER_USER_ID", "MCP_OAUTH_CLIENT_ID"):
        if backend[name] != frontend[name]:
            errors.append(f"Both services must use the same {name}.")
        try:
            UUID(backend[name])
        except ValueError:
            errors.append(f"backend: {name} must be a UUID from Supabase.")
    urls = {}
    for name, value in {
        "SUPABASE_URL": backend["SUPABASE_URL"], "MCP_PUBLIC_URL": backend["MCP_PUBLIC_URL"],
        "FRONTEND_ORIGIN": backend["FRONTEND_ORIGIN"], "PYTHON_BACKEND_URL": frontend["PYTHON_BACKEND_URL"],
        "NEXT_PUBLIC_SUPABASE_URL": frontend["NEXT_PUBLIC_SUPABASE_URL"],
    }.items():
        try:
            parsed = urlsplit(value)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.query or parsed.fragment):
                raise ValueError
            urls[name] = parsed
        except ValueError:
            errors.append(f"{name} must be a canonical HTTPS URL without credentials, query or fragment.")
    if len(urls) == 5:
        if backend["SUPABASE_URL"].rstrip("/") != frontend["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/"):
            errors.append("The two Supabase project URLs do not match.")
        if urls["MCP_PUBLIC_URL"].path != "/mcp":
            errors.append("MCP_PUBLIC_URL must end in /mcp.")
        if urls["PYTHON_BACKEND_URL"].path != "/api":
            errors.append("PYTHON_BACKEND_URL must end in /api for the combined backend.")
        if urls["PYTHON_BACKEND_URL"].netloc != urls["MCP_PUBLIC_URL"].netloc:
            errors.append("API and MCP must point to the same backend host.")
        if urls["FRONTEND_ORIGIN"].path not in ("", "/"):
            errors.append("FRONTEND_ORIGIN must contain only the web origin.")
    try:
        connection = conninfo_to_dict(backend["CONTENTOPS_DATABASE_URL"])
        if connection.get("sslmode") not in ("require", "verify-ca", "verify-full"):
            errors.append("Database connection must explicitly require TLS (sslmode).")
        if connection.get("options") != "-c search_path=contentops":
            errors.append("Database options must select the private contentops schema: -c search_path=contentops.")
    except Exception:
        errors.append("CONTENTOPS_DATABASE_URL is not a valid PostgreSQL connection string.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-env", type=Path, required=True)
    parser.add_argument("--frontend-env", type=Path, required=True)
    args = parser.parse_args()
    try:
        backend = dict(dotenv_values(args.backend_env, interpolate=False))
        frontend = dict(dotenv_values(args.frontend_env, interpolate=False))
        if not args.backend_env.is_file() or not args.frontend_env.is_file():
            raise OSError
    except OSError:
        print("Cannot read both env files. Check their paths and permissions.")
        return 1
    errors = validate_configs(backend, frontend)
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: deployment settings are consistent. No secrets printed; no network calls made.")
        print("Still required: configured Supabase schema/token hook and a live OAuth acceptance test.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
