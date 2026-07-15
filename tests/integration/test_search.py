from tests.factories import fixed_vector


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_empty_query_short_circuits_without_calling_embed(client, token_a, monkeypatch):
    called = {"count": 0}

    def _fail_if_called(text):
        called["count"] += 1
        raise AssertionError("embed_one should not be called for a whitespace-only query")

    monkeypatch.setattr("backend.api.v1.endpoints.search.embed_one", _fail_if_called)

    resp = client.get("/search", params={"q": "   "}, headers=auth_header(token_a))
    assert resp.status_code == 200
    assert resp.json() == []
    assert called["count"] == 0


def test_search_with_no_matching_documents_returns_empty_list(client, token_a, monkeypatch):
    monkeypatch.setattr(
        "backend.api.v1.endpoints.search.embed_one", lambda text: fixed_vector(0.7)
    )

    resp = client.get("/search", params={"q": "anything at all"}, headers=auth_header(token_a))
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_returns_owner_scoped_results(client, token_a, monkeypatch):
    from backend.rag.vector_store import upsert_chunks

    user = client.get("/me", headers=auth_header(token_a)).json()
    upsert_chunks(
        document_id=7001,
        owner_sub=user["sub"],
        filename="findable.pdf",
        chunks=["the launch code is 99"],
        vectors=[fixed_vector(0.6)],
    )
    monkeypatch.setattr(
        "backend.api.v1.endpoints.search.embed_one", lambda text: fixed_vector(0.6)
    )

    resp = client.get("/search", params={"q": "launch code"}, headers=auth_header(token_a))
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["filename"] == "findable.pdf"
    assert results[0]["document_id"] == 7001
