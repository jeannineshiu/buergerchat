import os
import sys
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

from answer_cache import AnswerCache, cache_key
from app.db import FeedbackSessionLocal, FeedbackBase, feedback_engine, usage_engine
from app.models import FeedbackMessage, FeedbackSession
from behoerde import BehoerdeFinder
from budget import DailyBudget
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
#
# slowapi's default storage is in-process memory: each replica counts hits
# independently, so N replicas silently multiply every limit by N instead
# of enforcing it — no error, just a quietly-wrong limit. Fine today (one
# Railway replica per CLAUDE.md), but if replicas > 1 is ever turned on,
# set RATELIMIT_STORAGE_URI (e.g. redis://…, needs the `redis` package —
# already pinned in requirements.txt) so counts are shared.
RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI")
if not RATELIMIT_STORAGE_URI and os.environ.get("FRONTEND_ORIGIN"):
    # FRONTEND_ORIGIN is only set in the deployed environment (see CORS
    # below) — this is the "looks like production" signal available here.
    print(
        "[startup] RATELIMIT_STORAGE_URI not set: rate limiting uses "
        "in-process memory and only enforces correctly with exactly one "
        "backend replica.",
        file=sys.stderr,
    )
limiter = Limiter(key_func=client_ip, storage_uri=RATELIMIT_STORAGE_URI)

# Per minute stops bursts; per day stops one person (or script) from
# spending the whole daily budget alone — 10/minute alone allowed 14,400
# questions a day per IP. In-memory counts reset on redeploy.
CHAT_DAILY_LIMIT = int(os.environ.get("CHAT_DAILY_LIMIT", "30"))
CHAT_RATE_LIMIT = f"10/minute;{CHAT_DAILY_LIMIT}/day"

app = FastAPI(
    title="buergerchat API",
    description="RAG chatbot backend for German government services",
    version="0.1.0",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded(request: Request, exc: RateLimitExceeded):
    # The frontend tells "wait a minute" apart from "come back tomorrow"
    # by this code — slowapi's default body only carries a prose detail.
    daily = exc.limit.limit.GRANULARITY.name == "day"
    response = _rate_limit_exceeded_handler(request, exc)
    return JSONResponse(
        status_code=429,
        content={
            "error": f"Rate limit exceeded: {exc.detail}",
            "code": "daily_limit" if daily else "rate_limit",
        },
        headers=dict(response.headers),
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
# Every OpenAI response /chat triggers is costed into today's total; see
# budget.py. DAILY_BUDGET_USD (default 0.50, "off" disables) caps it.
daily_budget = DailyBudget.from_env(usage_engine)
rag_pipeline = RAGPipeline(on_usage=daily_budget.record)
behoerde_finder = BehoerdeFinder()
answer_cache = AnswerCache()


class DailyBudgetExhausted(Exception):
    """Today's OpenAI spend reached DAILY_BUDGET_USD."""


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


@app.exception_handler(DailyBudgetExhausted)
def daily_budget_exhausted(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "error": "Daily usage limit reached. Please try again tomorrow.",
            "code": "daily_budget_exhausted",
        },
    )


@app.exception_handler(IndexNotReadyError)
def index_not_ready(request, exc):
    return JSONResponse(
        status_code=503,
        content={"error": "Index not yet available. Please try again later."},
    )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    # First turns are cached (answer_cache.py): the starter prompts arrive
    # again and again and cost nothing on a hit — even after the daily
    # budget is used up. "Cache-Control: no-cache" skips the lookup; the
    # smoke test sends it because it must reach the LLM to mean anything.
    first_turn = not chat_request.history
    key = cache_key(chat_request.message, chat_request.language)
    skip_lookup = "no-cache" in request.headers.get("cache-control", "").lower()
    if first_turn and not skip_lookup:
        cached = answer_cache.get(key)
        if cached is not None:
            return cached

    if daily_budget.exhausted():
        raise DailyBudgetExhausted()

    response = answer_question(chat_request)
    if first_turn:
        answer_cache.put(key, response)
    return response


def answer_question(chat_request: ChatRequest) -> ChatResponse:
    # Intent, topic and PLZ may be split across turns ("Wo ist mein
    # Jobcenter?" → bot asks for PLZ → "10115"), so fall back to the
    # user's history for whatever the new message doesn't contain.
    user_history = [m.content for m in chat_request.history if m.role == "user"]

    if query_router.is_chitchat(chat_request.message):
        # Pure small talk ("hi", "danke", "bye") — skip retrieval, same as
        # meta-questions, so no LLM call burns an embedding + top-5 search
        # (and no stray chunks leak into a source list that shouldn't exist).
        answer, _ = rag_pipeline.query(
            chat_request.message,
            language=chat_request.language,
            history=[m.model_dump() for m in chat_request.history],
            chitchat=True,
        )
        return ChatResponse(answer=answer, sources=[], topic=DEFAULT_TOPIC)

    if query_router.is_meta_question(chat_request.message):
        answer, _ = rag_pipeline.query(
            chat_request.message,
            language=chat_request.language,
            history=[m.model_dump() for m in chat_request.history],
            meta_only=True,
        )
        return ChatResponse(answer=answer, sources=[], topic=DEFAULT_TOPIC)

    message_topic = query_router.classify(chat_request.message)
    topic = message_topic
    if topic == DEFAULT_TOPIC:
        for past in reversed(user_history):
            past_topic = query_router.classify(past)
            if past_topic != DEFAULT_TOPIC:
                topic = past_topic
                break

    # Short follow-ups ("erkläre das nochmal", "用中文講一次", a bare PLZ)
    # carry no searchable meaning — embedding them retrieves noise. Enrich
    # the retrieval query with the previous question; the prompt still shows
    # the user's actual message.
    retrieval_query = None
    if message_topic == DEFAULT_TOPIC and user_history and len(chat_request.message) <= 80:
        retrieval_query = f"{user_history[-1]}\n{chat_request.message}"

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
    ask_for_topic = False
    authority_missing = False
    if wants_authority and plz:
        authority = behoerde_finder.find(plz, lookup_query, topic=topic)
        # A postcode alone does not determine a Behörde — responsibility is
        # per service. When the lookup came back empty and the message never
        # said what it is about ("Which office is responsible? 10115"), ask
        # rather than send the person off to a generic search page.
        if authority is None and topic == DEFAULT_TOPIC:
            ask_for_topic = True
        else:
            authority_missing = authority is None
    elif wants_authority:
        ask_for_plz = True

    answer, sources = rag_pipeline.query(
        chat_request.message,
        language=chat_request.language,
        topic=topic,
        authority=authority,
        ask_for_plz=ask_for_plz,
        ask_for_topic=ask_for_topic,
        authority_missing=authority_missing,
        history=[m.model_dump() for m in chat_request.history],
        retrieval_query=retrieval_query,
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
