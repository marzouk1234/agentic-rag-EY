import sys
from typing import Any

from backend.app.retrieval_tools import search_with_context

import os

OLLAMA_MODEL_NAME = "llama3.2:3b"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def build_context_text(context_documents: list[dict[str, Any]]) -> str:
    # This function turns parent chunks into a single readable context.
    if not context_documents:
        return "Aucun contexte disponible."

    context_parts = []

    for index, document in enumerate(context_documents, start=1):
        source = document.get("source", "")
        parent_id = document.get("parent_id", "")
        parent_content = document.get("parent_content", "")

        context_parts.append(
            "\n".join(
                [
                    f"Document {index}",
                    f"Source: {source}",
                    f"Parent ID: {parent_id}",
                    "Contenu:",
                    parent_content,
                ]
            )
        )

    return "\n\n".join(context_parts)


def build_prompt(query: str, context_documents: list[dict[str, Any]]) -> str:
    context = build_context_text(context_documents)

    return f"""Tu es un assistant spécialisé dans l'analyse documentaire.

Réponds en utilisant exclusivement les informations du contexte.

Si le contexte contient des informations pertinentes, réponds directement.

Si aucune information pertinente n'est trouvée, indique clairement que les documents ne permettent pas de répondre.

Question :
{query}

Contexte :
{context}

Réponse :
"""


def generate_answer(query: str, context_documents: list[dict[str, Any]]) -> str:
    # Import is inside the function to keep the module easy to import
    # even if the Ollama Python package is not installed yet.
    try:
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError(
            "Le package Python 'ollama' n'est pas installe dans l'environnement du projet."
        ) from exc

    prompt = build_prompt(query=query, context_documents=context_documents)
    client = Client(host=OLLAMA_HOST)

    response = client.chat(
        model=OLLAMA_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    message = response.get("message", {})
    return message.get("content", "").strip()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    query = "audit financier banque mondiale"
    search_result = search_with_context(query=query, limit=5)
    answer = generate_answer(
        query=query,
        context_documents=search_result.get("results", []),
    )

    print("Question :")
    print(query)
    print()
    print("Réponse finale :")
    print(answer)
