from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

from backend.app.agent_graph import run_agent
from backend.app.llm_service import generate_answer
from backend.app.retrieval_tools import search_with_context

app = FastAPI(
    title="Agentic RAG TdR",
    version="1.0"
)


class SearchRequest(BaseModel):
    query: str = Field(..., description="Question utilisateur a rechercher")
    limit: int = Field(default=5, ge=1, description="Nombre maximum de resultats")


class SearchResult(BaseModel):
    score: float
    source: str
    parent_id: str
    parent_content: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class AnswerSource(BaseModel):
    source: str
    parent_id: str
    score: float


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[AnswerSource]


class AgentAskRequest(BaseModel):
    query: str = Field(..., description="Question utilisateur a analyser")


class AgentAskResponse(BaseModel):
    query: str
    answer: str
    sources_count: int


@app.get("/")
def root():
    return {
        "message": "Agentic RAG TdR API fonctionne"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    # This endpoint sends the user question to the retrieval pipeline.
    return search_with_context(
        query=request.query,
        limit=request.limit,
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: SearchRequest):
    try:
        search_response = search_with_context(
            query=request.query,
            limit=request.limit,
        )
        results = search_response.get("results", [])
        answer = generate_answer(
            query=request.query,
            context_documents=results,
        )

        sources = [
            {
                "source": result.get("source", ""),
                "parent_id": result.get("parent_id", ""),
                "score": float(result.get("score", 0.0)),
            }
            for result in results
        ]

        return {
            "query": request.query,
            "answer": answer,
            "sources": sources,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la generation de la reponse : {exc}",
        ) from exc


@app.post("/agent-ask", response_model=AgentAskResponse)
def agent_ask(request: AgentAskRequest):
    try:
        result = run_agent(request.query)
        return {
            "query": result.get("query", request.query),
            "answer": result.get("answer", ""),
            "sources_count": len(result.get("results", [])),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'execution du graphe agentique : {exc}",
        ) from exc
