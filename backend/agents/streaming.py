import json
import logging

from agents import RawResponsesStreamEvent, RunItemStreamEvent, Runner
from agents.items import ToolCallItem

from backend.agents.agent import build_agent
from backend.agents.citations import extract_citations
from backend.agents.context import AgentContext
from backend.agents.session import get_session
from backend.core.config import CHAT_STREAM_TTL_SECONDS
from backend.core.redis_client import get_async_redis

log = logging.getLogger(__name__)


def stream_key(thread_id: int, turn_id: str) -> str:
    return f"chat:stream:{thread_id}:{turn_id}"


def active_turn_key(thread_id: int) -> str:
    return f"chat:active_turn:{thread_id}"


def _event(event_type: str, data: dict) -> dict:
    return {"event_type": event_type, "data": json.dumps(data)}


async def run_turn_streaming(thread_id: int, turn_id: str, owner_sub: str, message: str) -> None:
    """Runs the agent to completion in the background, publishing normalized events to a
    per-turn Redis Stream as they happen. This coroutine is scheduled via asyncio.create_task
    and is NOT awaited by any request handler — it keeps running (and persists to the SDK
    session on completion) even if every SSE subscriber disconnects.
    """
    redis = get_async_redis()
    key = stream_key(thread_id, turn_id)

    try:
        session = get_session(thread_id)
        agent = build_agent()
        result = Runner.run_streamed(
            agent,
            message,
            context=AgentContext(owner_sub=owner_sub),
            session=session,
        )

        async for event in result.stream_events():
            if isinstance(event, RawResponsesStreamEvent):
                data = event.data
                if getattr(data, "type", None) == "response.output_text.delta":
                    await redis.xadd(key, _event("text_delta", {"delta": data.delta}))
            elif isinstance(event, RunItemStreamEvent):
                if event.name == "tool_called" and isinstance(event.item, ToolCallItem):
                    tool_name = event.item.tool_name or ""
                    await redis.xadd(key, _event("tool_call_started", {"tool_name": tool_name}))
                elif event.name == "tool_output":
                    tool_name = getattr(event.item, "tool_name", "") or ""
                    await redis.xadd(key, _event("tool_call_finished", {"tool_name": tool_name}))

        citations = extract_citations(result.new_items)
        await redis.xadd(
            key, _event("turn_complete", {"answer": result.final_output, "citations": citations})
        )
    except Exception as exc:
        log.exception("Chat turn %s on thread %s failed", turn_id, thread_id)
        await redis.xadd(key, _event("turn_failed", {"error": str(exc)}))
    finally:
        await redis.expire(key, CHAT_STREAM_TTL_SECONDS)
        await redis.delete(active_turn_key(thread_id))
