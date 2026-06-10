import sys
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.llm_service import generate_answer
from backend.app.retrieval_tools import search_with_context

OLLAMA_MODEL_NAME = "llama3.2:3b"
OLLAMA_HOST = "http://localhost:11434"


class AgentState(TypedDict, total=False):
    query: str
    original_query: str
    rewritten_query: str
    needs_retrieval: bool
    results: list[dict[str, Any]]
    answer: str


def analyze_query(state: AgentState) -> dict[str, Any]:
    # We keep the original query in the state.
    original_query = state["query"]
    return {
        "query": original_query,
        "original_query": original_query,
        "needs_retrieval": True,
    }


def rewrite_query(state: AgentState) -> dict[str, Any]:
    # Rewrites the user question into a more precise document search query.
    try:
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError(
            "Le package Python 'ollama' n'est pas installe dans l'environnement du projet."
        ) from exc

    original_query = state.get("original_query", state["query"])
    client = Client(host=OLLAMA_HOST)

    prompt = f"""Tu es un assistant spécialisé dans la recherche documentaire.

Réécris la question utilisateur en une requête documentaire courte, précise et utile pour la recherche.

Règles :
- garde les noms propres, institutions, dates et concepts importants
- n'ajoute pas d'explication
- retourne uniquement la requête réécrite

Question utilisateur :
{original_query}

Requête documentaire :"""

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
    rewritten_query = message.get("content", "").strip()

    return {
        "rewritten_query": rewritten_query or original_query,
    }


def retrieve_context(state: AgentState) -> dict[str, Any]:
    # Retrieve parent chunks from the existing search pipeline.
    search_query = state.get("rewritten_query") or state["query"]
    search_result = search_with_context(search_query)
    return {
        "results": search_result.get("results", []),
    }


def generate_response(state: AgentState) -> dict[str, Any]:
    # Send the retrieved documents to the LLM.
    answer = generate_answer(
        query=state.get("original_query", state["query"]),
        context_documents=state.get("results", []),
    )
    return {
        "answer": answer,
    }


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analyze_query", analyze_query)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_response", generate_response)

    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "rewrite_query")
    graph.add_edge("rewrite_query", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


AGENT_GRAPH = build_agent_graph()


def run_agent(query: str) -> dict[str, Any]:
    return AGENT_GRAPH.invoke({"query": query})


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    question = "audit financier banque mondiale"
    result = run_agent(question)

    print("query:")
    print(result.get("query", question))
    print()
    print("rewritten_query:")
    print(result.get("rewritten_query", ""))
    print()
    print("nombre de documents retrouves:")
    print(len(result.get("results", [])))
    print()
    print("reponse finale:")
    print(result.get("answer", ""))
