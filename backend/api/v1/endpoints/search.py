from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.core.auth import verify_token
from backend.rag.embedder import embed_one
from backend.rag.vector_store import search

router = APIRouter(prefix="/search", tags=["search"])
security = HTTPBearer()


class SearchResult(BaseModel):
    text: str
    filename: str
    document_id: int
    chunk_index: int
    score: float


def get_current_sub(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]


@router.get("", response_model=List[SearchResult])
def semantic_search(
    q: str = Query(..., min_length=1, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Number of results"),
    owner_sub: str = Depends(get_current_sub),
):
    if not q.strip():
        return []

    query_vector = embed_one(q.strip())
    results = search(query_vector, owner_sub=owner_sub, k=k)
    return results
