from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import RAGPipeline
from router import QueryRouter

app = FastAPI(
    title="buergerchat API",
    description="RAG chatbot backend for German government services",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_router = QueryRouter()
rag_pipeline = RAGPipeline()


class Source(BaseModel):
    title: str
    url: str


class ChatRequest(BaseModel):
    message: str
    language: str = "de"


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    topic: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    topic = query_router.classify(request.message)
    answer, sources = rag_pipeline.query(request.message, language=request.language, topic=topic)

    return ChatResponse(
        answer=answer,
        sources=[Source(**s) for s in sources],
        topic=topic,
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"service": "buergerchat-backend"}
