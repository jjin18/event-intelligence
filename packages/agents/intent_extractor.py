"""Normalize organizer input into three pillars:

1. Event type — format/kind of event being proposed
2. Desired attendees — who should be in the room (organizer's words)
3. Overall goal — what success looks like

Uses Claude when ANTHROPIC_API_KEY is set; otherwise parses simple labeled lines
(Event type: / People we want: / Goal:) so offline templates still work.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

MODEL = "claude-sonnet-4-6"


def _empty_intent() -> dict[str, Any]:
    return {
        "event_type": "",
        "desired_attendees": "",
        "overall_goal": "",
        "target_size": None,
        "city": "",
        "event_name": "",
    }


def extract_event_intent(brief: str) -> dict[str, Any]:
    """Return intent dict; never raises."""
    text = (brief or "").strip()
    if not text:
        return _empty_intent()

    if os.environ.get("ANTHROPIC_API_KEY"):
        llm = _extract_via_llm(text)
        if llm:
            merged = _empty_intent()
            merged.update({k: llm.get(k) or merged[k] for k in merged})
            return merged

    return _extract_labeled_fallback(text)


def _extract_via_llm(brief: str) -> dict[str, Any] | None:
    # File-backed cache by (model, version, brief). Re-running an identical
    # brief is free — no LLM call. Bumps version when the prompt changes.
    from packages.shared import cache as _cache

    cache_parts = (MODEL, "v1", brief)
    cached = _cache.get("intent_extractor", *cache_parts)
    if isinstance(cached, dict):
        return cached

    prompt = f"""An organizer described an event in free text. Extract their intent into JSON only.

Return STRICTLY one JSON object (no markdown fences, no prose) with:
{{
  "event_type": "short phrase: kind/format of event (e.g. curated dinner, hackathon, salon)",
  "desired_attendees": "who they want in the room, in their wording — roles, segments, seniority, vibe",
  "overall_goal": "why they're running it and what success means",
  "target_size": <integer headcount if mentioned, else null>,
  "city": "<venue city if mentioned, else empty string>",
  "event_name": "<short title if mentioned, else empty string>"
}}

If something is not stated, use empty string or null. Infer lightly only when obvious from context.

Organizer message:
{brief}
"""
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        chunks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        raw = "\n".join(chunks).strip()
        payload = raw
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, flags=re.DOTALL)
        if m:
            payload = m.group(1)
        elif not raw.startswith("{"):
            m2 = re.search(r"(\{{.*\}})", raw, flags=re.DOTALL)
            if m2:
                payload = m2.group(1)
        data = json.loads(payload)
        if not isinstance(data, dict):
            return None
        _cache.put("intent_extractor", data, *cache_parts)
        return data
    except Exception:
        return None


def _extract_labeled_fallback(brief: str) -> dict[str, Any]:
    out = _empty_intent()
    lines = brief.splitlines()

    # Accept optional "## Section" markdown headers followed by content until next header
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current, buf
        if not current or not buf:
            current = None
            buf = []
            return
        block = "\n".join(buf).strip()
        if current == "event_type" and block:
            out["event_type"] = block
        elif current == "desired_attendees" and block:
            out["desired_attendees"] = block
        elif current == "overall_goal" and block:
            out["overall_goal"] = block
        current = None
        buf = []

    header_map = {
        "event type": "event_type",
        "type of event": "event_type",
        "format": "event_type",
        "people we want": "desired_attendees",
        "desired attendees": "desired_attendees",
        "who should be there": "desired_attendees",
        "who we want": "desired_attendees",
        "overall goal": "overall_goal",
        "goal": "overall_goal",
        "success": "overall_goal",
    }

    for line in lines:
        stripped = line.strip()
        m_hdr = re.match(r"^#+\s*(.+)$", stripped)
        if m_hdr:
            flush()
            key = m_hdr.group(1).strip().lower().rstrip(":")
            mapped = header_map.get(key)
            if mapped:
                current = mapped
            else:
                current = None
            continue

        m_kv = re.match(
            r"(?i)^(?:event\s+type|type\s+of\s+event|format)\s*:\s*(.*)$", stripped
        )
        if m_kv:
            flush()
            if m_kv.group(1).strip():
                out["event_type"] = m_kv.group(1).strip()
            else:
                current = "event_type"
            continue

        m_kv = re.match(
            r"(?i)^(?:people\s+we\s+want|desired\s+attendees|who\s+(?:we\s+want|should\s+be\s+there))\s*:\s*(.*)$",
            stripped,
        )
        if m_kv:
            flush()
            if m_kv.group(1).strip():
                out["desired_attendees"] = m_kv.group(1).strip()
            else:
                current = "desired_attendees"
            continue

        m_kv = re.match(r"(?i)^(?:overall\s+goal|goal|success)\s*:\s*(.*)$", stripped)
        if m_kv:
            flush()
            if m_kv.group(1).strip():
                out["overall_goal"] = m_kv.group(1).strip()
            else:
                current = "overall_goal"
            continue

        if current:
            buf.append(line)

    flush()

    # If headers didn't fill goals, leave overall_goal empty — objective_agent keeps its heuristic

    return out
