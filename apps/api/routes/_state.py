"""Shared helpers for routes that mutate data/event_state.json.

Centralizes the path resolution + read-modify-write pattern used by the
event/budget/attendees routes so they don't all rebuild the same boilerplate.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, TypeVar

from packages.shared.event_state import (
    BUDGET_CATEGORIES,
    empty_event_state,
    load_event_state,
    save_event_state,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_STATE_PATH = REPO_ROOT / "data" / "event_state.json"


# Single in-process lock so concurrent confirms / budget edits don't clobber
# each other. The API is single-host; this is the right granularity.
_LOCK = threading.Lock()


T = TypeVar("T")


def read_state() -> dict:
    """Load current event_state, falling back to an empty state if no file."""
    return load_event_state(EVENT_STATE_PATH)


def mutate_state(fn: Callable[[dict], T]) -> T:
    """Atomically read, mutate, and write event_state.

    ``fn`` receives the state dict and may mutate it in place; whatever
    ``fn`` returns is returned to the caller.
    """
    with _LOCK:
        state = read_state()
        result = fn(state)
        # Make sure the new top-level keys exist with sensible defaults so
        # consumers reading downstream can rely on them.
        state.setdefault("event_date", "")
        state.setdefault("event_end_time", None)
        budget = state.setdefault("budget", {"total_budget": 0.0, "sponsor_income": 0.0, "line_items": []})
        budget.setdefault("total_budget", 0.0)
        budget.setdefault("sponsor_income", 0.0)
        budget.setdefault("line_items", [])
        state.setdefault("attendees", [])
        save_event_state(EVENT_STATE_PATH, state)
        return result


__all__ = ["BUDGET_CATEGORIES", "EVENT_STATE_PATH", "REPO_ROOT", "read_state", "mutate_state", "empty_event_state"]
