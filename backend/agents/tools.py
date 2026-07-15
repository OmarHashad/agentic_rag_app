import json

from agents import RunContextWrapper, function_tool

from backend.agents.context import AgentContext
from backend.core.config import RAG_TOOL_TOP_K, RAG_MIN_SCORE
from backend.rag.embedder import embed_one
from backend.rag.vector_store import search

RETRIEVE_TOOL_NAME = "retrieve_documents"


@function_tool(name_override=RETRIEVE_TOOL_NAME)
async def retrieve_documents(ctx: RunContextWrapper[AgentContext], query: str) -> str:
    """Search the user's uploaded documents for passages relevant to the query.

    Only call this when the user's question likely depends on their own documents.
    Returns a JSON array of chunks, each with text, filename, document_id, chunk_index, score.
    """
    owner_sub = ctx.context.owner_sub
    vector = embed_one(query)
    chunks = search(vector, owner_sub=owner_sub, k=RAG_TOOL_TOP_K)
    relevant = [c for c in chunks if c.get("score", 0) >= RAG_MIN_SCORE]
    return json.dumps(relevant)
