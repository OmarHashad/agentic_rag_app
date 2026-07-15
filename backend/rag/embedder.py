import httpx
from typing import List
from backend.core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_EMBEDDING_MODEL


def _call_api(texts: List[str]) -> List[List[float]]:
    response = httpx.post(
        f"{OPENROUTER_BASE_URL}/embeddings",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": OPENROUTER_EMBEDDING_MODEL, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()["data"]
    # API returns results indexed — sort by index to preserve order
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def embed(texts: List[str]) -> List[List[float]]:
    return _call_api(texts)


def embed_one(text: str) -> List[float]:
    return _call_api([text])[0]
