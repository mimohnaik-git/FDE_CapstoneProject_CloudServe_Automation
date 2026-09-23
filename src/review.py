"""Ephemeral storage for exact human-review handoffs.

Review drafts are deliberately not written to the decision database.
Loss of this cache therefore fails safely: the ticket remains escalated.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import math
import threading
import time
from typing import Any, Dict, Optional


class ReviewHandoffStore:
    """Thread-safe, TTL-bounded in-process handoff store."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 3600.0,
        max_entries: int = 1000,
    ):
        ttl = float(ttl_seconds)

        if not math.isfinite(ttl) or ttl <= 0:
            raise ValueError(
                "Review handoff TTL must be finite and positive"
            )

        if (
            isinstance(max_entries, bool)
            or not isinstance(max_entries, int)
            or max_entries < 1
        ):
            raise ValueError(
                "Review handoff capacity must be a positive integer"
            )

        self.ttl_seconds = ttl
        self.max_entries = max_entries
        self._items: OrderedDict[
            str,
            tuple[float, Dict[str, Any]],
        ] = OrderedDict()
        self._lock = threading.Lock()

    def _purge_expired(self, now: float) -> None:
        expired = [
            key
            for key, (expires_at, _) in self._items.items()
            if expires_at <= now
        ]

        for key in expired:
            self._items.pop(key, None)

    def put(
        self,
        decision_id: str,
        handoff: Dict[str, Any],
    ) -> None:
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise ValueError("decision_id is required")

        if not isinstance(handoff, dict):
            raise ValueError("handoff must be a dictionary")

        now = time.monotonic()

        with self._lock:
            self._purge_expired(now)

            key = decision_id.strip()
            self._items.pop(key, None)
            self._items[key] = (
                now + self.ttl_seconds,
                deepcopy(handoff),
            )

            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def get(
        self,
        decision_id: str,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(decision_id, str) or not decision_id.strip():
            return None

        now = time.monotonic()

        with self._lock:
            self._purge_expired(now)

            item = self._items.get(decision_id.strip())

            if item is None:
                return None

            _, handoff = item
            return deepcopy(handoff)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


review_handoff_store = ReviewHandoffStore()
