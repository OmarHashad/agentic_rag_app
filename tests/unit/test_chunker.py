from backend.rag.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_text_shorter_than_size_is_a_single_chunk():
    text = "short text"
    chunks = chunk_text(text, size=512, overlap=100)
    assert chunks == [text]


def test_chunks_overlap_by_configured_amount():
    text = "a" * 1000
    chunks = chunk_text(text, size=512, overlap=100)
    assert len(chunks) > 1
    # the tail of chunk[i] and the head of chunk[i+1] share `overlap` characters
    assert chunks[0][-100:] == chunks[1][:100]


def test_chunks_cover_the_full_text_without_gaps():
    text = "0123456789" * 100  # 1000 chars, easy to reason about by index
    chunks = chunk_text(text, size=250, overlap=50)
    # reconstruct: each chunk after the first starts `size - overlap` further in
    stride = 250 - 50
    for i, chunk in enumerate(chunks):
        start = i * stride
        assert text[start : start + 250] == chunk


def test_last_chunk_is_not_padded_beyond_text_end():
    text = "x" * 550
    chunks = chunk_text(text, size=512, overlap=100)
    assert len(chunks[-1]) <= 512
    assert chunks[-1] == text[len(text) - len(chunks[-1]) :]


def test_no_chunk_exceeds_configured_size():
    text = "y" * 2000
    chunks = chunk_text(text, size=300, overlap=50)
    assert all(len(c) <= 300 for c in chunks)
