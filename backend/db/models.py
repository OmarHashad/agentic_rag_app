from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    sub = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    threads = relationship("Thread", back_populates="user")


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="threads")
