import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

BASE_DIR = Path(__file__).resolve().parents[2]

PARENT_STORE_PATH = BASE_DIR / "data" / "parent_store"
QDRANT_PATH = BASE_DIR / "data" / "qdrant"

COLLECTION_NAME = "document_child_chunks"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    # Same embedding model as indexing.py.
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"local_files_only": True},
    )


def get_qdrant_client() -> QdrantClient:
    # Local Qdrant is stored on disk inside data/qdrant.
    return QdrantClient(path=str(QDRANT_PATH))


def _extract_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def search_child_chunks(query: str, limit: int = 5) -> list[dict[str, Any]]:
    embeddings = get_embeddings()
    qdrant_client = get_qdrant_client()

    try:
        query_vector = embeddings.embed_query(query)
        response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        results: list[dict[str, Any]] = []

        for point in response.points or []:
            payload = point.payload or {}
            metadata = _extract_metadata(payload)

            results.append(
                {
                    "score": float(point.score) if point.score is not None else 0.0,
                    "source": metadata.get("source", ""),
                    "parent_id": metadata.get("parent_id", ""),
                    "child_id": metadata.get("child_id", ""),
                    "content": payload.get("page_content", ""),
                }
            )

        return results
    finally:
        qdrant_client.close()


def retrieve_parent_chunk(parent_id: str) -> dict[str, Any]:
    parent_file = PARENT_STORE_PATH / f"{parent_id}.json"

    if not parent_file.exists():
        return {
            "parent_id": parent_id,
            "source": "",
            "content": "",
        }

    with parent_file.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "parent_id": metadata.get("parent_id", parent_id),
        "source": metadata.get("source", ""),
        "content": data.get("page_content", ""),
    }


def search_with_context(query: str, limit: int = 5) -> dict[str, Any]:
    child_results = search_child_chunks(query=query, limit=limit)

    results: list[dict[str, Any]] = []
    seen_parent_ids: set[str] = set()

    for child_result in child_results:
        parent_id = child_result.get("parent_id", "")

        if not parent_id or parent_id in seen_parent_ids:
            continue

        parent_chunk = retrieve_parent_chunk(parent_id)

        results.append(
            {
                "score": child_result.get("score", 0.0),
                "source": child_result.get("source") or parent_chunk.get("source", ""),
                "parent_id": parent_chunk.get("parent_id", parent_id),
                "parent_content": parent_chunk.get("content", ""),
            }
        )
        seen_parent_ids.add(parent_id)

    return {
        "query": query,
        "results": results,
    }


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    query = "audit financier banque mondiale"
    output = search_with_context(query=query, limit=5)
    print(json.dumps(output, ensure_ascii=False, indent=2))
