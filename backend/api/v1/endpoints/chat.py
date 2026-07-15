import asyncio
import uuid
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.agents.citations import replay_history
from backend.agents.session import get_session
from backend.agents.streaming import active_turn_key, run_turn_streaming, stream_key
from backend.api.v1.endpoints.users import get_current_user
from backend.core.config import CHAT_ACTIVE_TURN_TTL_SECONDS, CHAT_STREAM_BLOCK_MS
from backend.core.redis_client import get_async_redis
from backend.db import repository
from backend.db.session import get_db

router = APIRouter(prefix="/threads/{thread_id}", tags=["chat"])

# Keeps references to scheduled background tasks so they aren't garbage-collected
# mid-flight (asyncio only holds a weak reference to a task once nothing else does).
_background_tasks: set[asyncio.Task] = set()


class ChatRequest(BaseModel):
    message: str


class ChatTurnResponse(BaseModel):
    turn_id: str


class ActiveTurnResponse(BaseModel):
    turn_id: Optional[str] = None


class Citation(BaseModel):
    document_id: Optional[int]
    filename: Optional[str]
    chunk_index: Optional[int]
    text_snippet: str


class ChatMessage(BaseModel):
    role: str
    content: str
    citations: List[Citation] = []


def _get_owned_thread(thread_id: int, user, db: Session):
    thread = repository.get_thread(db, thread_id=thread_id, user_id=user.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("/chat", response_model=ChatTurnResponse, status_code=202)
async def chat(
    thread_id: int,
    body: ChatRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Starts a turn in the background and returns immediately. The caller subscribes
    to GET .../turns/{turn_id}/stream to watch it; the run itself is independent of
    that connection and persists to the session when it finishes regardless."""
    _get_owned_thread(thread_id, user, db)

    turn_id = uuid.uuid4().hex
    redis = get_async_redis()
    await redis.set(active_turn_key(thread_id), turn_id, ex=CHAT_ACTIVE_TURN_TTL_SECONDS)

    task = asyncio.create_task(run_turn_streaming(thread_id, turn_id, user.sub, body.message))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ChatTurnResponse(turn_id=turn_id)


@router.get("/active-turn", response_model=ActiveTurnResponse)
async def get_active_turn(
    thread_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_thread(thread_id, user, db)

    redis = get_async_redis()
    turn_id = await redis.get(active_turn_key(thread_id))
    return ActiveTurnResponse(turn_id=turn_id)


@router.get("/turns/{turn_id}/stream")
async def stream_turn(
    thread_id: int,
    turn_id: str,
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """Pure subscriber: tails the turn's Redis Stream starting at Last-Event-ID (or the
    beginning, on a fresh connect). Never runs the agent itself, so a client dropping
    this connection has no effect on the turn's progress."""
    _get_owned_thread(thread_id, user, db)

    redis = get_async_redis()
    key = stream_key(thread_id, turn_id)
    # The stream key may not exist yet even for a just-started turn (the background
    # task hasn't published its first event). Only 404 when it's neither present nor
    # the thread's currently active turn — a genuinely bad/expired turn_id, not a race.
    if not await redis.exists(key):
        active_id = await redis.get(active_turn_key(thread_id))
        if active_id != turn_id:
            raise HTTPException(status_code=404, detail="Turn not found or expired")

    async def event_source() -> AsyncIterator[str]:
        last_id = last_event_id or "0"
        while True:
            if await request.is_disconnected():
                return

            response = await redis.xread(
                {key: last_id}, block=CHAT_STREAM_BLOCK_MS, count=50
            )
            if not response:
                continue

            _, entries = response[0]
            for entry_id, fields in entries:
                last_id = entry_id
                event_type = fields["event_type"]
                data = fields["data"]
                yield f"id: {entry_id}\nevent: {event_type}\ndata: {data}\n\n"
                if event_type in ("turn_complete", "turn_failed"):
                    return

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/messages", response_model=List[ChatMessage])
async def get_messages(
    thread_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_thread(thread_id, user, db)

    session = get_session(thread_id)
    items = await session.get_items()
    return replay_history(items)
