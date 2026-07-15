import json

from backend.agents.citations import replay_history


def _function_call(call_id, name="retrieve_documents"):
    return {"type": "function_call", "call_id": call_id, "name": name}


def _function_call_output(call_id, chunks):
    return {"type": "function_call_output", "call_id": call_id, "output": json.dumps(chunks)}


def _message(role, text):
    return {"role": role, "content": text}


def test_replay_history_attaches_citations_to_the_following_assistant_message():
    chunks = [
        {"document_id": 1, "filename": "a.pdf", "chunk_index": 0, "text": "hello", "score": 0.9}
    ]
    items = [
        _message("user", "what's in my docs?"),
        _function_call("call-1"),
        _function_call_output("call-1", chunks),
        _message("assistant", "Here's what I found."),
    ]

    history = replay_history(items)

    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["citations"] == [
        {"document_id": 1, "filename": "a.pdf", "chunk_index": 0, "text_snippet": "hello"}
    ]


def test_replay_history_gives_no_citations_when_no_tool_was_called():
    items = [_message("user", "hi"), _message("assistant", "hello!")]

    history = replay_history(items)

    assert history[1]["citations"] == []


def test_replay_history_ignores_output_from_unrelated_tools():
    items = [
        _message("user", "what time is it"),
        _function_call("call-1", name="get_current_time"),
        _function_call_output("call-1", [{"time": "noon"}]),
        _message("assistant", "It's noon."),
    ]

    history = replay_history(items)

    assert history[1]["citations"] == []


def test_replay_history_dedupes_repeated_chunks():
    chunk = {"document_id": 1, "filename": "a.pdf", "chunk_index": 0, "text": "hello", "score": 0.9}
    items = [
        _message("user", "q1"),
        _function_call("call-1"),
        _function_call_output("call-1", [chunk, chunk]),
        _message("assistant", "answer"),
    ]

    history = replay_history(items)

    assert len(history[1]["citations"]) == 1


def test_replay_history_handles_malformed_tool_output_gracefully():
    items = [
        _message("user", "q"),
        _function_call("call-1"),
        {"type": "function_call_output", "call_id": "call-1", "output": "not json"},
        _message("assistant", "answer"),
    ]

    history = replay_history(items)

    assert history[1]["citations"] == []
