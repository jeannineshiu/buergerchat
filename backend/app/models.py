from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db import Base, FeedbackBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Chunk(Base):
    """One retrievable RAG chunk. id doubles as the FAISS vector ID —
    crawler/build_index.py assigns both from the same sequence.
    """

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    topic = Column(String)
    source = Column(String)
    content = Column(Text, nullable=False)
    crawled_at = Column(String)


# Feedback tables live on FeedbackBase (own sqlite file, see app/db.py) so
# neither the crawler's drop-and-recreate nor the index upload touches them.


class FeedbackMessage(FeedbackBase):
    """Thumbs up/down on a single assistant answer."""

    __tablename__ = "feedback_message"

    id = Column(Integer, primary_key=True)
    message_id = Column(String, nullable=False)
    session_id = Column(String, nullable=False)
    rating = Column(String, nullable=False)  # "up" | "down"
    comment = Column(Text)
    topic = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeedbackSession(FeedbackBase):
    """1-5 star rating for a whole conversation."""

    __tablename__ = "feedback_session"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
