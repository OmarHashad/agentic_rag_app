from agents.extensions.memory import SQLAlchemySession

from backend.db.async_session import async_engine


def get_session(thread_id: int) -> SQLAlchemySession:
    return SQLAlchemySession(str(thread_id), engine=async_engine, create_tables=True)
