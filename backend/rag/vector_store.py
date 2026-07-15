import uuid
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
)

from backend.core.config import QDRANT_URL, QDRANT_COLLECTION, EMBEDDING_DIM

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def ensure_collection() -> None:
    client = _get_client()
    existing = {c.name: c for c in client.get_collections().collections}
    if QDRANT_COLLECTION in existing:
        info = client.get_collection(QDRANT_COLLECTION)
        if info.config.params.vectors.size != EMBEDDING_DIM:
            # Dim mismatch (e.g. switched from local 384 to API 1536) — recreate
            client.delete_collection(QDRANT_COLLECTION)
        else:
            return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def _point_id(document_id: int, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{document_id}_{chunk_index}"))


def upsert_chunks(
    document_id: int,
    owner_sub: str,
    filename: str,
    chunks: List[str],
    vectors: List[List[float]],
) -> None:
    client = _get_client()
    points = [
        PointStruct(
            id=_point_id(document_id, i),
            vector=vectors[i],
            payload={
                "owner_sub": owner_sub,
                "document_id": document_id,
                "chunk_index": i,
                "text": chunks[i],
                "filename": filename,
            },
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def delete_document(document_id: int) -> None:
    _get_client().delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        ),
    )


def search(
    query_vector: List[float],
    owner_sub: str,
    k: int = 5,
) -> List[Dict[str, Any]]:
    # Owner filter is inside the Qdrant query — never post-hoc
    results = _get_client().search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=k,
        query_filter=Filter(
            must=[FieldCondition(key="owner_sub", match=MatchValue(value=owner_sub))]
        ),
        with_payload=True,
    )
    return [
        {
            "text": r.payload["text"],
            "filename": r.payload["filename"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload["chunk_index"],
            "score": round(r.score, 4),
        }
        for r in results
    ]
