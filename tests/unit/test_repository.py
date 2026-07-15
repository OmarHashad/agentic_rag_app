from tests.factories import make_document, make_thread, make_user


def _db():
    from backend.db.session import SessionLocal

    return SessionLocal()


def test_get_or_create_user_is_idempotent():
    db = _db()
    try:
        u1 = make_user(db, sub="sub-1", email="a@example.com")
        u2 = make_user(db, sub="sub-1", email="a@example.com")
        assert u1.id == u2.id
    finally:
        db.close()


def test_create_and_list_threads_scoped_to_user():
    from backend.db import repository

    db = _db()
    try:
        user = make_user(db, sub="sub-threads")
        make_thread(db, user.id, title="First")
        make_thread(db, user.id, title="Second")

        threads = repository.get_user_threads(db, user_id=user.id)
        assert {t.title for t in threads} == {"First", "Second"}
    finally:
        db.close()


def test_get_thread_returns_none_for_wrong_owner():
    from backend.db import repository

    db = _db()
    try:
        owner = make_user(db, sub="owner-sub")
        intruder = make_user(db, sub="intruder-sub")
        thread = make_thread(db, owner.id)

        assert repository.get_thread(db, thread.id, user_id=owner.id) is not None
        assert repository.get_thread(db, thread.id, user_id=intruder.id) is None
    finally:
        db.close()


def test_get_document_by_id_is_owner_scoped():
    from backend.db import repository

    db = _db()
    try:
        doc = make_document(db, owner_sub="owner-a", filename="a.pdf")

        assert repository.get_document_by_id(db, doc.id, owner_sub="owner-a") is not None
        assert repository.get_document_by_id(db, doc.id, owner_sub="owner-b") is None
    finally:
        db.close()


def test_delete_document_only_deletes_for_matching_owner():
    from backend.db import repository

    db = _db()
    try:
        doc = make_document(db, owner_sub="owner-a", filename="a.pdf")

        repository.delete_document(db, doc.id, owner_sub="owner-b")
        assert repository.get_document_by_id(db, doc.id, owner_sub="owner-a") is not None

        repository.delete_document(db, doc.id, owner_sub="owner-a")
        assert repository.get_document_by_id(db, doc.id, owner_sub="owner-a") is None
    finally:
        db.close()


def test_get_user_documents_excludes_pending():
    from backend.db import repository

    db = _db()
    try:
        make_document(db, owner_sub="owner-c", filename="pending.pdf", status="pending")
        make_document(db, owner_sub="owner-c", filename="ready.pdf", status="ready")

        docs = repository.get_user_documents(db, owner_sub="owner-c")
        filenames = {d.filename for d in docs}
        assert "ready.pdf" in filenames
        assert "pending.pdf" not in filenames
    finally:
        db.close()
