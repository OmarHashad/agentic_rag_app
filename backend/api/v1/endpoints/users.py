from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.core.auth import verify_token
from backend.db.session import get_db
from backend.db import repository

router = APIRouter()
security = HTTPBearer()


class UserResponse(BaseModel):
    id: int
    sub: str
    email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ThreadResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ThreadCreate(BaseModel):
    title: Optional[str] = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return repository.get_or_create_user(db, sub=payload["sub"], email=payload.get("email"))


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user


@router.post("/threads", response_model=ThreadResponse)
def create_thread(body: ThreadCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return repository.create_thread(db, user_id=user.id, title=body.title)


@router.get("/threads", response_model=List[ThreadResponse])
def list_threads(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return repository.get_user_threads(db, user_id=user.id)
