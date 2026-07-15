import redis as _redis
import redis.asyncio as _redis_async
from backend.core.config import REDIS_URL

_pool = _redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)


def get_redis() -> _redis.Redis:
    return _redis.Redis(connection_pool=_pool)


def get_async_redis() -> _redis_async.Redis:
    # No shared connection pool here (unlike get_redis): asyncio connections are bound
    # to the event loop that created them, and this client gets used from different
    # loops (background chat tasks, SSE requests, tests). from_url() with no pool
    # reuse means each call gets its own connection, avoiding a cross-loop crash.
    return _redis_async.Redis.from_url(REDIS_URL, decode_responses=True)
