"""Lightweight visibility / observability layer.

Every agent run writes a structured trace to:
  - logs/agent_runs.jsonl            (machine-readable)
  - docs/agent_activity_log.md       (human-readable)
  - event_state["state"]["activity_log"] (in-memory)

We never expose private chain-of-thought. `reasoning_summary` is a concise,
user-facing explanation suitable for product/ops review.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


BRANCH_CONTEXT = "event_intelligence"
LOG_FILE = "logs/agent_runs.jsonl"
ACTIVITY_LOG_MD = "docs/agent_activity_log.md"


def set_branch_context(name: str) -> None:
    """Override the default branch_context used in trace entries."""
    global BRANCH_CONTEXT
    BRANCH_CONTEXT = name


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run_id(agent_name: str) -> str:
    return f"{agent_name}-{uuid.uuid4().hex[:8]}"


def _ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_agent_run(
    agent_name: str,
    *,
    run_id: Optional[str] = None,
    input_summary: str = "",
    output_summary: str = "",
    decisions_made: Optional[list[str]] = None,
    reasoning_summary: str = "",
    confidence: float | str = "medium",
    files_read: Optional[list[str]] = None,
    files_written: Optional[list[str]] = None,
    blockers: Optional[list[str]] = None,
    next_actions: Optional[list[str]] = None,
    event_state: Optional[dict[str, Any]] = None,
    log_path: str = LOG_FILE,
    md_path: str = ACTIVITY_LOG_MD,
    persist_to_disk: bool = True,
) -> dict[str, Any]:
    """Write a structured trace entry; returns the entry dict.

    When persist_to_disk is False (e.g. dry-run previews), skip JSONL, Markdown,
    and DB writes — only optional in-memory activity_log on event_state.
    """
    entry = {
        "run_id": run_id or create_run_id(agent_name),
        "timestamp": _now_iso(),
        "branch_context": BRANCH_CONTEXT,
        "agent_name": agent_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "decisions_made": decisions_made or [],
        "reasoning_summary": reasoning_summary,
        "confidence": confidence,
        "files_read": files_read or [],
        "files_written": files_written or [],
        "blockers": blockers or [],
        "next_actions": next_actions or [],
    }

    if persist_to_disk:
        # 1. JSONL trace
        p = _ensure_parent(log_path)
        with p.open("a") as f:
            f.write(json.dumps(entry) + "\n")

        # 2. Markdown activity log
        append_activity_log_markdown(entry, md_path=md_path)

    # 3. In-memory event_state
    if event_state is not None:
        append_event_state_activity(event_state, entry)

    # 4. DB (best-effort — never fails the pipeline)
    if persist_to_disk:
        try:
            from packages.shared import db as _db
            if _db.is_db_enabled():
                event_id = None
                if event_state is not None:
                    event_id = event_state.get("_db_event_id")
                _db.append_agent_run(entry, event_id=event_id)
        except Exception:
            pass

    return entry


def append_activity_log_markdown(entry: dict[str, Any], md_path: str = ACTIVITY_LOG_MD) -> None:
    p = _ensure_parent(md_path)
    if not p.exists():
        p.write_text("# Agent Activity Log\n\nHuman-readable trace of all agent runs in the Eventful branch.\n\n")

    lines = [
        f"## {entry['timestamp']} — {entry['agent_name']} (`{entry['run_id']}`)\n",
        f"- **Input:** {entry['input_summary']}",
        f"- **Output:** {entry['output_summary']}",
        f"- **Reasoning:** {entry['reasoning_summary']}",
        f"- **Confidence:** {entry['confidence']}",
    ]
    if entry["decisions_made"]:
        lines.append("- **Decisions:**")
        lines.extend(f"  - {d}" for d in entry["decisions_made"])
    if entry["files_read"]:
        lines.append(f"- **Files read:** {', '.join(entry['files_read'])}")
    if entry["files_written"]:
        lines.append(f"- **Files written:** {', '.join(entry['files_written'])}")
    if entry["blockers"]:
        lines.append("- **Blockers:**")
        lines.extend(f"  - {b}" for b in entry["blockers"])
    if entry["next_actions"]:
        lines.append("- **Next actions:**")
        lines.extend(f"  - {a}" for a in entry["next_actions"])
    lines.append("")

    with p.open("a") as f:
        f.write("\n".join(lines) + "\n")


def append_event_state_activity(event_state: dict[str, Any], entry: dict[str, Any]) -> None:
    state = event_state.setdefault("state", {})
    log = state.setdefault("activity_log", [])
    log.append({
        "run_id": entry["run_id"],
        "timestamp": entry["timestamp"],
        "agent_name": entry["agent_name"],
        "summary": entry["output_summary"],
    })
    state["last_agent_run"] = {
        "agent_name": entry["agent_name"],
        "timestamp": entry["timestamp"],
        "summary": entry["output_summary"],
        "run_id": entry["run_id"],
    }
