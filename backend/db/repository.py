from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.db.models import User, Thread, Document


def get_or_create_user(db: Session, sub: str, email: str | None = None) -> User:
    user = db.query(User).filter(User.sub == sub).first()
    if user is None:
        user = User(sub=sub, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_thread(db: Session, user_id: int, title: str | None = None) -> Thread:
    thread = Thread(user_id=user_id, title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def get_user_threads(db: Session, user_id: int) -> list[Thread]:
    return db.query(Thread).filter(Thread.user_id == user_id).order_by(Thread.created_at.desc()).all()


def get_thread(db: Session, thread_id: int, user_id: int) -> Optional[Thread]:
    return (
        db.query(Thread)
        .filter(Thread.id == thread_id, Thread.user_id == user_id)
        .first()
    )


def create_document(
    db: Session,
    owner_sub: str,
    filename: str,
    content_type: str,
    object_key: str,
    size: Optional[int] = None,
    status: str = "pending",
) -> Document:
    doc = Document(
        owner_sub=owner_sub,
        filename=filename,
        content_type=content_type,
        object_key=object_key,
        size=size,
        status=status,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document_status(
    db: Session, document_id: int, status: str, size: Optional[int] = None
) -> Optional[Document]:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        return None
    doc.status = status
    if size is not None:
        doc.size = size
    db.commit()
    db.refresh(doc)
    return doc


_VISIBLE_STATUSES = ("ready", "processing", "embedded", "failed")


def get_user_documents(db: Session, owner_sub: str) -> List[Document]:
    return (
        db.query(Document)
        .filter(Document.owner_sub == owner_sub, Document.status.in_(_VISIBLE_STATUSES))
        .order_by(Document.created_at.desc())
        .all()
    )


def get_document_by_id(
    db: Session, document_id: int, owner_sub: str
) -> Optional[Document]:
    return (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_sub == owner_sub)
        .first()
    )


def delete_document(db: Session, document_id: int, owner_sub: str) -> None:
    db.query(Document).filter(
        Document.id == document_id, Document.owner_sub == owner_sub
    ).delete()
    db.commit()
