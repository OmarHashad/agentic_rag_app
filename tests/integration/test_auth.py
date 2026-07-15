def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_me_rejects_missing_token(client):
    resp = client.get("/me")
    assert resp.status_code in (401, 403)  # HTTPBearer returns 403 with no header at all


def test_me_rejects_invalid_token(client):
    resp = client.get("/me", headers=auth_header("not-a-real-jwt"))
    assert resp.status_code == 401


def test_me_accepts_valid_token(client, token_a):
    resp = client.get("/me", headers=auth_header(token_a))
    assert resp.status_code == 200
    assert "sub" in resp.json()


def test_documents_list_rejects_invalid_token(client):
    resp = client.get("/documents", headers=auth_header("garbage"))
    assert resp.status_code == 401


def test_documents_list_accepts_valid_token(client, token_a):
    resp = client.get("/documents", headers=auth_header(token_a))
    assert resp.status_code == 200


def test_search_rejects_invalid_token(client):
    resp = client.get("/search", params={"q": "hello"}, headers=auth_header("garbage"))
    assert resp.status_code == 401


def test_search_accepts_valid_token(client, token_a, monkeypatch):
    monkeypatch.setattr(
        "backend.api.v1.endpoints.search.embed_one", lambda text: [0.1] * 1536
    )
    resp = client.get("/search", params={"q": "hello"}, headers=auth_header(token_a))
    assert resp.status_code == 200


def test_chat_rejects_invalid_token(client):
    resp = client.get("/threads/1/messages", headers=auth_header("garbage"))
    assert resp.status_code == 401


def test_chat_accepts_valid_token_but_404s_for_missing_thread(client, token_a):
    resp = client.get("/threads/999999/messages", headers=auth_header(token_a))
    assert resp.status_code == 404
