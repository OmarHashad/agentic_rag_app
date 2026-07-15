"""
Test environment setup. This module MUST set env vars before any `backend.*`
import happens anywhere in the test session, because backend/core/auth.py fetches
JWKS at import time and backend/db/session.py + backend/db/async_session.py bind
their engines to DATABASE_URL at import time.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

os.environ["DATABASE_URL"] = "postgresql://app_user:app_password@localhost:5432/agentic_rag_test"
os.environ["MINIO_BUCKET"] = "test-documents"
os.environ["QDRANT_COLLECTION"] = "test_documents"

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from qdrant_client.models import FilterSelector, Filter as QdrantFilter
from sqlalchemy import create_engine, text

KEYCLOAK_URL = "http://localhost:8080"
KEYCLOAK_REALM = "agentic-rag-realm"
CLIENT_ID = "agentic-rag-frontend"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"

USER_A = ("pytest-user-a", "pytest-pass-a")
USER_B = ("pytest-user-b", "pytest-pass-b")


def _kc_request(method, url, data=None, headers=None):
    headers = headers or {}
    body = None
    if data is not None:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()


def _kc_admin_token():
    status, data = _kc_request(
        "POST",
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200:
        raise RuntimeError(f"Failed to get Keycloak admin token: {status} {data}")
    return data["access_token"]


def _kc_ensure_user(admin_token, username, password):
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    status, users = _kc_request(
        "GET",
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users?username={username}&exact=true",
        headers=headers,
    )
    if status == 200 and users:
        return
    body = {
        "username": username,
        "email": f"{username}@example.com",
        "firstName": username,
        "lastName": "User",
        "enabled": True,
        "emailVerified": True,
        "requiredActions": [],
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    status, data = _kc_request(
        "POST",
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
        data=body,
        headers=headers,
    )
    if status not in (201, 204):
        raise RuntimeError(f"Failed to create Keycloak user '{username}': {status} {data}")


def _kc_password_grant_token(username, password):
    status, data = _kc_request(
        "POST",
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200:
        raise RuntimeError(f"Failed to get token for '{username}': {status} {data}")
    return data["access_token"]


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """Create the isolated test database (on the same Postgres container) if missing,
    then create all sync-model tables in it."""
    admin_url = "postgresql://app_user:app_password@localhost:5432/agentic_rag"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'agentic_rag_test'")
        ).first()
        if not exists:
            conn.execute(text("CREATE DATABASE agentic_rag_test"))
    admin_engine.dispose()

    from backend.db.base import Base
    from backend.db import models  # noqa: F401 — populate Base.metadata
    from backend.db.session import engine

    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def _keycloak_users():
    admin_token = _kc_admin_token()
    _kc_ensure_user(admin_token, *USER_A)
    _kc_ensure_user(admin_token, *USER_B)


@pytest.fixture(scope="session")
def token_a():
    return _kc_password_grant_token(*USER_A)


@pytest.fixture(scope="session")
def token_b():
    return _kc_password_grant_token(*USER_B)


@pytest.fixture(scope="session", autouse=True)
def _qdrant_test_collection():
    from backend.rag.vector_store import ensure_collection

    ensure_collection()


@pytest.fixture(scope="session", autouse=True)
def _minio_test_bucket():
    from backend.storage.minio_client import ensure_bucket_exists, get_minio_client

    ensure_bucket_exists(get_minio_client())


@pytest.fixture(autouse=True)
def _clean_state():
    """Wipe Postgres tables, Qdrant points, and Redis cache before every test so
    tests are isolated regardless of which connection (API, worker) wrote data."""
    from backend.db.session import engine
    from backend.core.redis_client import get_redis
    from backend.rag.vector_store import _get_client
    from backend.core.config import QDRANT_COLLECTION

    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE users, threads, documents RESTART IDENTITY CASCADE"
            )
        )
        # agent_sessions/agent_messages are created lazily by the SDK; truncate if present.
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_sessions'"
            )
        ).first()
        if exists:
            conn.execute(text("TRUNCATE agent_sessions, agent_messages RESTART IDENTITY CASCADE"))
        conn.commit()

    get_redis().flushdb()

    client = _get_client()
    try:
        client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=FilterSelector(filter=QdrantFilter(must=[])),
        )
    except Exception:
        pass

    yield


@pytest.fixture
def client():
    from backend.main import app

    with TestClient(app) as c:
        yield c
