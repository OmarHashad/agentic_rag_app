from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, func
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


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    owner_sub = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=True)
    object_key = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
