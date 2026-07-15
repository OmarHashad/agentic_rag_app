from typing import List


def chunk_text(text: str, size: int = 512, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping character-level chunks.

    size=512, overlap=100:
    - ~100-130 words per chunk — enough context without being too broad
    - 100-char overlap prevents losing meaning at chunk boundaries
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap

    return chunks
