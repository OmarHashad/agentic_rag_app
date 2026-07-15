import json

import pytest
from agents.tool_context import ToolContext

from backend.agents.context import AgentContext
from backend.agents.tools import retrieve_documents
from backend.rag.vector_store import upsert_chunks
from tests.factories import fixed_vector


def _seed_owner_chunk(owner_sub: str, document_id: int, text: str, seed: float):
    upsert_chunks(
        document_id=document_id,
        owner_sub=owner_sub,
        filename=f"{owner_sub}.pdf",
        chunks=[text],
        vectors=[fixed_vector(seed)],
    )


async def _call_tool(owner_sub: str, query: str, monkeypatch, embed_seed: float):
    monkeypatch.setattr(
        "backend.agents.tools.embed_one", lambda text: fixed_vector(embed_seed)
    )
    args = json.dumps({"query": query})
    ctx = ToolContext(
        context=AgentContext(owner_sub=owner_sub),
        tool_name="retrieve_documents",
        tool_call_id="test-call-id",
        tool_arguments=args,
    )
    raw = await retrieve_documents.on_invoke_tool(ctx, args)
    return json.loads(raw)


@pytest.mark.asyncio
async def test_owner_filter_is_applied_inside_the_query(monkeypatch):
    _seed_owner_chunk("owner-a", document_id=101, text="owner a secret content", seed=0.5)
    _seed_owner_chunk("owner-b", document_id=102, text="owner b secret content", seed=0.5)

    results = await _call_tool("owner-a", "secret content", monkeypatch, embed_seed=0.5)

    assert len(results) >= 1
    assert all(r["document_id"] == 101 for r in results)


@pytest.mark.asyncio
async def test_low_score_chunks_are_filtered_out(monkeypatch):
    _seed_owner_chunk("owner-c", document_id=201, text="closely matching chunk", seed=0.5)

    # Query embedding far from the stored vector -> low cosine similarity -> filtered
    results = await _call_tool("owner-c", "unrelated query", monkeypatch, embed_seed=-0.9)

    assert results == []


@pytest.mark.asyncio
async def test_no_documents_for_owner_returns_empty(monkeypatch):
    results = await _call_tool("owner-with-nothing", "anything", monkeypatch, embed_seed=0.5)

    assert results == []
