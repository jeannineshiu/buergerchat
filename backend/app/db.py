import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SQLITE_PREFIX = "sqlite:///"


def resolve_database_url() -> str:
    """Relative sqlite paths are anchored to the repo root, not cwd — a
    relative path resolved against whatever directory a process happens to
    be launched from is a trap (bit the crawler scripts twice already).
    Postgres URLs pass through unchanged.
    """
    data_dir = os.environ.get("DATA_DIR", "data")
    url = os.environ.get("DATABASE_URL", f"{SQLITE_PREFIX}{data_dir}/metadata.db")
    if url.startswith(SQLITE_PREFIX):
        raw_path = url[len(SQLITE_PREFIX):]
        abs_path = (REPO_ROOT / raw_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{SQLITE_PREFIX}{abs_path}"
    return url


def resolve_feedback_database_url() -> str:
    """Feedback lives in its own sqlite file, NOT in metadata.db: the index
    upload (scripts/upload-index.sh) replaces metadata.db wholesale on the
    volume, which would silently wipe feedback stored alongside the chunks.
    """
    data_dir = os.environ.get("DATA_DIR", "data")
    url = os.environ.get("FEEDBACK_DATABASE_URL", f"{SQLITE_PREFIX}{data_dir}/feedback.db")
    if url.startswith(SQLITE_PREFIX):
        raw_path = url[len(SQLITE_PREFIX):]
        abs_path = (REPO_ROOT / raw_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{SQLITE_PREFIX}{abs_path}"
    return url


def resolve_usage_database_url() -> str:
    """Daily OpenAI spend (budget.py). Own file for the same reason as
    feedback.db: the index upload must never reset the day's spend."""
    data_dir = os.environ.get("DATA_DIR", "data")
    url = os.environ.get("USAGE_DATABASE_URL", f"{SQLITE_PREFIX}{data_dir}/usage.db")
    if url.startswith(SQLITE_PREFIX):
        raw_path = url[len(SQLITE_PREFIX):]
        abs_path = (REPO_ROOT / raw_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{SQLITE_PREFIX}{abs_path}"
    return url


engine = create_engine(resolve_database_url())
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

feedback_engine = create_engine(resolve_feedback_database_url())
FeedbackSessionLocal = sessionmaker(bind=feedback_engine)
FeedbackBase = declarative_base()

usage_engine = create_engine(resolve_usage_database_url())
