"""LLM-powered candidate curator.

Given an event brief + audience ICP, calls Claude with the server-side web
search tool to source real candidate attendees from public information. The
target count is driven by the event's `target_size` (extracted from the brief
by objective_agent), not hardcoded.

Returns a list of dicts conforming to the canonical person schema in
`packages/shared/event_state.py`. The pipeline's rule-based scorer then
ranks/buckets them — same contract as before.

Cost: a few cents per run. Requires ANTHROPIC_API_KEY env var.
Falls back to an empty list (and logs the reason) if the SDK or key is missing.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from packages.shared.event_state import empty_person


import os
# Sonnet by default — candidate synthesis from search results benefits from
# the bigger model. Override with ANTHROPIC_CURATOR_MODEL=claude-haiku-4-5-20251001
# to cut cost ~3-5x at some recall loss.
MODEL = os.environ.get("ANTHROPIC_CURATOR_MODEL", "claude-sonnet-4-6")
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
DEFAULT_OVERSOURCE_FACTOR = 1.1  # was 1.5 — extra bench depth wasn't worth the cost


def _build_prompt(event_brief: str, target_count: int,
                  audience_icp: list[dict], avoid_personas: list[dict]) -> str:
    icp_lines = "\n".join(
        f"- **{p['name']}** (weight {p.get('weight', '-')}): {p.get('description','')}"
        for p in audience_icp
    )
    avoid_lines = "\n".join(
        f"- **{p['name']}**: {p.get('description','')}"
        for p in avoid_personas
    )
    return f"""You are sourcing real candidate attendees for a curated event. Use web search to find publicly-known people who fit the event's ICP, citing public information only.

# Event proposal
{event_brief}

# Target count
Find ~{target_count} candidates. Bias toward HIGH-SIGNAL public figures (founders, named CTO/CEOs, well-known engineers, public researchers, prominent auditors, named DevRel, GP-level investors).

# ICP personas (in priority order)
{icp_lines}

# Avoid personas
{avoid_lines}

# Sourcing rules
- Real people only. No fabricated names. If you can't verify someone publicly, skip them.
- Public information only. No private emails. Leave email blank.
- Use web search aggressively across categories: protocol founders, smart-contract engineers, ZK/cryptography researchers, wallet/AA builders, DeFi engineers, security auditors (Code4rena/Spearbit top), DevRel, crypto-native investors with technical/operator backgrounds.
- Each row: include the person's name, company, role, public LinkedIn or X URL if you find one (else blank), 1-2 sentence "notes" with concrete signals (what they built, where they work, public credentials), and a "source" describing where you verified them.
- Distribute across personas — don't return 50 founders.

# Output format
Return STRICTLY a JSON array of objects matching this schema, with NO surrounding prose, NO markdown fences, NO explanation:

[
  {{
    "name": "Real Full Name",
    "company": "Company",
    "role": "Title",
    "linkedin_url": "https://... or empty string",
    "email": "",
    "source": "web_search:<short citation>",
    "persona": "<one of the ICP persona names above, lowercased exactly>",
    "notes": "1-2 sentence signal-rich blurb that includes keywords matching the persona (e.g. 'Solidity', 'zk-SNARK', 'DevRel', 'audit')."
  }}
]

Return the array and nothing else."""


def curate(event_brief: str,
           target_count: int,
           audience_icp: list[dict],
           avoid_personas: list[dict],
           *,
           oversource_factor: float = DEFAULT_OVERSOURCE_FACTOR,
           model: str = MODEL,
           max_tokens: int = 16000,
           max_searches: int = 10) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (people_list, telemetry_dict).

    people_list conforms to the canonical person schema. telemetry_dict has
    `status`, `model`, `usage`, and `notes` for the visibility logger.
    """
    telemetry: dict[str, Any] = {
        "status": "skipped",
        "model": model,
        "target_count": target_count,
        "notes": [],
    }

    if not os.environ.get("ANTHROPIC_API_KEY"):
        telemetry["notes"].append("ANTHROPIC_API_KEY not set; skipping live curation.")
        return [], telemetry

    try:
        import anthropic  # type: ignore
    except ImportError:
        telemetry["notes"].append("anthropic SDK not installed; skipping live curation.")
        return [], telemetry

    requested = max(target_count, int(round(target_count * oversource_factor)))
    prompt = _build_prompt(event_brief, requested, audience_icp, avoid_personas)

    # Cache hit on identical prompt = no LLM call, no web search bill.
    from packages.shared import cache as _cache
    cache_parts = (model, "v2", str(requested), prompt)
    cached = _cache.get("llm_curator", *cache_parts)
    if cached is not None:
        telemetry["status"] = "cached"
        telemetry["people_returned"] = len(cached)
        telemetry["notes"].append("Cache hit; no LLM call or web searches billed.")
        return cached, telemetry

    client = anthropic.Anthropic()
    web_tool = dict(WEB_SEARCH_TOOL)
    web_tool["max_uses"] = max_searches  # cap web search usage per run

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        tools=[web_tool],
    ) as stream:
        response = stream.get_final_message()

    # Concatenate all text blocks from the final assistant turn.
    text_chunks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    raw = "\n".join(text_chunks).strip()

    people = _parse_people(raw)
    telemetry["status"] = "ok" if people else "empty"
    telemetry["raw_text_len"] = len(raw)
    telemetry["people_returned"] = len(people)
    if people:
        _cache.put("llm_curator", people, *cache_parts)
    if hasattr(response, "usage"):
        stu = getattr(response.usage, "server_tool_use", None)
        stu_dict = None
        if stu is not None:
            stu_dict = {
                "web_search_requests": getattr(stu, "web_search_requests", 0),
                "web_fetch_requests": getattr(stu, "web_fetch_requests", 0),
            }
        telemetry["usage"] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "server_tool_use": stu_dict,
        }

    return people, telemetry


def _parse_people(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    # tolerate fenced output
    m = re.search(r"```(?:json)?\s*(\[.*\])\s*```", raw, flags=re.DOTALL)
    payload = m.group(1) if m else raw
    # find the first JSON array if extra prose snuck in
    if not payload.lstrip().startswith("["):
        m2 = re.search(r"(\[.*\])", payload, flags=re.DOTALL)
        if m2:
            payload = m2.group(1)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        person = empty_person()
        for k in ("name", "company", "role", "linkedin_url", "email",
                  "source", "persona", "notes"):
            v = row.get(k)
            if isinstance(v, str) and v.strip():
                person[k] = v.strip()
        # don't trust LLM-supplied scores; the rule-based scorer assigns these
        person["fit_score"] = None
        person["priority"] = ""
        if person["name"]:
            out.append(person)
    return out
