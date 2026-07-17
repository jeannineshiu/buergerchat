import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import FeedbackSessionLocal, FeedbackBase, feedback_engine
from app.models import FeedbackMessage, FeedbackSession
from behoerde import BehoerdeFinder
from rag import IndexNotReadyError, RAGPipeline
from router import DEFAULT_TOPIC, QueryRouter

# Creates only the missing feedback tables; a no-op once they exist.
FeedbackBase.metadata.create_all(feedback_engine)

app = FastAPI(
    title="buergerchat API",
    description="RAG chatbot backend for German government services",
    version="0.1.0",
)

# In production, FRONTEND_ORIGIN carries the deployed frontend's origin
# (e.g. https://frontend-….up.railway.app).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"]
    + ([os.environ["FRONTEND_ORIGIN"]] if os.environ.get("FRONTEND_ORIGIN") else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_router = QueryRouter()
rag_pipeline = RAGPipeline()
behoerde_finder = BehoerdeFinder()


class Source(BaseModel):
    title: str
    url: str


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    language: str = "de"
    history: list[HistoryMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    topic: str


@app.exception_handler(IndexNotReadyError)
def index_not_ready(request, exc):
    return JSONResponse(
        status_code=503,
        content={"error": "Index not yet available. Please try again later."},
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Intent, topic and PLZ may be split across turns ("Wo ist mein
    # Jobcenter?" → bot asks for PLZ → "10115"), so fall back to the
    # user's history for whatever the new message doesn't contain.
    user_history = [m.content for m in request.history if m.role == "user"]

    if query_router.is_meta_question(request.message):
        answer, _ = rag_pipeline.query(
            request.message,
            language=request.language,
            history=[m.model_dump() for m in request.history],
            meta_only=True,
        )
        return ChatResponse(answer=answer, sources=[], topic=DEFAULT_TOPIC)

    topic = query_router.classify(request.message)
    if topic == DEFAULT_TOPIC:
        for past in reversed(user_history):
            past_topic = query_router.classify(past)
            if past_topic != DEFAULT_TOPIC:
                topic = past_topic
                break

    wants_authority = query_router.wants_authority(request.message) or any(
        query_router.wants_authority(past) for past in user_history[-2:]
    )
    plz = query_router.extract_plz(request.message)
    if plz is None:
        for past in reversed(user_history):
            plz = query_router.extract_plz(past)
            if plz:
                break

    # A bare-PLZ follow-up carries no searchable text of its own — the
    # question it answers is the previous user message.
    lookup_query = request.message
    if plz and request.message.strip() == plz and user_history:
        lookup_query = user_history[-1]

    authority = None
    ask_for_plz = False
    authority_missing = False
    if wants_authority and plz:
        authority = behoerde_finder.find(plz, lookup_query, topic=topic)
        authority_missing = authority is None
    elif wants_authority:
        ask_for_plz = True

    answer, sources = rag_pipeline.query(
        request.message,
        language=request.language,
        topic=topic,
        authority=authority,
        ask_for_plz=ask_for_plz,
        authority_missing=authority_missing,
        history=[m.model_dump() for m in request.history],
    )

    return ChatResponse(
        answer=answer,
        sources=[Source(**s) for s in sources],
        topic=topic,
    )


class MessageFeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    rating: Literal["up", "down"]
    comment: str | None = None
    topic: str | None = None


class SessionFeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


@app.post("/feedback/message", status_code=201)
def feedback_message(request: MessageFeedbackRequest):
    session = FeedbackSessionLocal()
    try:
        session.add(FeedbackMessage(**request.model_dump()))
        session.commit()
    finally:
        session.close()
    return {"status": "saved"}


@app.post("/feedback/session", status_code=201)
def feedback_session(request: SessionFeedbackRequest):
    session = FeedbackSessionLocal()
    try:
        session.add(FeedbackSession(**request.model_dump()))
        session.commit()
    finally:
        session.close()
    return {"status": "saved"}


@app.get("/health")
def health_check():
    # Always 200 so the Railway healthcheck passes while the /data volume
    # is still empty; "degraded" tells operators the index is missing.
    if rag_pipeline.load():
        return {"status": "ok", "index": "loaded"}
    return {"status": "degraded", "index": "missing"}


@app.get("/")
def root():
    return {"service": "buergerchat-backend"}
