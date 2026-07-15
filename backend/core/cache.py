import json
from typing import Optional
from backend.core.redis_client import get_redis

_DOCS_TTL = 60        # seconds — document list cache
_PRESIGN_TTL = 3300   # seconds — 55 min (presigned URLs expire in 1h)


def _docs_key(owner_sub: str) -> str:
    return f"docs:{owner_sub}"


def _presign_key(object_key: str) -> str:
    return f"presign:{object_key}"


def get_cached_documents(owner_sub: str) -> Optional[list]:
    raw = get_redis().get(_docs_key(owner_sub))
    return json.loads(raw) if raw else None


def cache_documents(owner_sub: str, docs: list) -> None:
    get_redis().set(_docs_key(owner_sub), json.dumps(docs), ex=_DOCS_TTL)


def invalidate_documents(owner_sub: str) -> None:
    get_redis().delete(_docs_key(owner_sub))


def get_cached_presign_url(object_key: str) -> Optional[str]:
    return get_redis().get(_presign_key(object_key))


def cache_presign_url(object_key: str, url: str) -> None:
    get_redis().set(_presign_key(object_key), url, ex=_PRESIGN_TTL)
