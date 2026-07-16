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
    url = os.environ.get("DATABASE_URL", f"{SQLITE_PREFIX}data/metadata.db")
    if url.startswith(SQLITE_PREFIX):
        raw_path = url[len(SQLITE_PREFIX):]
        abs_path = (REPO_ROOT / raw_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{SQLITE_PREFIX}{abs_path}"
    return url


engine = create_engine(resolve_database_url())
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
