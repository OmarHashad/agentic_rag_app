import os
from dotenv import load_dotenv
import httpx
from jose import jwt

load_dotenv()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")

JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

jwks_response = httpx.get(JWKS_URL)
jwks = jwks_response.json()


def verify_token(token):
    try:
        payload = jwt.decode(token, jwks, algorithms=["RS256"], audience="account")
        return payload
    except jwt.JWTError:
        print("Token verification failed!")
        return None
