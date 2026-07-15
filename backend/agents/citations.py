import json
from typing import Any

from agents import RunItem
from agents.items import ToolCallItem, ToolCallOutputItem

from backend.agents.tools import RETRIEVE_TOOL_NAME


def _parse_chunks(output: Any) -> list[dict]:
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(output, list):
        return []
    return [c for c in output if isinstance(c, dict)]


def _to_citation(chunk: dict) -> dict:
    return {
        "document_id": chunk.get("document_id"),
        "filename": chunk.get("filename"),
        "chunk_index": chunk.get("chunk_index"),
        "text_snippet": chunk.get("text", ""),
    }


def _dedupe(citations: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for c in citations:
        key = (c.get("document_id"), c.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        result.append(c)
    return result


def extract_citations(new_items: list[RunItem]) -> list[dict]:
    """Pull citations out of a live RunResult.new_items list (this turn's tool calls only)."""
    retrieve_call_ids = {
        item.call_id
        for item in new_items
        if isinstance(item, ToolCallItem) and item.tool_name == RETRIEVE_TOOL_NAME
    }
    citations: list[dict] = []
    for item in new_items:
        if isinstance(item, ToolCallOutputItem) and item.call_id in retrieve_call_ids:
            citations.extend(_to_citation(c) for c in _parse_chunks(item.output))
    return _dedupe(citations)


def replay_history(items: list[dict]) -> list[dict]:
    """Rebuild displayable chat history from raw SDK session items (TResponseInputItem dicts)."""
    retrieve_call_ids: set[str] = set()
    citations_by_call_id: dict[str, list[dict]] = {}

    for item in items:
        if item.get("type") == "function_call" and item.get("name") == RETRIEVE_TOOL_NAME:
            call_id = item.get("call_id")
            if call_id:
                retrieve_call_ids.add(call_id)
        elif item.get("type") == "function_call_output":
            call_id = item.get("call_id")
            if call_id in retrieve_call_ids:
                chunks = _parse_chunks(item.get("output"))
                citations_by_call_id[call_id] = [_to_citation(c) for c in chunks]

    pending_citations: list[dict] = []
    messages: list[dict] = []

    for item in items:
        item_type = item.get("type")
        if item_type == "function_call_output":
            call_id = item.get("call_id")
            if call_id in citations_by_call_id:
                pending_citations.extend(citations_by_call_id[call_id])
            continue

        role = item.get("role")
        if role not in ("user", "assistant"):
            continue

        content = item.get("content")
        text = _extract_text(content)
        if not text:
            continue

        message = {"role": role, "content": text, "citations": []}
        if role == "assistant" and pending_citations:
            message["citations"] = _dedupe(pending_citations)
            pending_citations = []
        messages.append(message)

    return messages


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""
