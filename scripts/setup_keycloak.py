"""
Configure Keycloak with the realm and client needed for agentic-rag-app.
Run this after 'docker compose up -d' and once Keycloak is healthy at http://localhost:8080.

Usage:
    python scripts/setup_keycloak.py [--create-user <username> <password>]
"""

import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse

KEYCLOAK_URL = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"
REALM = "agentic-rag-realm"
CLIENT_ID = "agentic-rag-frontend"


def request(method, url, data=None, headers=None):
    headers = headers or {}
    body = None
    if data is not None:
        if isinstance(data, dict) and headers.get("Content-Type") == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body_json = json.loads(raw)
        except Exception:
            body_json = raw.decode()
        return e.code, body_json


def wait_for_keycloak(timeout=120):
    print(f"Waiting for Keycloak at {KEYCLOAK_URL} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # /health/ready is only available when --health-enabled=true; use master realm as probe
            with urllib.request.urlopen(f"{KEYCLOAK_URL}/realms/master", timeout=3) as r:
                if r.status == 200:
                    print("Keycloak is ready.", flush=True)
                    return True
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"Keycloak did not become ready within {timeout}s")


def get_admin_token():
    status, data = request(
        "POST",
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": ADMIN_USER, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200:
        raise RuntimeError(f"Failed to get admin token: {status} {data}")
    return data["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_realm(token):
    status, _ = request("GET", f"{KEYCLOAK_URL}/admin/realms/{REALM}", headers=auth_headers(token))
    if status == 200:
        print(f"Realm '{REALM}' already exists — skipping creation.", flush=True)
        return
    realm_body = {
        "realm": REALM,
        "enabled": True,
        "displayName": "Agentic RAG",
        "registrationAllowed": False,
        "resetPasswordAllowed": True,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
    }
    status, data = request("POST", f"{KEYCLOAK_URL}/admin/realms", data=realm_body, headers=auth_headers(token))
    if status not in (201, 204):
        raise RuntimeError(f"Failed to create realm: {status} {data}")
    print(f"Realm '{REALM}' created.", flush=True)


def create_client(token):
    status, clients = request(
        "GET",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}",
        headers=auth_headers(token),
    )
    if status == 200 and clients:
        print(f"Client '{CLIENT_ID}' already exists — skipping creation.", flush=True)
        return
    client_body = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "publicClient": True,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "redirectUris": ["http://localhost:5173/*", "http://localhost:5173"],
        "webOrigins": ["http://localhost:5173"],
        "attributes": {},
    }
    status, data = request(
        "POST",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients",
        data=client_body,
        headers=auth_headers(token),
    )
    if status not in (201, 204):
        raise RuntimeError(f"Failed to create client: {status} {data}")
    print(f"Client '{CLIENT_ID}' created.", flush=True)


def create_user(token, username, password):
    status, users = request(
        "GET",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?username={username}&exact=true",
        headers=auth_headers(token),
    )
    if status == 200 and users:
        print(f"User '{username}' already exists — skipping creation.", flush=True)
        return
    user_body = {
        "username": username,
        "email": f"{username}@example.com",
        "firstName": username.capitalize(),
        "lastName": "User",
        "enabled": True,
        "emailVerified": True,
        "requiredActions": [],
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    status, data = request(
        "POST",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users",
        data=user_body,
        headers=auth_headers(token),
    )
    if status not in (201, 204):
        raise RuntimeError(f"Failed to create user '{username}': {status} {data}")
    print(f"User '{username}' created with password '{password}'.", flush=True)


def main():
    create_user_args = None
    args = sys.argv[1:]
    if "--create-user" in args:
        idx = args.index("--create-user")
        if len(args) < idx + 3:
            print("Usage: --create-user <username> <password>")
            sys.exit(1)
        create_user_args = (args[idx + 1], args[idx + 2])

    wait_for_keycloak()
    token = get_admin_token()
    create_realm(token)
    # Re-auth after realm creation (token still valid for master realm ops)
    token = get_admin_token()
    create_client(token)

    if create_user_args:
        create_user(token, *create_user_args)

    print("\nKeycloak setup complete.")
    print(f"  Realm:     {REALM}")
    print(f"  Client:    {CLIENT_ID}")
    print(f"  Admin UI:  {KEYCLOAK_URL}/admin  (admin / admin)")
    if create_user_args:
        print(f"  Test user: {create_user_args[0]} / {create_user_args[1]}")


if __name__ == "__main__":
    main()
