"""Objective Agent — normalizes organizer input into a structured objective.

Pulls three pillars when possible (event type, desired attendees, overall goal)
via intent_extractor (LLM when configured, else labeled-section parsing), then
fills size/city with lightweight heuristics.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

from packages.agents.intent_extractor import extract_event_intent
from packages.shared.visibility import create_run_id, log_agent_run


AGENT_NAME = "objective_agent"

# Baseline checklist merged into state / preview — surfaced until brief has answers.
DEFAULT_OPEN_QUESTIONS: list[str] = [
    "Is the event public or invite-only?",
    "Is there a sponsor or partner goal?",
    "Is the venue already secured?",
    "What is the exact date and time?",
    "Who is the primary host / face of the event?",
]


def _extract_int(text: str, default: int) -> int:
    m = re.search(r"(\d{2,4})\s*[- ]?\s*person", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{2,4})\b", text)
    return int(m.group(1)) if m else default


def _extract_city(text: str) -> str:
    for token in ["SF", "San Francisco", "NYC", "New York", "LA", "Los Angeles", "Austin", "Seattle", "London"]:
        if re.search(rf"\b{re.escape(token)}\b", text, flags=re.IGNORECASE):
            return token
    return ""


def _extract_event_type(text: str) -> str:
    t = text.lower()
    if "hackathon" in t:
        return "hackathon"
    if "dinner" in t:
        return "curated dinner"
    if "panel" in t:
        return "panel"
    if "summit" in t or "conference" in t:
        return "summit"
    if "meetup" in t or "community" in t:
        return "curated tech community event"
    return "curated tech community event"


_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _next_weekday(target_idx: int, base: date, force_next_week: bool = False) -> date:
    """Return the next date with weekday == target_idx, after ``base``.

    If today already matches and force_next_week is False, returns today + 7
    (event organizers saying "Saturday" on Saturday rarely mean today).
    """
    diff = (target_idx - base.weekday()) % 7
    if diff == 0 or force_next_week:
        diff = 7 if force_next_week or diff == 0 else diff
    return base + timedelta(days=diff)


def _extract_date(text: str, today: Optional[date] = None) -> str:
    """Best-effort date extraction from a free-form brief.

    Returns an ISO 8601 date string ("YYYY-MM-DD") if a date is found,
    otherwise an empty string. Designed to handle the common phrasings
    organizers use ("next Saturday", "May 17", "5/17/2026", "2026-05-17",
    "tomorrow") without adding a dateutil dependency.
    """
    if not text:
        return ""
    today = today or date.today()
    t = text.lower()

    # Relative day shortcuts
    if re.search(r"\btomorrow\b", t):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", t):
        return today.isoformat()

    # "next/this <weekday>"
    m = re.search(r"\b(this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m:
        modifier = m.group(1)
        wd = _WEEKDAYS[m.group(2)]
        return _next_weekday(wd, today, force_next_week=(modifier == "next")).isoformat()

    # ISO format YYYY-MM-DD
    m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass

    # US format M/D/YYYY or M/D/YY
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", text)
    if m:
        try:
            mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if yr < 100:
                yr += 2000
            return date(yr, mo, day).isoformat()
        except ValueError:
            pass

    # "Month D[, YYYY]"  e.g. "May 17", "May 17, 2026", "Jan 5"
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+"
        r"(\d{1,2})(?:[,\s]+(20\d{2}))?\b",
        t,
    )
    if m:
        try:
            mo = _MONTHS[m.group(1)]
            day = int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else today.year
            d = date(yr, mo, day)
            # If no year given and the date already passed this year, roll forward.
            if not m.group(3) and d < today:
                d = date(yr + 1, mo, day)
            return d.isoformat()
        except (ValueError, KeyError):
            pass

    # Bare weekday name ("on Saturday")
    m = re.search(r"\b(?:on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m:
        return _next_weekday(_WEEKDAYS[m.group(1)], today).isoformat()

    return ""


def _coerce_size(value: Any, brief: str, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return _extract_int(brief, default)


def run(brief: str, constraints: Optional[dict[str, Any]] = None,
        event_state: Optional[dict[str, Any]] = None,
        *,
        intent: Optional[dict[str, Any]] = None,
        persist_visibility: bool = True) -> dict[str, Any]:
    """Run the Objective Agent. Returns a structured objective dict.

    Pass ``intent`` when you already called ``extract_event_intent`` (e.g. preview UIs)
    to avoid duplicate LLM calls.
    """
    constraints = constraints or {}
    run_id = create_run_id(AGENT_NAME)

    intent = intent if intent is not None else extract_event_intent(brief)

    target_size = constraints.get("target_size") or _coerce_size(
        intent.get("target_size"), brief, 100
    )
    city = (constraints.get("city") or intent.get("city") or "").strip() or _extract_city(brief)

    event_type = (
        constraints.get("event_type")
        or (intent.get("event_type") or "").strip()
        or _extract_event_type(brief)
    )

    desired_attendees = (intent.get("desired_attendees") or "").strip()

    # Goal: structured intent first, then legacy heuristic on full brief
    goal = (intent.get("overall_goal") or "").strip()
    if not goal:
        m = re.search(r"goal[^.]*\.", brief, flags=re.IGNORECASE)
        if m:
            goal = m.group(0).strip()
        else:
            sentences = [s.strip() for s in re.split(r"[.\n]", brief) if s.strip()]
            if sentences:
                goal = max(sentences, key=len)

    event_name = (intent.get("event_name") or "").strip()

    # Pre-fill event date from the brief when the organizer wrote one.
    # Lands on the new top-level event_state["event_date"] (kept distinct
    # from the legacy event_state["event"]["date"] which is unrelated state).
    event_date_iso = (intent.get("event_date") or "").strip() or _extract_date(brief)

    success_metrics = [
        f"{target_size} RSVPs",
        f"{int(target_size * 0.6)}-{int(target_size * 0.7)} actual attendees",
        f"{max(20, int(target_size * 0.3))}+ high-fit attendees aligned with the theme",
        "10 meaningful post-event follow-ups",
    ]

    open_questions = list(DEFAULT_OPEN_QUESTIONS)

    objective = {
        "goal": goal,
        "event_type": event_type,
        "desired_attendees": desired_attendees,
        "target_size": target_size,
        "city": city,
        "success_metrics": success_metrics,
        "open_questions": open_questions,
        "event_name": event_name,
    }

    if event_state is not None:
        ev = event_state.setdefault("event", {})
        if event_name:
            ev["name"] = event_name
        ev["goal"] = goal
        ev["desired_attendees"] = desired_attendees
        ev["target_size"] = target_size
        ev["city"] = city
        ev["format"] = event_type
        ev["success_metrics"] = success_metrics
        # Only pre-fill event_date if extraction succeeded AND the user hasn't
        # already set one (e.g. via the date picker between runs).
        if event_date_iso and not (event_state.get("event_date") or "").strip():
            event_state["event_date"] = event_date_iso
        state_meta = event_state.setdefault("state", {})
        state_meta.setdefault("open_questions", []).extend(open_questions)

    log_agent_run(
        AGENT_NAME,
        run_id=run_id,
        input_summary=f"Raw event brief ({len(brief)} chars)",
        output_summary=(
            f"Normalized {target_size}-person '{event_type}' in {city or 'unspecified city'}; "
            f"goal_len={len(goal)}, desired_attendees_len={len(desired_attendees)}."
        ),
        decisions_made=[
            f"event_type='{event_type}'.",
            f"target_size={target_size}, city='{city}'.",
            "Captured organizer triad: event type, desired attendees, overall goal (when extractable).",
        ],
        reasoning_summary=(
            "intent_extractor supplies event type, desired attendees, and overall goal when "
            "ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still "
            "use constraints, intent fields, and regex fallbacks on the full brief."
        ),
        confidence="medium",
        files_read=[],
        files_written=[],
        next_actions=["Run audience_agent to define ICP and avoid personas."],
        event_state=event_state,
        persist_to_disk=persist_visibility,
    )

    return objective
