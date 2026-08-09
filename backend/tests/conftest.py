"""Shared fixtures. Everything runs offline: OpenAI, FAISS files and the
PVOG API are stubbed or written into a temp DATA_DIR.

Env vars are set BEFORE any app import — app.db resolves its engines and
main.py creates the feedback tables at import time.
"""

import os
import sys
import tempfile
from pathlib import Path

# One temp data dir for the whole test session, wired up before imports.
# SET (never just pop) every path-ish variable: main.py load_dotenv()s the
# developer's backend/.env on import, and dotenv fills in any key that is
# absent — a popped DATABASE_URL would come back pointing at the REAL
# data/metadata.db, which test fixtures then drop_all(). Been there.
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="buergerchat-test-data-")
os.environ["DATA_DIR"] = _TEST_DATA_DIR
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["FAISS_INDEX_PATH"] = ""  # falsy → rag falls back to DATA_DIR
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATA_DIR}/metadata.db"
os.environ["FEEDBACK_DATABASE_URL"] = f"sqlite:///{_TEST_DATA_DIR}/feedback.db"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture()
def data_dir() -> Path:
    return Path(_TEST_DATA_DIR)


class FakeEmbeddings:
    """Deterministic embeddings: hash of the text seeds a random vector, so
    identical texts embed identically and retrieval is reproducible."""

    def create(self, model: str, input):  # noqa: A002 - OpenAI SDK signature
        texts = input if isinstance(input, list) else [input]
        data = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            vec = rng.standard_normal(1536).astype("float32")
            data.append(type("Item", (), {"embedding": vec.tolist()})())
        return type("Resp", (), {"data": data})()


class FakeChatCompletions:
    def __init__(self):
        self.last_messages = None
        # retrieve() can make two chat calls now (translation, rerank) before
        # the answer call, so tests need the whole sequence, not just the last.
        self.calls = []

    def create(self, model, messages):
        self.last_messages = messages
        self.calls.append(messages)
        message = type("Msg", (), {"content": "STUB ANSWER"})()
        choice = type("Choice", (), {"message": message})()
        return type("Completion", (), {"choices": [choice]})()


class FakeOpenAI:
    def __init__(self):
        self.embeddings = FakeEmbeddings()
        self.chat = type("Chat", (), {"completions": FakeChatCompletions()})()


@pytest.fixture()
def fake_openai() -> FakeOpenAI:
    return FakeOpenAI()
