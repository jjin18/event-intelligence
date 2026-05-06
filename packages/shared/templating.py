"""Minimal placeholder template renderer for outreach messages.

Supports a focused set of fields drawn from the canonical person schema +
event dict. Unknown / empty placeholders fall back to friendly defaults so
no rendered message contains literal "{name}" garbage.

Example:
    template = "Hi {name}, I'd love to invite you to our {event} alongside other {role}s building at {company}-style teams."
    render(template, person, event)
    # -> "Hi Alex, I'd love to invite you to our crypto hackathon alongside other Founders building at Loop AI-style teams."
"""
from __future__ import annotations

import re
from typing import Any


# Default fallbacks when a placeholder field is missing or empty.
FALLBACKS: dict[str, str] = {
    "name": "there",
    "first_name": "there",
    "company": "your team",
    "role": "builder",
    "persona": "builder",
    "event": "the event",
    "event_name": "the event",
    "event_type": "event",
    "city": "the city",
    "goal": "the event's goal",
    "event_date": "TBD",
    "confirm_link": "",
}


def _first_name(full: str) -> str:
    if not full:
        return ""
    return full.strip().split()[0] if full.strip() else ""


def _human_date(iso: str) -> str:
    """Render an ISO 8601 date/datetime as a friendly string for outreach.

    Returns the input unchanged if it can't be parsed — keeps templates safe.
    """
    if not iso:
        return ""
    s = iso.strip()
    if not s:
        return ""
    try:
        from datetime import datetime
        # Accept date or datetime; tolerate trailing Z.
        s2 = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s2)
            return dt.strftime("%a, %b %-d") if not _has_time(s) else dt.strftime("%a, %b %-d at %-I:%M %p")
        except ValueError:
            from datetime import date
            return date.fromisoformat(s).strftime("%a, %b %-d")
    except Exception:
        return s


def _has_time(iso: str) -> bool:
    return "T" in iso or " " in iso


def _build_context(person: dict[str, Any],
                   event: dict[str, Any],
                   extras: dict[str, str] | None = None) -> dict[str, str]:
    p = person or {}
    e = event or {}
    name = (p.get("name") or "").strip()
    # event_date can come from the new top-level event_state["event_date"]
    # (passed in as event["_event_date"]) or fall back to legacy event["date"].
    raw_date = (e.get("_event_date") or e.get("date") or "").strip()
    ctx = {
        "name": name or FALLBACKS["name"],
        "first_name": _first_name(name) or FALLBACKS["first_name"],
        "company": (p.get("company") or "").strip() or FALLBACKS["company"],
        "role": (p.get("role") or "").strip() or FALLBACKS["role"],
        "persona": (p.get("persona") or "").strip() or FALLBACKS["persona"],
        "event": (e.get("name") or e.get("format") or "").strip() or FALLBACKS["event"],
        "event_name": (e.get("name") or "").strip() or FALLBACKS["event_name"],
        "event_type": (e.get("format") or "").strip() or FALLBACKS["event_type"],
        "city": (e.get("city") or "").strip() or FALLBACKS["city"],
        "goal": (e.get("goal") or "").strip() or FALLBACKS["goal"],
        "event_date": _human_date(raw_date) or FALLBACKS["event_date"],
        "confirm_link": FALLBACKS["confirm_link"],
    }
    if extras:
        for k, v in extras.items():
            if v is not None:
                ctx[k] = str(v)
    return ctx


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def render(template: str,
           person: dict[str, Any],
           event: dict[str, Any],
           extras: dict[str, str] | None = None) -> str:
    """Render a template string with placeholders substituted from person + event.

    Unknown placeholders are left untouched (e.g. {linkedin_url}) — pass them
    through so the user can extend templates without breaking.

    ``extras`` lets callers inject per-recipient values (e.g. confirm_link).
    """
    if not template:
        return ""
    ctx = _build_context(person, event, extras=extras)

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return ctx.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(_sub, template)


def render_batch(template: str,
                 people: list[dict[str, Any]],
                 event: dict[str, Any],
                 per_person_extras: dict[str, dict[str, str]] | None = None) -> list[dict[str, Any]]:
    """Render the same template across many people. Returns a list of dicts
    each with: name, email, linkedin_url, rendered, channel.

    ``per_person_extras`` is keyed by person name; values are extra placeholder
    substitutions (e.g. {"Alex Doe": {"confirm_link": "https://..."}}).
    """
    out: list[dict[str, Any]] = []
    extras_by_name = per_person_extras or {}
    for p in people or []:
        extras = extras_by_name.get((p.get("name") or "").strip())
        rendered = render(template, p, event, extras=extras)
        email = (p.get("email") or "").strip()
        linkedin = (p.get("linkedin_url") or "").strip()
        # Pick the best available channel.
        if email:
            channel = "email"
        elif linkedin:
            channel = "linkedin"
        else:
            channel = "none"
        out.append({
            "name": p.get("name", ""),
            "company": p.get("company", ""),
            "role": p.get("role", ""),
            "persona": p.get("persona", ""),
            "email": email,
            "linkedin_url": linkedin,
            "channel": channel,
            "rendered": rendered,
        })
    return out
