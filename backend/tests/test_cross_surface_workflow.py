import asyncio
import os
import socket
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from mcp import Client

from app.content.dependencies import get_content_workflow_service
from app.content.repository import SQLiteContentRepository
from app.content.service import ContentWorkflowService
from app.main import app


def test_pwa_capture_can_complete_the_full_mcp_review_workflow(tmp_path: Path) -> None:
    database_path = tmp_path / "cross-surface-contentops.db"
    application_service = ContentWorkflowService(SQLiteContentRepository(database_path))
    app.dependency_overrides[get_content_workflow_service] = lambda: application_service
    mcp_process: subprocess.Popen[str] | None = None

    try:
        with TestClient(app) as application_client:
            capture_response = application_client.post(
                "/content-items/ideas",
                json={
                    "raw_idea": (
                        "A portfolio project becomes credible when it preserves decisions and approval state, "
                        "instead of only generating text."
                    ),
                    "idempotency_key": "pwa-cross-surface-capture",
                },
            )
            assert capture_response.status_code == 201
            content_item_id = capture_response.json()["id"]

            with socket.socket() as probe_socket:
                probe_socket.bind(("127.0.0.1", 0))
                mcp_port = probe_socket.getsockname()[1]

            environment = os.environ.copy()
            environment.update(
                {
                    "CONTENTOPS_DB_PATH": str(database_path),
                    "MCP_HOST": "127.0.0.1",
                    "MCP_PORT": str(mcp_port),
                }
            )
            mcp_process = subprocess.Popen(
                [sys.executable, "-m", "app.mcp_server", "--transport", "streamable-http"],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            async def run_host_workflow() -> tuple[str, str]:
                mcp_url = f"http://127.0.0.1:{mcp_port}/mcp"
                last_startup_error: Exception | None = None
                for _ in range(50):
                    if mcp_process is not None and mcp_process.poll() is not None:
                        stdout, stderr = mcp_process.communicate()
                        raise AssertionError(f"MCP server exited early. stdout={stdout!r} stderr={stderr!r}")
                    try:
                        async with Client(mcp_url) as probe_client:
                            await probe_client.list_tools()
                        break
                    except Exception as startup_error:  # noqa: BLE001 - retry while the local server starts
                        last_startup_error = startup_error
                        await asyncio.sleep(0.1)
                else:
                    raise AssertionError(f"MCP server did not become ready: {last_startup_error}")

                async with Client(mcp_url, raise_exceptions=True) as mcp_client:
                    listed = await mcp_client.call_tool(
                        "contentops_list_content_items",
                        {"status": "captured", "limit": 10},
                    )
                    assert listed.structured_content is not None
                    assert any(item["id"] == content_item_id for item in listed.structured_content["items"])

                    await mcp_client.call_tool(
                        "contentops_update_writing_profile",
                        {
                            "style_instructions": (
                                "Write concretely, avoid hype, and explain the engineering trade-off."
                            ),
                            "target_audience": "software engineers and technical hiring managers",
                            "language": "en",
                            "idempotency_key": "cross-surface-profile",
                        },
                    )
                    writing_context = await mcp_client.call_tool(
                        "contentops_get_writing_context",
                        {"max_examples": 5},
                    )
                    assert writing_context.structured_content is not None
                    assert "avoid hype" in writing_context.structured_content["profile"]["style_instructions"]

                    first_draft = await mcp_client.call_tool(
                        "contentops_save_draft_version",
                        {
                            "content_item_id": content_item_id,
                            "body": (
                                "A portfolio project is not strong because it generates polished text.\n\n"
                                "It becomes credible when it preserves the source idea, revisions, feedback, and the "
                                "exact version a human approved. That workflow state is the real engineering work."
                            ),
                            "change_summary": "Initial host-written draft",
                            "idempotency_key": "cross-surface-draft-v1",
                        },
                    )
                    assert first_draft.structured_content is not None
                    first_version = first_draft.structured_content["versions"][-1]

                    feedback_result = await mcp_client.call_tool(
                        "contentops_request_changes",
                        {
                            "content_item_id": content_item_id,
                            "version_id": first_version["id"],
                            "feedback": "Add one concrete benefit for the user and make the ending less abstract.",
                            "idempotency_key": "cross-surface-feedback-v1",
                        },
                    )
                    assert feedback_result.structured_content is not None
                    assert feedback_result.structured_content["status"] == "changes_requested"

                    revised_draft = await mcp_client.call_tool(
                        "contentops_save_draft_version",
                        {
                            "content_item_id": content_item_id,
                            "body": (
                                "A portfolio project is not strong because it generates polished text.\n\n"
                                "It becomes credible when it preserves the source idea, revisions, feedback, and the "
                                "exact version a human approved. You can resume the work from ChatGPT, Codex, or the "
                                "web app without losing context or approving stale copy."
                            ),
                            "change_summary": "Added the cross-client user benefit",
                            "idempotency_key": "cross-surface-draft-v2",
                        },
                    )
                    assert revised_draft.structured_content is not None
                    current_version = revised_draft.structured_content["versions"][-1]

                    approved = await mcp_client.call_tool(
                        "contentops_approve_draft",
                        {
                            "content_item_id": content_item_id,
                            "version_id": current_version["id"],
                            "expected_content_hash": current_version["content_hash"],
                            "idempotency_key": "cross-surface-approval-v2",
                        },
                    )
                    assert approved.structured_content is not None
                    assert approved.structured_content["status"] == "approved"
                    return current_version["id"], current_version["content_hash"]

            approved_version_id, approved_hash = asyncio.run(run_host_workflow())

            final_response = application_client.get(f"/content-items/{content_item_id}")
            assert final_response.status_code == 200
            final_item = final_response.json()
            assert final_item["status"] == "approved"
            assert len(final_item["versions"]) == 2
            assert len(final_item["feedback"]) == 1
            assert final_item["active_approval"]["version_id"] == approved_version_id
            assert final_item["active_approval"]["content_hash"] == approved_hash
    finally:
        if mcp_process is not None:
            mcp_process.terminate()
            try:
                mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mcp_process.kill()
                mcp_process.wait(timeout=5)
        app.dependency_overrides.clear()
