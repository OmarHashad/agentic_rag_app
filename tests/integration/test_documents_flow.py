import io

from tests.factories import fixed_vector


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_upload_rejects_disallowed_file_type(client, token_a):
    resp = client.post(
        "/documents/upload",
        files={"file": ("virus.exe", io.BytesIO(b"binary"), "application/x-msdownload")},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 415


def test_upload_rejects_oversized_file(client, token_a):
    big = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        "/documents/upload",
        files={"file": ("big.txt", io.BytesIO(big), "text/plain")},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 413


def test_status_and_download_404_for_missing_document(client, token_a):
    resp = client.get("/documents/999999/status", headers=auth_header(token_a))
    assert resp.status_code == 404

    resp = client.get("/documents/999999/download", headers=auth_header(token_a))
    assert resp.status_code == 404


def test_upload_then_process_job_transitions_to_embedded(client, token_a, monkeypatch):
    resp = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello world, this is a test document"), "text/plain")},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["status"] == "ready"

    status = client.get(f"/documents/{doc['id']}/status", headers=auth_header(token_a)).json()
    assert status["status"] == "ready"

    monkeypatch.setattr(
        "backend.worker.embed", lambda chunks: [fixed_vector(0.3) for _ in chunks]
    )

    import json

    from backend.worker import process_job

    user = client.get("/me", headers=auth_header(token_a)).json()
    process_job(json.dumps({"document_id": doc["id"], "owner_sub": user["sub"]}))

    status = client.get(f"/documents/{doc['id']}/status", headers=auth_header(token_a)).json()
    assert status["status"] == "embedded"


def test_process_job_marks_document_failed_when_text_extraction_is_empty(
    client, token_a, monkeypatch
):
    resp = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", io.BytesIO(b"   "), "text/plain")},
        headers=auth_header(token_a),
    )
    doc = resp.json()

    monkeypatch.setattr(
        "backend.worker.embed", lambda chunks: [fixed_vector(0.3) for _ in chunks]
    )

    import json

    from backend.worker import process_job

    user = client.get("/me", headers=auth_header(token_a)).json()
    process_job(json.dumps({"document_id": doc["id"], "owner_sub": user["sub"]}))

    status = client.get(f"/documents/{doc['id']}/status", headers=auth_header(token_a)).json()
    assert status["status"] == "failed"
