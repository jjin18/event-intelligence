"""LLM-powered audience designer.

Given an event proposal, calls Claude to produce the full audience definition:
ICP personas, avoid personas, scoring rubric, and target room mix. Replaces
the hand-tuned hardcoded persona libraries that previously lived in
`audience_agent.py`.

Output shape matches what `attendee_fit.score()` and `room_balance_agent.run()`
expect, so no downstream code changes are needed.

Cost: one API call (no web search), a few cents. Requires ANTHROPIC_API_KEY.
Falls back to a minimal generic library if the SDK or key is missing — the
fallback is intentionally NOT theme-specific.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any


import os
# Haiku is plenty for structured persona design and ~10x cheaper than Sonnet.
# Override with ANTHROPIC_DESIGN_MODEL=claude-sonnet-4-6 for higher quality.
MODEL = os.environ.get("ANTHROPIC_DESIGN_MODEL", "claude-haiku-4-5-20251001")


# Minimal generic fallback used only when the LLM is unavailable. NOT
# theme-specific. The system will still run; it just won't know your domain.
_GENERIC_FALLBACK = {
    "audience_icp": [
        {"name": "decision_maker", "description": "Founders, CEOs, and senior decision-makers in the event's domain.",
         "weight": 9, "signals": ["founder", "ceo", "co-founder", "cofounder", "head of"]},
        {"name": "hands_on_builder", "description": "Engineers, designers, and operators actively shipping in the domain.",
         "weight": 8, "signals": ["engineer", "developer", "builder", "designer", "lead"]},
        {"name": "domain_expert", "description": "Researchers, writers, and recognized experts.",
         "weight": 7, "signals": ["researcher", "scientist", "writer", "professor"]},
        {"name": "community_connector", "description": "Community organizers, DevRel, and high-signal connectors.",
         "weight": 6, "signals": ["community", "organizer", "devrel", "advocate"]},
        {"name": "investor_high_signal", "description": "Investors with operator backgrounds.",
         "weight": 4, "signals": ["partner", "principal", "venture"]},
    ],
    "avoid_personas": [
        {"name": "sales_only", "description": "Sales-only attendees with no domain context.",
         "penalty": 12, "signals": ["account executive", "sdr", "ae", "enterprise sales"]},
        {"name": "generic_networker", "description": "Generic networkers with no clear connection to the theme.",
         "penalty": 15, "signals": ["bd", "business development"]},
        {"name": "low_context", "description": "Attendees with no clear connection to the theme.",
         "penalty": 10, "signals": []},
    ],
    "scoring_rubric": {
        "max_score": 100,
        "persona_weights": {},  # filled in below
        "avoid_penalties": {},
        "bonuses": {
            "city_match": 10,
            "founder_or_lead_signal": 8,
            "github_or_writing_signal": 6,
            "warm_intro": 6,
        },
        "thresholds": {"high": 75, "medium": 55, "low": 35},
        "notes": "Generic fallback rubric. LLM-designed when ANTHROPIC_API_KEY is set.",
    },
    "target_mix": {
        "decision_maker": 0.25,
        "hands_on_builder": 0.40,
        "domain_expert": 0.15,
        "community_connector": 0.15,
        "investor_high_signal": 0.05,
    },
    "approval_criteria": [
        "Clear connection to the event theme.",
        "Currently building, leading, or operating in a relevant role.",
        "Likely to contribute to the room.",
    ],
    "data_to_collect": ["name", "company", "role", "linkedin_url", "email",
                        "what they're currently working on", "why they want to attend"],
    "sourcing_channels": [
        {"channel": "Personal/team networks (warm intros)", "priority": "high"},
        {"channel": "Past attendee lists from similar events", "priority": "high"},
        {"channel": "Public profiles relevant to the theme", "priority": "medium"},
    ],
}

# fill in defaults from weights/penalties so the fallback rubric is self-consistent
for _p in _GENERIC_FALLBACK["audience_icp"]:
    _GENERIC_FALLBACK["scoring_rubric"]["persona_weights"][_p["name"]] = _p["weight"] * 8
for _p in _GENERIC_FALLBACK["avoid_personas"]:
    _GENERIC_FALLBACK["scoring_rubric"]["avoid_penalties"][_p["name"]] = _p["penalty"]


def _build_prompt(event_brief: str) -> str:
    return f"""You are designing the audience definition for a curated event. The text may begin
with explicit sections (event type, who belongs in the room, overall goal) — treat those as
hard constraints, then use the rest for nuance. Do NOT default to generic personas — derive
personas that match the *specific* domain, format, and goals described.

# Event proposal
{event_brief}

# What to produce

Return STRICTLY a JSON object (no surrounding prose, no markdown fences) with this exact shape:

{{
  "audience_icp": [
    {{
      "name": "snake_case_persona_name",
      "description": "1-sentence description of who this persona is.",
      "weight": <integer 4-10, higher = more important to room quality>,
      "signals": ["lowercase substring keywords", "...", "..."]
    }}
    // 5-9 ICP personas, ordered by importance
  ],
  "avoid_personas": [
    {{
      "name": "snake_case_name",
      "description": "Why this persona hurts the room.",
      "penalty": <integer 5-25>,
      "signals": ["lowercase substring keywords"]
    }}
    // 3-5 avoid personas
  ],
  "scoring_rubric": {{
    "max_score": 100,
    "persona_weights": {{ "<persona_name>": <int>, ... }}, // typically weight*8
    "avoid_penalties": {{ "<avoid_name>": <int>, ... }},   // copy from avoid_personas
    "bonuses": {{
      "city_match": 10,
      "founder_or_lead_signal": 8,
      "github_or_writing_signal": 6,
      "warm_intro": 6
    }},
    "thresholds": {{ "high": 75, "medium": 55, "low": 35 }},
    "notes": "1 sentence explaining the rubric design choices."
  }},
  "target_mix": {{ "<persona_name>": <float between 0 and 1>, ... }},
  // target_mix values must sum to ~1.0; use the same persona names as audience_icp.
  "approval_criteria": ["bullet-string", "..."],
  "data_to_collect": ["field name", "..."],
  "sourcing_channels": [
    {{ "channel": "where to source this persona", "priority": "high|medium|low" }}
  ]
}}

# Critical rules
- Persona names MUST be snake_case and unique.
- "signals" are case-insensitive substrings checked against role/company/notes — choose distinctive, non-overlapping keywords (e.g. for a crypto event use "solidity"/"zk"/"protocol", not "ai" which is too generic).
- "weight" reflects how much someone in this persona elevates the room.
- "target_mix" percentages sum to ~1.0 and use the SAME persona names as in audience_icp.
- Tailor everything to the actual event described — derive personas from the proposal, do not output a generic catch-all.
- Return ONLY the JSON object. No explanation, no markdown."""


def design_audience(event_brief: str, *, model: str = MODEL,
                    max_tokens: int = 4000) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (audience_design_dict, telemetry_dict)."""
    telemetry: dict[str, Any] = {"status": "fallback", "model": model, "notes": []}

    if not event_brief.strip():
        telemetry["notes"].append("Empty brief; using generic fallback.")
        return _GENERIC_FALLBACK, telemetry

    if not os.environ.get("ANTHROPIC_API_KEY"):
        telemetry["notes"].append("ANTHROPIC_API_KEY not set; using generic fallback.")
        return _GENERIC_FALLBACK, telemetry

    # Cache hit on identical brief + model = no LLM call.
    from packages.shared import cache as _cache
    cached = _cache.get("audience_designer", model, "v1", event_brief)
    if cached is not None:
        telemetry["status"] = "cached"
        telemetry["personas"] = [p.get("name") for p in cached.get("audience_icp", [])]
        telemetry["notes"].append("Cache hit; no LLM call billed.")
        return cached, telemetry

    try:
        import anthropic  # type: ignore
    except ImportError:
        telemetry["notes"].append("anthropic SDK not installed; using generic fallback.")
        return _GENERIC_FALLBACK, telemetry

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": _build_prompt(event_brief)}],
    )
    text_chunks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    raw = "\n".join(text_chunks).strip()

    parsed = _parse_audience(raw)
    if not parsed:
        telemetry["notes"].append("LLM output failed to parse; using generic fallback.")
        return _GENERIC_FALLBACK, telemetry

    telemetry["status"] = "ok"
    telemetry["personas"] = [p["name"] for p in parsed.get("audience_icp", [])]
    telemetry["raw_text_len"] = len(raw)
    _cache.put("audience_designer", parsed, model, "v1", event_brief)
    if hasattr(response, "usage"):
        telemetry["usage"] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
    return parsed, telemetry


def _parse_audience(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, flags=re.DOTALL)
    payload = m.group(1) if m else raw
    if not payload.lstrip().startswith("{"):
        m2 = re.search(r"(\{.*\})", payload, flags=re.DOTALL)
        if m2:
            payload = m2.group(1)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    # minimal shape validation
    if not isinstance(data, dict) or "audience_icp" not in data:
        return None
    return data
