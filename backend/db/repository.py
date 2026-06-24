from __future__ import annotations

from sqlalchemy.orm import Session
from backend.db.models import User, Thread


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
