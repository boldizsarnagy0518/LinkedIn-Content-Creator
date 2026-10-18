import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from mcp import Client

from app.mcp_server import create_mcp_server


def test_mcp_tools_advertise_accurate_annotations_and_structured_results(tmp_path: Path) -> None:
    async def scenario() -> None:
        server = create_mcp_server(tmp_path / "contentops.db")
        tools = {tool.name: tool for tool in await server.list_tools()}

        assert set(tools) == {
            "contentops_capture_idea",
            "contentops_capture_research",
            "contentops_list_content_items",
            "contentops_get_content_item",
            "contentops_get_writing_context",
            "contentops_get_author_memory",
            "contentops_update_author_memory",
            "contentops_update_writing_profile",
            "contentops_save_draft_version",
            "contentops_request_changes",
            "contentops_approve_draft",
            "contentops_set_publication_plan",
            "contentops_confirm_external_schedule",
            "contentops_mark_published",
            "contentops_record_performance_snapshot",
            "contentops_revoke_approval",
            "contentops_archive_content_item",
            "contentops_export_workspace",
        }
        assert tools["contentops_get_content_item"].annotations.read_only_hint is True
        assert tools["contentops_capture_idea"].annotations.read_only_hint is False
        assert tools["contentops_capture_idea"].annotations.idempotent_hint is True
        assert tools["contentops_approve_draft"].annotations.open_world_hint is False
        assert tools["contentops_set_publication_plan"].annotations.open_world_hint is False
        assert tools["contentops_confirm_external_schedule"].annotations.open_world_hint is False
        assert tools["contentops_mark_published"].annotations.open_world_hint is False
        assert tools["contentops_record_performance_snapshot"].annotations.open_world_hint is False
        assert tools["contentops_archive_content_item"].annotations.destructive_hint is True
        assert not any(prohibited in tool_name for tool_name in tools for prohibited in ("linkedin", "comment", "like"))

        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "contentops_capture_idea",
                {
                    "raw_idea": "Ebből legyen később egy poszt.",
                    "idempotency_key": "mcp-idea-request-001",
                },
            )
            assert result.is_error is not True
            assert result.structured_content is not None
            assert result.structured_content["status"] == "captured"
            assert result.structured_content["versions"] == []

    asyncio.run(scenario())


def test_streamable_http_server_exposes_mcp_endpoint(tmp_path: Path) -> None:
    with socket.socket() as probe_socket:
        probe_socket.bind(("127.0.0.1", 0))
        port = probe_socket.getsockname()[1]

    environment = os.environ.copy()
    environment.update(
        {
            "CONTENTOPS_DB_PATH": str(tmp_path / "http-contentops.db"),
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "app.mcp_server", "--transport", "streamable-http"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    async def probe() -> set[str]:
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            return {tool.name for tool in (await client.list_tools()).tools}

    try:
        last_error: Exception | None = None
        for _ in range(40):
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(f"MCP server exited early. stdout={stdout!r} stderr={stderr!r}")
            try:
                tool_names = asyncio.run(probe())
                break
            except Exception as error:  # noqa: BLE001 - retry while the subprocess starts
                last_error = error
                time.sleep(0.1)
        else:
            raise AssertionError(f"MCP HTTP endpoint did not become ready: {last_error}")

        assert "contentops_get_writing_context" in tool_names
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
