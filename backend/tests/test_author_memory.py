import asyncio

import pytest
from mcp import Client

from app.content.models import AuthorMemory, PastPost
from app.content.repository import ConflictError, SQLiteContentRepository
from app.content.service import ContentWorkflowService
from app.mcp_server import create_mcp_server


def test_memory_survives_restart_filters_examples_and_exports_every_post(tmp_path):
    path = tmp_path / "memory.db"
    service = ContentWorkflowService(SQLiteContentRepository(path))
    memory = AuthorMemory(background="Python fejlesztő vagyok.", past_posts=[
        PastPost(title="Tanulás", body="Saját tapasztalat egy projektről.", topics="Python, tanulás"),
        PastPost(title="Régi hang", body="Ezt már nem használnám mintaként.", use_as_example=False),
        PastPost(title="Munka", body="Egy második saját poszt.", topics="saját projektek"),
    ])
    saved = service.update_author_memory(memory, "memory-save-001")
    assert service.update_author_memory(memory, "memory-save-001") == saved
    with pytest.raises(ConflictError):
        service.update_author_memory(memory, "memory-stale-001")
    restarted = ContentWorkflowService(SQLiteContentRepository(path))
    context = restarted.get_writing_context(1)
    assert context.author_memory.background == memory.background
    assert [post.title for post in context.author_memory.past_posts] == ["Tanulás"]
    assert [entry["title"] for entry in context.past_post_topics] == ["Tanulás", "Munka"]
    assert len(restarted.export_workspace().author_memory.past_posts) == 3
    assert restarted.get_writing_context(0).author_memory.past_posts == []
    cleared = saved.model_copy(update={"past_posts": []})
    restarted.update_author_memory(cleared, "memory-clear-001")
    assert restarted.get_writing_context(5).past_post_topics == []


def test_mcp_reads_saved_profile_and_past_posts_before_drafting(tmp_path):
    async def scenario():
        async with Client(create_mcp_server(tmp_path / "mcp.db"), raise_exceptions=True) as client:
            await client.call_tool("contentops_update_author_memory", {
                "memory": {"background": "Saját szakmai háttér", "past_posts": [
                    {"title": "Saját poszt", "body": "Konkrét tapasztalat, rövid mondatok.", "topics": "tanulás"}
                ], "revision": "empty"}, "idempotency_key": "mcp-memory-001",
            })
            result = await client.call_tool("contentops_get_writing_context", {"max_examples": 5})
            assert result.structured_content["author_memory"]["background"] == "Saját szakmai háttér"
            assert result.structured_content["author_memory"]["past_posts"][0]["title"] == "Saját poszt"
    asyncio.run(scenario())
