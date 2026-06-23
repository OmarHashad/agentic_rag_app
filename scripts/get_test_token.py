import os
from dotenv import load_dotenv
import httpx

load_dotenv()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
TOKEN_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

login_data = {
    "grant_type": "password",
    "client_id": "agentic-rag-frontend",
    "username": "testuser1",
    "password": "test123"
}

token_response = httpx.post(TOKEN_URL, data=login_data)
print(token_response.json())
