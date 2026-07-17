import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.db import FeedbackSessionLocal, FeedbackBase, feedback_engine
from app.models import FeedbackMessage, FeedbackSession
from behoerde import BehoerdeFinder
from rag import IndexNotReadyError, RAGPipeline
from router import DEFAULT_TOPIC, QueryRouter

# Creates only the missing feedback tables; a no-op once they exist.
FeedbackBase.metadata.create_all(feedback_engine)

def client_ip(request: Request) -> str:
    """Rate-limit key. Behind Railway's proxy the socket peer is the edge,
    not the user — trust the first X-Forwarded-For hop instead."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Per-IP limits: /chat costs an LLM call per hit — without this it's a free,
# anonymous, unmetered OpenAI proxy. Limits are generous for human use.
limiter = Limiter(key_func=client_ip)

app = FastAPI(
    title="buergerchat API",
    description="RAG chatbot backend for German government services",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    # Length caps bound the cost of a single request (embedding + prompt
    # tokens scale with input size).
    message: str = Field(min_length=1, max_length=2000)
    language: str = Field(default="de", max_length=10)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


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
@limiter.limit("10/minute")
def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    # Intent, topic and PLZ may be split across turns ("Wo ist mein
    # Jobcenter?" → bot asks for PLZ → "10115"), so fall back to the
    # user's history for whatever the new message doesn't contain.
    user_history = [m.content for m in chat_request.history if m.role == "user"]

    if query_router.is_meta_question(chat_request.message):
        answer, _ = rag_pipeline.query(
            chat_request.message,
            language=chat_request.language,
            history=[m.model_dump() for m in chat_request.history],
            meta_only=True,
        )
        return ChatResponse(answer=answer, sources=[], topic=DEFAULT_TOPIC)

    topic = query_router.classify(chat_request.message)
    if topic == DEFAULT_TOPIC:
        for past in reversed(user_history):
            past_topic = query_router.classify(past)
            if past_topic != DEFAULT_TOPIC:
                topic = past_topic
                break

    wants_authority = query_router.wants_authority(chat_request.message) or any(
        query_router.wants_authority(past) for past in user_history[-2:]
    )
    plz = query_router.extract_plz(chat_request.message)
    if plz is None:
        for past in reversed(user_history):
            plz = query_router.extract_plz(past)
            if plz:
                break

    # A bare-PLZ follow-up carries no searchable text of its own — the
    # question it answers is the previous user message.
    lookup_query = chat_request.message
    if plz and chat_request.message.strip() == plz and user_history:
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
        chat_request.message,
        language=chat_request.language,
        topic=topic,
        authority=authority,
        ask_for_plz=ask_for_plz,
        authority_missing=authority_missing,
        history=[m.model_dump() for m in chat_request.history],
    )

    return ChatResponse(
        answer=answer,
        sources=[Source(**s) for s in sources],
        topic=topic,
    )


class MessageFeedbackRequest(BaseModel):
    message_id: str = Field(max_length=64)
    session_id: str = Field(max_length=64)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)
    topic: str | None = Field(default=None, max_length=40)


class SessionFeedbackRequest(BaseModel):
    session_id: str = Field(max_length=64)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


@app.post("/feedback/message", status_code=201)
@limiter.limit("30/minute")
def feedback_message(request: Request, feedback: MessageFeedbackRequest):
    session = FeedbackSessionLocal()
    try:
        session.add(FeedbackMessage(**feedback.model_dump()))
        session.commit()
    finally:
        session.close()
    return {"status": "saved"}


@app.post("/feedback/session", status_code=201)
@limiter.limit("30/minute")
def feedback_session(request: Request, feedback: SessionFeedbackRequest):
    session = FeedbackSessionLocal()
    try:
        session.add(FeedbackSession(**feedback.model_dump()))
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
