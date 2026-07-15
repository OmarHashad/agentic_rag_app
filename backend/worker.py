"""
Document processing worker — extracts text, chunks, embeds, upserts into Qdrant.

Run from the project root:
    .\\venv\\Scripts\\python -m backend.worker
"""

import io
import json
import logging

from pathlib import Path
from dotenv import load_dotenv

_root = Path(__file__).parent.parent
load_dotenv(_root / ".env")
load_dotenv(_root / "backend" / ".env")

from backend.core.cache import invalidate_documents
from backend.core.redis_client import get_redis
from backend.db.repository import get_document_by_id, update_document_status
from backend.db.session import SessionLocal
from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed
from backend.rag.extractor import extract_text
from backend.rag.vector_store import ensure_collection, upsert_chunks
from backend.storage.minio_client import get_minio_client
from backend.core.config import MINIO_BUCKET

QUEUE_NAME = "doc_processing_queue"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
log = logging.getLogger(__name__)

# Statuses the worker will accept for processing (includes legacy "processed" from old stub)
_PROCESSABLE = {"ready", "processed"}


def process_job(job_str: str) -> None:
    job = json.loads(job_str)
    document_id: int = job["document_id"]
    owner_sub: str = job["owner_sub"]

    db = SessionLocal()
    try:
        doc = get_document_by_id(db, document_id=document_id, owner_sub=owner_sub)
        if doc is None:
            log.warning("Document %d not found — skipping", document_id)
            return
        if doc.status == "embedded":
            log.info("Document %d already embedded — skipping", document_id)
            return
        if doc.status not in _PROCESSABLE:
            log.info("Document %d in status '%s' — skipping", document_id, doc.status)
            return

        log.info("Processing document %d (%s)", document_id, doc.filename)
        update_document_status(db, document_id, status="processing")
        invalidate_documents(owner_sub)

        # 1. Download bytes from MinIO
        minio = get_minio_client()
        response = minio.get_object(MINIO_BUCKET, doc.object_key)
        data = response.read()
        response.close()

        # 2. Extract text
        text = extract_text(data, doc.content_type)
        if not text.strip():
            log.warning("Document %d produced no text — marking failed", document_id)
            update_document_status(db, document_id, status="failed")
            invalidate_documents(owner_sub)
            return

        # 3. Chunk
        chunks = chunk_text(text)
        log.info("Document %d → %d chunks", document_id, len(chunks))

        # 4. Embed
        vectors = embed(chunks)

        # 5. Upsert into Qdrant
        ensure_collection()
        upsert_chunks(document_id, owner_sub, doc.filename, chunks, vectors)

        # 6. Mark embedded
        update_document_status(db, document_id, status="embedded")
        invalidate_documents(owner_sub)
        log.info("Document %d embedded successfully (%d vectors)", document_id, len(chunks))

    except Exception:
        log.exception("Failed to process document %d", document_id)
        try:
            update_document_status(db, document_id, status="failed")
            invalidate_documents(owner_sub)
        except Exception:
            pass
    finally:
        db.close()


def recover_stuck_jobs() -> None:
    """On startup, re-enqueue any docs that are stuck in ready/processed/processing."""
    db = SessionLocal()
    redis = get_redis()
    try:
        from backend.db.models import Document
        stuck = (
            db.query(Document)
            .filter(Document.status.in_(list(_PROCESSABLE) + ["processing"]))
            .all()
        )
        if not stuck:
            log.info("Recovery: no stuck documents found")
            return
        for doc in stuck:
            if doc.status == "processing":
                update_document_status(db, doc.id, status="ready")
            job = json.dumps({"document_id": doc.id, "owner_sub": doc.owner_sub})
            redis.rpush(QUEUE_NAME, job)
            log.info("Recovery: re-enqueued document %d (%s, was '%s')", doc.id, doc.filename, doc.status)
    finally:
        db.close()


def main() -> None:
    recover_stuck_jobs()
    redis = get_redis()
    log.info("Worker started — listening on queue '%s'", QUEUE_NAME)
    while True:
        result = redis.blpop(QUEUE_NAME, timeout=5)
        if result is None:
            continue
        _, job_str = result
        process_job(job_str)


if __name__ == "__main__":
    main()
