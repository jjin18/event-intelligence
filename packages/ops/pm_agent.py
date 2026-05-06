"""PM Agent: turns event state + ranked people into workstreams, timeline, blockers, next actions."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.shared import visibility
from . import _common
from ._common import (
    DATA_DIR, DOCS_DIR, EVENT_STATE_PATH, RANKED_PEOPLE_PATH,
    INTELLIGENCE_SUMMARY_PATH, rel,
)

WORKSTREAMS = [
    "guest_outreach",
    "venue_outreach",
    "sponsor_partner_outreach",
    "rsvp_tracking",
    "retention",
    "basic_ops",
]


def run(event_state: dict[str, Any]) -> dict[str, Any]:
    _common.ensure_dirs()
    run_id = visibility.create_run_id("pm_agent")

    event = event_state.get("event", {}) or {}
    target = event.get("target_size") or 100
    venue_pipeline = (event_state.get("venues", {}) or {}).get("pipeline", []) or []
    venue_confirmed = any((v.get("status") or "").lower() == "confirmed" for v in venue_pipeline)
    ranked = (event_state.get("people", {}) or {}).get("ranked_prospects", []) or []

    next_actions = [
        f"Send first batch of {min(30, max(10, len(ranked) // 3))} high-priority guest invites",
        "Contact 10 venue candidates and request availability + capacity + AV",
        "Create event page copy for Luma / manual ticketing",
        "Schedule 48h and day-of reminder cadence",
    ]
    blockers: list[str] = []
    if not venue_confirmed:
        blockers.append("Venue not confirmed")
    if not target:
        blockers.append("No RSVP target set")
    if not ranked:
        blockers.append("No ranked prospects available — Eventful may not have run yet")

    one_week_timeline = [
        "T-7d: lock venue, finalize ICP, send first 30 invites",
        "T-6d: open Luma/RSVP page, send next 30 invites",
        "T-5d: sponsor/partner outreach, food + AV decisions",
        "T-4d: reply triage, calendar invites to accepted",
        "T-3d: send 48h reminder, personal nudges to top-priority no-replies",
        "T-2d: confirm headcount, finalize run-of-show, print name tags",
        "T-1d: day-of reminder, staff briefing, final venue walkthrough",
        "Day-of: doors 6:00 PM, program 6:30, soft close 8:00",
    ]

    state = event_state.setdefault("state", {})
    ops = event_state.setdefault("ops", {})
    ops["workstreams"] = [{"name": w, "status": "active"} for w in WORKSTREAMS]
    state["next_actions"] = next_actions
    state["blockers"] = blockers
    state.setdefault("approval_queue", [])
    state["approval_queue"] = [
        {"item": "First batch of guest invite drafts", "owner": "organizer", "status": "pending_review"},
        {"item": "Venue shortlist (top 5)", "owner": "organizer", "status": "pending_review"},
    ]

    files_read = [rel(EVENT_STATE_PATH)]
    if RANKED_PEOPLE_PATH.exists():
        files_read.append(rel(RANKED_PEOPLE_PATH))
    if INTELLIGENCE_SUMMARY_PATH.exists():
        files_read.append(rel(INTELLIGENCE_SUMMARY_PATH))

    timeline_path = DOCS_DIR / "one_week_timeline.md"
    timeline_path.write_text(
        "# One-Week Timeline\n\n" + "\n".join(f"- {row}" for row in one_week_timeline) + "\n"
    )

    visibility.log_agent_run(
        agent_name="pm_agent",
        run_id=run_id,
        input_summary=f"target={target}, ranked={len(ranked)}, venue_confirmed={venue_confirmed}",
        output_summary=f"set {len(WORKSTREAMS)} workstreams, {len(next_actions)} next actions, {len(blockers)} blockers",
        decisions_made=[
            f"Workstreams: {', '.join(WORKSTREAMS)}",
            "One-week timeline generated",
        ],
        reasoning_summary=(
            "Curated event for ~100 in one week needs parallel guest, venue, sponsor, RSVP, "
            "retention, and basic-ops tracks. Blockers prioritized by what gates the next decision."
        ),
        confidence="medium",
        files_read=files_read,
        files_written=[rel(timeline_path)],
        blockers=blockers,
        next_actions=next_actions,
        event_state=event_state,
    )
    return {"workstreams": WORKSTREAMS, "next_actions": next_actions, "blockers": blockers}
