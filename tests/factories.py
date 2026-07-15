"""Test data builders. Import lazily from backend so conftest's env vars are
already applied before backend.* modules bind their engines."""


def make_user(db, sub="test-sub", email=None):
    from backend.db import repository

    return repository.get_or_create_user(db, sub=sub, email=email)


def make_thread(db, user_id, title="Test thread"):
    from backend.db import repository

    return repository.create_thread(db, user_id=user_id, title=title)


def make_document(db, owner_sub, filename="doc.pdf", status="embedded", object_key=None):
    from backend.db import repository

    return repository.create_document(
        db,
        owner_sub=owner_sub,
        filename=filename,
        content_type="application/pdf",
        object_key=object_key or f"{owner_sub}/{filename}",
        size=123,
        status=status,
    )


def fixed_vector(seed: float = 0.1, dim: int = 1536) -> list[float]:
    """Deterministic fake embedding vector — no real OpenRouter call."""
    return [seed] * dim
