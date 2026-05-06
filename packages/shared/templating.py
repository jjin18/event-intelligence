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
}


def _first_name(full: str) -> str:
    if not full:
        return ""
    return full.strip().split()[0] if full.strip() else ""


def _build_context(person: dict[str, Any], event: dict[str, Any]) -> dict[str, str]:
    p = person or {}
    e = event or {}
    name = (p.get("name") or "").strip()
    return {
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
    }


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def render(template: str, person: dict[str, Any], event: dict[str, Any]) -> str:
    """Render a template string with placeholders substituted from person + event.

    Unknown placeholders are left untouched (e.g. {linkedin_url}) — pass them
    through so the user can extend templates without breaking.
    """
    if not template:
        return ""
    ctx = _build_context(person, event)

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return ctx.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(_sub, template)


def render_batch(template: str,
                 people: list[dict[str, Any]],
                 event: dict[str, Any]) -> list[dict[str, Any]]:
    """Render the same template across many people. Returns a list of dicts
    each with: name, email, linkedin_url, rendered, channel."""
    out: list[dict[str, Any]] = []
    for p in people or []:
        rendered = render(template, p, event)
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
