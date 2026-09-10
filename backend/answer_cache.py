"""In-memory cache for first-turn answers.

Most visitors start by clicking one of the frontend's starter prompts, so
the same few questions arrive over and over, and each one costs a rerank
and an answer completion. A first turn (no history) is a pure function of
(message, language) up to model sampling, so its answer can be reused.

In-process memory on purpose: a redeploy clears it, and shipping a new index
requires a redeploy anyway (see CLAUDE.md), so no cached answer outlives the
index it was built from. With more than one replica each keeps its own
copy, which only lowers the hit rate.
"""

import threading
import time
from collections import OrderedDict


def cache_key(message: str, language: str) -> tuple[str, str]:
    # Whitespace-insensitive, so a trailing space or newline still hits.
    return (" ".join(message.split()), language)


class AnswerCache:
    def __init__(self, ttl_seconds: float = 24 * 3600, max_entries: int = 500, clock=time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if self._clock() - stored_at > self.ttl_seconds:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def put(self, key, value) -> None:
        with self._lock:
            self._entries[key] = (self._clock(), value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
