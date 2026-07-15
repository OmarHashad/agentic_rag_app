import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

OPENROUTER_AGENT_MODEL = os.getenv("OPENROUTER_AGENT_MODEL", "deepseek/deepseek-v4-pro")
AGENT_SESSION_DATABASE_URL = os.getenv("AGENT_SESSION_DATABASE_URL")
RAG_TOOL_TOP_K = int(os.getenv("RAG_TOOL_TOP_K", "5"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.4"))

CHAT_STREAM_TTL_SECONDS = int(os.getenv("CHAT_STREAM_TTL_SECONDS", "3600"))
CHAT_ACTIVE_TURN_TTL_SECONDS = int(os.getenv("CHAT_ACTIVE_TURN_TTL_SECONDS", "600"))
CHAT_STREAM_BLOCK_MS = int(os.getenv("CHAT_STREAM_BLOCK_MS", "15000"))
