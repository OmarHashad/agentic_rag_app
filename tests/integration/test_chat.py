import json

import pytest
from agents import RawResponsesStreamEvent, RunItemStreamEvent
from agents.items import ToolCallItem


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class _FakeAgent:
    """A plain object with a real __weakref__ slot, since ToolCallItem weak-references
    the agent that produced it."""


class _FakeTextDelta:
    def __init__(self, delta):
        self.type = "response.output_text.delta"
        self.delta = delta


class _FakeResultStreaming:
    """Stands in for RunResultStreaming so tests never call OpenRouter. Mimics the one
    real side effect tests rely on: persisting turns into the session once the stream
    is fully drained (the same guarantee the real SDK provides)."""

    def __init__(self, final_output, session=None, message=None, new_items=None):
        self.final_output = final_output
        self.new_items = new_items or []
        self._session = session
        self._message = message

    async def stream_events(self):
        yield RunItemStreamEvent(
            name="tool_called",
            item=ToolCallItem(
                agent=_FakeAgent(), raw_item={"name": "retrieve_documents", "call_id": "call-1"}
            ),
        )
        yield RawResponsesStreamEvent(data=_FakeTextDelta("This is "))
        yield RawResponsesStreamEvent(data=_FakeTextDelta("a fake grounded answer."))
        yield RunItemStreamEvent(name="tool_output", item={"call_id": "call-1"})

        if self._session is not None:
            await self._session.add_items(
                [
                    {"role": "user", "content": self._message},
                    {"role": "assistant", "content": self.final_output},
                ]
            )


class _FakeRunner:
    @classmethod
    def run_streamed(cls, agent, message, context=None, session=None, **kwargs):
        return _FakeResultStreaming(
            final_output="This is a fake grounded answer.", session=session, message=message
        )


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setattr("backend.agents.streaming.Runner", _FakeRunner)


def _drain_sse(client, thread_id, turn_id, token):
    resp = client.get(
        f"/threads/{thread_id}/turns/{turn_id}/stream", headers=auth_header(token)
    )
    assert resp.status_code == 200
    events = []
    for block in resp.text.split("\n\n"):
        if not block.strip():
            continue
        event_type, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        if event_type:
            events.append((event_type, data))
    return events


def test_chat_404s_for_nonexistent_thread(client, token_a):
    resp = client.post(
        "/threads/999999/chat", json={"message": "hi"}, headers=auth_header(token_a)
    )
    assert resp.status_code == 404


def test_messages_404s_for_nonexistent_thread(client, token_a):
    resp = client.get("/threads/999999/messages", headers=auth_header(token_a))
    assert resp.status_code == 404


def test_active_turn_404s_for_nonexistent_thread(client, token_a):
    resp = client.get("/threads/999999/active-turn", headers=auth_header(token_a))
    assert resp.status_code == 404


def test_stream_404s_for_unknown_turn_id(client, token_a):
    thread = client.post("/threads", json={"title": "T"}, headers=auth_header(token_a)).json()
    resp = client.get(
        f"/threads/{thread['id']}/turns/does-not-exist/stream", headers=auth_header(token_a)
    )
    assert resp.status_code == 404


def test_chat_returns_turn_id_immediately(client, token_a):
    thread = client.post("/threads", json={"title": "T"}, headers=auth_header(token_a)).json()

    resp = client.post(
        f"/threads/{thread['id']}/chat",
        json={"message": "hello"},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 202
    assert "turn_id" in resp.json()


def test_active_turn_reports_the_turn_while_in_flight(client, token_a):
    thread = client.post("/threads", json={"title": "T"}, headers=auth_header(token_a)).json()

    turn = client.post(
        f"/threads/{thread['id']}/chat",
        json={"message": "hello"},
        headers=auth_header(token_a),
    ).json()

    active = client.get(
        f"/threads/{thread['id']}/active-turn", headers=auth_header(token_a)
    ).json()
    assert active["turn_id"] == turn["turn_id"]

    # Draining the stream lets the background turn run to completion, which clears
    # the active-turn marker (same as it would once the real run finishes).
    _drain_sse(client, thread["id"], turn["turn_id"], token_a)

    active_after = client.get(
        f"/threads/{thread['id']}/active-turn", headers=auth_header(token_a)
    ).json()
    assert active_after["turn_id"] is None


def test_stream_delivers_deltas_and_a_terminal_turn_complete_event(client, token_a):
    thread = client.post("/threads", json={"title": "T"}, headers=auth_header(token_a)).json()

    turn = client.post(
        f"/threads/{thread['id']}/chat",
        json={"message": "hello"},
        headers=auth_header(token_a),
    ).json()

    events = _drain_sse(client, thread["id"], turn["turn_id"], token_a)

    types = [e[0] for e in events]
    assert "text_delta" in types
    assert "tool_call_started" in types
    assert types[-1] == "turn_complete"

    complete_data = events[-1][1]
    assert complete_data["answer"] == "This is a fake grounded answer."
    assert complete_data["citations"] == []


def test_message_history_persists_and_replays_after_a_chat_turn(client, token_a):
    thread = client.post("/threads", json={"title": "T"}, headers=auth_header(token_a)).json()

    turn = client.post(
        f"/threads/{thread['id']}/chat",
        json={"message": "hello there"},
        headers=auth_header(token_a),
    ).json()
    _drain_sse(client, thread["id"], turn["turn_id"], token_a)

    history = client.get(
        f"/threads/{thread['id']}/messages", headers=auth_header(token_a)
    ).json()

    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "hello there"
    assert history[1]["content"] == "This is a fake grounded answer."
