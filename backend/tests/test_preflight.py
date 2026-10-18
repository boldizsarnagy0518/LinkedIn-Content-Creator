from app.preflight import validate_configs


def configs():
    owner = "11111111-1111-4111-8111-111111111111"
    client = "22222222-2222-4222-8222-222222222222"
    backend = {
        "APP_ENV": "production", "AUTH_MODE": "supabase",
        "CONTENTOPS_DATABASE_URL": "postgresql://user:secret@db.test/db?sslmode=require&"
                                   "options=-c%20search_path%3Dcontentops",
        "SUPABASE_URL": "https://project.supabase.co", "CONTENTOPS_OWNER_USER_ID": owner,
        "MCP_OAUTH_CLIENT_ID": client, "MCP_PUBLIC_URL": "https://backend.test/mcp",
        "FRONTEND_ORIGIN": "https://web.test",
    }
    frontend = {
        "PYTHON_BACKEND_URL": "https://backend.test/api", "NEXT_PUBLIC_SUPABASE_URL": backend["SUPABASE_URL"],
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "test-key", "CONTENTOPS_OWNER_USER_ID": owner,
        "MCP_OAUTH_CLIENT_ID": client,
    }
    return backend, frontend


def test_matching_configuration_passes_without_network():
    assert validate_configs(*configs()) == []


def test_detects_mismatched_project_and_wrong_api_path_without_leaking_values():
    backend, frontend = configs()
    frontend.update(PYTHON_BACKEND_URL="https://backend.test", NEXT_PUBLIC_SUPABASE_URL="https://other.test")
    backend["CONTENTOPS_DATABASE_URL"] = "postgresql://user:secret@db.test/db"
    errors = " ".join(validate_configs(backend, frontend))
    assert "project URLs" in errors and "/api" in errors and "schema" in errors and "TLS" in errors
    assert "secret" not in errors


def test_placeholders_fail_closed():
    backend, frontend = configs()
    backend["MCP_OAUTH_CLIENT_ID"] = "REPLACE_CLIENT_UUID"
    assert "placeholder" in validate_configs(backend, frontend)[0]
