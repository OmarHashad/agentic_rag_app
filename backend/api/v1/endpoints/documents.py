import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from minio import Minio
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.auth import verify_token
from backend.core.config import MINIO_BUCKET
from backend.db import repository as db_repo
from backend.db.session import get_db
from backend.storage import repository as storage_repo
from backend.storage.minio_client import get_minio_client

router = APIRouter(prefix="/documents", tags=["documents"])
security = HTTPBearer()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    size: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PresignRequest(BaseModel):
    filename: str
    content_type: str


class PresignResponse(BaseModel):
    document_id: int
    upload_url: str


def get_current_sub(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]


def get_storage_client() -> Minio:
    return get_minio_client()


@router.post("/upload", response_model=DocumentResponse)
def upload_via_backend(
    file: UploadFile = File(...),
    owner_sub: str = Depends(get_current_sub),
    db: Session = Depends(get_db),
    storage: Minio = Depends(get_storage_client),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415, detail=f"File type not allowed: {file.content_type}"
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    object_key = f"{owner_sub}/{uuid.uuid4().hex}_{safe_filename}"

    doc = db_repo.create_document(
        db,
        owner_sub=owner_sub,
        filename=safe_filename,
        content_type=file.content_type,
        object_key=object_key,
        size=len(content),
        status="pending",
    )

    try:
        storage_repo.upload_fileobj(
            storage,
            object_key=object_key,
            data=io.BytesIO(content),
            length=len(content),
            content_type=file.content_type,
        )
    except Exception:
        db_repo.update_document_status(db, doc.id, status="failed")
        raise HTTPException(status_code=500, detail="Storage upload failed")

    return db_repo.update_document_status(db, doc.id, status="ready")


@router.post("/presign", response_model=PresignResponse)
def request_presigned_upload(
    body: PresignRequest,
    owner_sub: str = Depends(get_current_sub),
    db: Session = Depends(get_db),
    storage: Minio = Depends(get_storage_client),
):
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415, detail=f"File type not allowed: {body.content_type}"
        )

    safe_filename = body.filename.replace("/", "_").replace("\\", "_")
    object_key = f"{owner_sub}/{uuid.uuid4().hex}_{safe_filename}"

    doc = db_repo.create_document(
        db,
        owner_sub=owner_sub,
        filename=safe_filename,
        content_type=body.content_type,
        object_key=object_key,
        status="pending",
    )

    upload_url = storage_repo.get_presigned_upload_url(storage, object_key=object_key)
    return {"document_id": doc.id, "upload_url": upload_url}


@router.post("/{document_id}/confirm", response_model=DocumentResponse)
def confirm_upload(
    document_id: int,
    owner_sub: str = Depends(get_current_sub),
    db: Session = Depends(get_db),
    storage: Minio = Depends(get_storage_client),
):
    doc = db_repo.get_document_by_id(db, document_id=document_id, owner_sub=owner_sub)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "pending":
        raise HTTPException(status_code=409, detail="Document already confirmed")

    if not storage_repo.object_exists(storage, doc.object_key):
        raise HTTPException(
            status_code=422, detail="File not found in storage — upload it first"
        )

    meta = storage_repo.get_object_metadata(storage, doc.object_key)

    if meta.size > MAX_FILE_SIZE:
        storage.remove_object(MINIO_BUCKET, doc.object_key)
        db_repo.update_document_status(db, doc.id, status="failed")
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    return db_repo.update_document_status(db, doc.id, status="ready", size=meta.size)


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    owner_sub: str = Depends(get_current_sub),
    db: Session = Depends(get_db),
):
    return db_repo.get_user_documents(db, owner_sub=owner_sub)


@router.get("/{document_id}/download")
def get_download_url(
    document_id: int,
    owner_sub: str = Depends(get_current_sub),
    db: Session = Depends(get_db),
    storage: Minio = Depends(get_storage_client),
):
    doc = db_repo.get_document_by_id(db, document_id=document_id, owner_sub=owner_sub)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    url = storage_repo.get_presigned_download_url(storage, object_key=doc.object_key)
    return {"url": url}
