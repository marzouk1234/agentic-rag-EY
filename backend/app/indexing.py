import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = BASE_DIR / "data" / "raw"
PARENT_STORE_PATH = BASE_DIR / "data" / "parent_store"
QDRANT_PATH = BASE_DIR / "data" / "qdrant"

COLLECTION_NAME = "document_child_chunks"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

PARENT_STORE_PATH.mkdir(parents=True, exist_ok=True)
QDRANT_PATH.mkdir(parents=True, exist_ok=True)

parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=3000,
    chunk_overlap=300,
)

child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)


def build_raw_pdf_lookup() -> dict[str, str]:
    return {
        path.stem.casefold(): path.name
        for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    }


def write_parent_document(parent_file: Path, parent_doc: Document) -> None:
    with parent_file.open("w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "page_content": parent_doc.page_content,
                "metadata": parent_doc.metadata,
            },
            file_handle,
            ensure_ascii=False,
            indent=2,
        )


def get_embeddings() -> HuggingFaceEmbeddings:
    # This model creates 384-dimension dense vectors for each child chunk.
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


import os


def get_qdrant_client() -> QdrantClient:
    qdrant_url = os.getenv("QDRANT_URL")
    if qdrant_url:
        return QdrantClient(url=qdrant_url)
    # Local Qdrant is stored on disk inside data/qdrant.
    return QdrantClient(path=str(QDRANT_PATH))


def recreate_collection(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=Distance.COSINE,
        ),
    )


def ensure_collection_exists(client: QdrantClient, reset: bool) -> None:
    if reset:
        print("Reset de la collection Qdrant...")
        recreate_collection(client)
        
        # Nettoyage physique du stockage local des chunks parents
        print("Nettoyage du dossier parent_store...")
        for json_file in PARENT_STORE_PATH.glob("*.json"):
            try:
                json_file.unlink()
            except Exception as e:
                print(f"Impossible de supprimer {json_file.name} : {e}")
        return

    if not client.collection_exists(COLLECTION_NAME):
        print("Creation de la collection Qdrant...")
        recreate_collection(client)


def get_vector_store(
    client: QdrantClient,
    embeddings: HuggingFaceEmbeddings,
) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )


def build_qdrant_point_id(child_id: str) -> str:
    # Qdrant expects a valid UUID for string point ids.
    # uuid5 keeps the id deterministic for the same child chunk across re-indexing.
    return str(uuid5(NAMESPACE_URL, child_id))


def create_child_documents(
    parent_doc: Document,
    source_name: str,
    parent_id: str,
) -> tuple[list[Document], list[str], list[str]]:
    child_documents = []
    child_ids = []
    point_ids = []

    split_children = child_splitter.split_documents([parent_doc])

    for child_index, child_doc in enumerate(split_children):
        child_id = f"{parent_id}_child_{child_index}"
        child_doc.metadata["source"] = source_name
        child_doc.metadata["parent_id"] = parent_id
        child_doc.metadata["child_id"] = child_id
        child_documents.append(child_doc)
        child_ids.append(child_id)
        point_ids.append(build_qdrant_point_id(child_id))

    return child_documents, child_ids, point_ids


def index_documents(reset: bool = False) -> None:
    txt_files = sorted(PROCESSED_DIR.glob("*.txt"), key=lambda path: path.name.lower())

    if not txt_files:
        print("Aucun fichier TXT trouve dans data/processed")
        return

    print(f"{len(txt_files)} fichiers TXT trouves")
    print(f"Modele d'embedding : {EMBEDDING_MODEL_NAME}")
    print(f"Collection Qdrant : {COLLECTION_NAME}")

    total_parents = 0
    total_children = 0
    error_count = 0
    raw_pdf_lookup = build_raw_pdf_lookup()

    embeddings = get_embeddings()
    qdrant_client = get_qdrant_client()
    ensure_collection_exists(qdrant_client, reset=reset)
    vector_store = get_vector_store(qdrant_client, embeddings)

    for txt_file in txt_files:
        print(f"Traitement : {txt_file.name}")

        try:
            text = txt_file.read_text(encoding="utf-8", errors="ignore")

            if len(text.strip()) < 100:
                print("Texte trop court, ignore")
                continue

            source_name = raw_pdf_lookup.get(
                txt_file.stem.casefold(),
                f"{txt_file.stem}.pdf",
            )
            parent_chunks = parent_splitter.split_text(text)

            file_child_documents = []
            file_point_ids = []

            for parent_index, parent_text in enumerate(parent_chunks):
                parent_id = f"{txt_file.stem}_parent_{parent_index}"

                parent_doc = Document(
                    page_content=parent_text,
                    metadata={
                        "source": source_name,
                        "parent_id": parent_id,
                    },
                )

                parent_file = PARENT_STORE_PATH / f"{parent_id}.json"
                write_parent_document(parent_file, parent_doc)

                child_documents, _, point_ids = create_child_documents(
                    parent_doc=parent_doc,
                    source_name=source_name,
                    parent_id=parent_id,
                )

                file_child_documents.extend(child_documents)
                file_point_ids.extend(point_ids)

                total_parents += 1
                total_children += len(child_documents)

            if file_child_documents:
                # Deterministic UUIDs let us re-run indexing without duplicating chunks.
                vector_store.add_documents(
                    documents=file_child_documents,
                    ids=file_point_ids,
                )

            print(
                f"{txt_file.name} -> {len(parent_chunks)} parent chunks, "
                f"{len(file_child_documents)} child chunks"
            )

        except Exception as exc:
            error_count += 1
            print(f"ERREUR : {txt_file.name}")
            print(exc)

    print("Indexation locale terminee")
    print(f"Total parent chunks : {total_parents}")
    print(f"Total child chunks : {total_children}")
    print(f"Fichiers en erreur : {error_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cree les parent chunks en JSON et indexe les child chunks dans Qdrant.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprime puis recree la collection Qdrant avant indexation.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    index_documents(reset=args.reset)
