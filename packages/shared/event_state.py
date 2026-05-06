"""Canonical shared event state schema for OneLoop.

This module defines the contract between the Eventful branch and the
Agentic Ops branch. Both branches read/write `data/event_state.json` using this
shape. Keep additions backward-compatible: prefer adding new optional keys over
renaming existing ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import json
from pathlib import Path


# ---------- Person / prospect ----------

PERSON_CSV_COLUMNS: list[str] = [
    "name",
    "company",
    "role",
    "linkedin_url",
    "email",
    "source",
    "persona",
    "why_relevant",
    "fit_score",
    "priority",
    "outreach_angle",
    "status",
    "tags",
    "notes",
]


def empty_person() -> dict[str, Any]:
    return {
        "name": "",
        "company": "",
        "role": "",
        "linkedin_url": "",
        "email": "",
        "source": "",
        "persona": "",
        "why_relevant": "",
        "fit_score": None,
        "priority": "",
        "outreach_angle": "",
        "status": "not_contacted",
        "tags": [],
        "notes": "",
    }


# ---------- Sub-section dataclasses ----------

@dataclass
class EventInfo:
    # goal = overall success intent; format = event kind; desired_attendees = who belongs in the room
    name: str = ""
    goal: str = ""
    desired_attendees: str = ""
    city: str = ""
    date: str = ""
    target_size: int = 100
    format: str = ""
    success_metrics: list[str] = field(default_factory=list)


@dataclass
class Intelligence:
    audience_icp: list[dict] = field(default_factory=list)
    avoid_personas: list[dict] = field(default_factory=list)
    sourcing_strategy: list[dict] = field(default_factory=list)
    scoring_rubric: dict = field(default_factory=dict)
    room_balance: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class People:
    prospects: list[dict] = field(default_factory=list)
    ranked_prospects: list[dict] = field(default_factory=list)
    approved: list[dict] = field(default_factory=list)
    waitlist: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)


@dataclass
class Ops:
    workstreams: list[dict] = field(default_factory=list)
    outreach_queue: list[dict] = field(default_factory=list)
    rsvp_tracker: list[dict] = field(default_factory=list)
    retention_plan: list[dict] = field(default_factory=list)
    basic_ops_checklist: list[dict] = field(default_factory=list)


@dataclass
class Venues:
    requirements: dict = field(default_factory=dict)
    pipeline: list[dict] = field(default_factory=list)


@dataclass
class Sponsors:
    partner_icp: list[dict] = field(default_factory=list)
    pipeline: list[dict] = field(default_factory=list)


@dataclass
class LastAgentRun:
    agent_name: str = ""
    timestamp: str = ""
    summary: str = ""
    run_id: str = ""


@dataclass
class StateMeta:
    open_questions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    approval_queue: list[dict] = field(default_factory=list)
    activity_log: list[dict] = field(default_factory=list)
    last_agent_run: LastAgentRun = field(default_factory=LastAgentRun)


@dataclass
class Visibility:
    latest_summary_files: list[str] = field(default_factory=list)
    latest_trace_file: str = "logs/agent_runs.jsonl"
    latest_activity_log: str = "docs/agent_activity_log.md"


@dataclass
class EventState:
    event: EventInfo = field(default_factory=EventInfo)
    intelligence: Intelligence = field(default_factory=Intelligence)
    people: People = field(default_factory=People)
    ops: Ops = field(default_factory=Ops)
    venues: Venues = field(default_factory=Venues)
    sponsors: Sponsors = field(default_factory=Sponsors)
    state: StateMeta = field(default_factory=StateMeta)
    visibility: Visibility = field(default_factory=Visibility)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------- IO helpers ----------

def empty_event_state() -> dict[str, Any]:
    return EventState().to_dict()


def load_event_state(path: str | Path) -> dict[str, Any]:
    """Load event_state.json, or return an empty state if it doesn't exist."""
    p = Path(path)
    if not p.exists():
        return empty_event_state()
    with p.open("r") as f:
        data = json.load(f)
    # merge with empty defaults so missing keys don't break consumers
    return _deep_merge(empty_event_state(), data)


def save_event_state(path: str | Path, state: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(state, f, indent=2, default=str)


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
