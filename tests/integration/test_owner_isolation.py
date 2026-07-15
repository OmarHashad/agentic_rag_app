"""The multi-tenant boundary: user B must never read, search, or chat over
user A's data. This is the highest-value test class in the suite."""

from tests.factories import fixed_vector, make_document


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _whoami(client, token):
    return client.get("/me", headers=auth_header(token)).json()


def _db():
    from backend.db.session import SessionLocal

    return SessionLocal()


def test_user_b_cannot_list_or_read_user_a_document(client, token_a, token_b):
    user_a = _whoami(client, token_a)

    db = _db()
    try:
        doc = make_document(db, owner_sub=user_a["sub"], filename="a-private.pdf")
    finally:
        db.close()

    # Not present in B's document list
    docs_b = client.get("/documents", headers=auth_header(token_b)).json()
    assert all(d["filename"] != "a-private.pdf" for d in docs_b)

    # Direct access by id is a 404, not a 403 (don't even confirm it exists)
    resp = client.get(f"/documents/{doc.id}/status", headers=auth_header(token_b))
    assert resp.status_code == 404

    resp = client.get(f"/documents/{doc.id}/download", headers=auth_header(token_b))
    assert resp.status_code == 404

    resp = client.delete(f"/documents/{doc.id}", headers=auth_header(token_b))
    assert resp.status_code == 404

    # It's still there for A
    resp = client.get(f"/documents/{doc.id}/status", headers=auth_header(token_a))
    assert resp.status_code == 200


def test_user_b_search_never_returns_user_a_chunks(client, token_a, token_b, monkeypatch):
    from backend.rag.vector_store import upsert_chunks

    user_a = _whoami(client, token_a)
    upsert_chunks(
        document_id=5001,
        owner_sub=user_a["sub"],
        filename="a-secret.pdf",
        chunks=["the confidential figure is 42"],
        vectors=[fixed_vector(0.5)],
    )

    monkeypatch.setattr(
        "backend.api.v1.endpoints.search.embed_one", lambda text: fixed_vector(0.5)
    )

    results_a = client.get(
        "/search", params={"q": "confidential figure"}, headers=auth_header(token_a)
    ).json()
    assert any(r["document_id"] == 5001 for r in results_a)

    results_b = client.get(
        "/search", params={"q": "confidential figure"}, headers=auth_header(token_b)
    ).json()
    assert all(r["document_id"] != 5001 for r in results_b)
    assert results_b == []


def test_user_b_cannot_see_or_use_user_a_thread(client, token_a, token_b):
    thread = client.post(
        "/threads", json={"title": "A's private thread"}, headers=auth_header(token_a)
    ).json()

    threads_b = client.get("/threads", headers=auth_header(token_b)).json()
    assert all(t["id"] != thread["id"] for t in threads_b)

    resp = client.get(f"/threads/{thread['id']}/messages", headers=auth_header(token_b))
    assert resp.status_code == 404

    resp = client.post(
        f"/threads/{thread['id']}/chat",
        json={"message": "what's in your documents?"},
        headers=auth_header(token_b),
    )
    assert resp.status_code == 404
