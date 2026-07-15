import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from backend.core.config import AGENT_SESSION_DATABASE_URL

load_dotenv(Path(__file__).parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


ASYNC_DATABASE_URL = AGENT_SESSION_DATABASE_URL or _to_asyncpg_url(DATABASE_URL)

# NullPool: each checkout opens a fresh asyncpg connection rather than reusing a
# pooled one tied to a previous event loop (asyncpg connections are bound to the
# loop that created them — pooling across loop boundaries crashes).
async_engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
