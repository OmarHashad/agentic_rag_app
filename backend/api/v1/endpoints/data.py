from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.core.auth import verify_token

router = APIRouter()
security = HTTPBearer()


@router.get("/public-data")
def public_data():
    return {"message": "This is public, anyone can see it."}


@router.get("/protected-data")
def protected_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": f"Hello {payload['preferred_username']}, this is protected data."}
