"""LLM + web-search sourcing for the Organization tab.

Three categories (venues / caterers / sponsors) share the same LLM call shape:
build a category-specific prompt, ask Claude to web-search and return JSON
matching a known schema, parse, return.

Cached by (category, canonicalized query) so the same search is free on
repeat. Keep web search budget small (~6 searches) since per-result detail
matters less than for people sourcing.

Cost: ~\\$0.20–0.40 per fresh search, \\$0 cached. Requires ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any


WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
MODEL = os.environ.get("ANTHROPIC_ORG_MODEL", "claude-sonnet-4-6")


# ---------- per-category prompt + schema ----------

VENUE_SCHEMA = """{
  "name": "venue name",
  "address": "street address",
  "city": "city",
  "capacity": <int — max attendees>,
  "rental_fee": "<text — flat fee or hourly/daily — e.g. '$3,500 day rate' or '$200/hr, 4hr min'>",
  "minimum_spend": "<text — F&B or other minimums — empty if none>",
  "amenities": ["AV equipment", "wifi", "kitchen", "..."],
  "rating": <float 0-5 — leave 0 if unknown>,
  "photo_url": "<url to a representative photo if you found one>",
  "contact_email": "",
  "contact_phone": "",
  "website": "<venue website or listing url>",
  "description": "1-2 sentence summary of the space",
  "source_url": "where you verified the listing"
}"""

CATERER_SCHEMA = """{
  "name": "caterer name",
  "cuisine_type": "primary cuisine — e.g. Mediterranean, Italian, Pan-Asian",
  "dietary_accommodations": ["vegan", "gluten-free", "halal", "..."],
  "location": "city / service area",
  "price_per_head": "<text — e.g. '$45-65/person' or 'starting at $30pp'>",
  "pricing_tiers": [
    {"name": "drop-off", "price": "$25-35pp"},
    {"name": "full-service", "price": "$60-90pp"}
  ],
  "minimum_order": "<text — e.g. '$500 minimum' or '20 person minimum'>",
  "rating": <float 0-5 — 0 if unknown>,
  "contact_email": "",
  "contact_phone": "",
  "website": "<caterer website>",
  "description": "1-2 sentence summary of style / specialty",
  "source_url": "where you verified"
}"""

SPONSOR_SCHEMA = """{
  "name": "company name",
  "industry": "primary industry",
  "company_size": "headcount range — e.g. '500-1000', 'Series B (200 emp)'",
  "typical_sponsorship_amount": "<text — e.g. '$10-50k tier sponsorships' or 'in-kind only'>",
  "past_events_sponsored": ["Devcon 2024", "ETHGlobal Tokyo", "..."],
  "budget_range": "<text — annual marketing/community spend if you can find it>",
  "contact_email": "",
  "contact_person": "<community / DevRel / partnerships lead if known>",
  "website": "company website or partnerships page",
  "description": "1-2 sentence summary of why this is a plausible sponsor",
  "source_url": "where you verified the sponsorship history"
}"""


def _build_prompt(category: str, query: dict[str, Any]) -> str:
    if category == "venues":
        schema = VENUE_SCHEMA
        focus = (
            "Find real, currently-listed event venues. Only include venues that "
            "actually exist on Peerspace, Eventbrite Venues, BizBash, the venue's "
            "own site, or similar public listings. Do NOT invent venues."
        )
        filters = (
            f"Location: {query.get('location') or 'any'}\n"
            f"Capacity needed: {query.get('capacity') or 'any'}\n"
            f"Date/availability: {query.get('availability') or 'flexible'}\n"
            f"Required amenities: {query.get('amenities') or 'none specified'}\n"
            f"Budget: {query.get('budget') or 'flexible'}"
        )
    elif category == "caterers":
        schema = CATERER_SCHEMA
        focus = (
            "Find real catering companies actively serving the requested area. "
            "Only include caterers with a real website / public reviews; do not "
            "invent businesses."
        )
        filters = (
            f"Location: {query.get('location') or 'any'}\n"
            f"Cuisine: {query.get('cuisine') or 'flexible'}\n"
            f"Dietary needs: {query.get('dietary') or 'none specified'}\n"
            f"Headcount: {query.get('headcount') or 'unspecified'}\n"
            f"Budget per head: {query.get('budget_per_head') or 'flexible'}"
        )
    elif category == "sponsors":
        schema = SPONSOR_SCHEMA
        focus = (
            "Identify real companies with a track record of sponsoring events in "
            "the target industry. Use sponsor lists from past events, company "
            "DevRel pages, and partnership announcements as evidence."
        )
        filters = (
            f"Industry / theme: {query.get('industry') or 'unspecified'}\n"
            f"Company size: {query.get('size') or 'any'}\n"
            f"Sponsorship budget range: {query.get('budget') or 'any tier'}\n"
            f"Notes: {query.get('notes') or '-'}"
        )
    else:
        raise ValueError(f"Unknown category: {category}")

    n = max(1, min(int(query.get("limit") or 12), 25))
    return f"""You are sourcing real, publicly-listed options for an event organizer's "Organization" tool.

# Category
{category}

# Filters
{filters}

# Sourcing rules
{focus}

# Output
Return STRICTLY a JSON array of ~{n} objects matching this schema, with no surrounding prose, no markdown fences:

[
  {schema}
]

Return ONLY the JSON array."""


def _parse(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    m = re.search(r"```(?:json)?\s*(\[.*\])\s*```", raw, flags=re.DOTALL)
    payload = m.group(1) if m else raw
    if not payload.lstrip().startswith("["):
        m2 = re.search(r"(\[.*\])", payload, flags=re.DOTALL)
        if m2:
            payload = m2.group(1)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def search(category: str, query: dict[str, Any], *,
           model: str = MODEL,
           max_searches: int = 6,
           max_tokens: int = 12000) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (results, telemetry). Empty list if API key/SDK missing."""
    telemetry: dict[str, Any] = {"status": "skipped", "category": category,
                                 "model": model, "notes": []}

    if category not in {"venues", "caterers", "sponsors"}:
        telemetry["notes"].append(f"unknown category: {category}")
        return [], telemetry

    if not os.environ.get("ANTHROPIC_API_KEY"):
        telemetry["notes"].append("ANTHROPIC_API_KEY not set; skipping search.")
        return [], telemetry

    # canonicalize query for cache key
    canonical_query = json.dumps(query, sort_keys=True, default=str)

    # cache check
    from packages.shared import cache as _cache
    cache_parts = (model, "v1", category, canonical_query)
    cached = _cache.get("org_search", *cache_parts)
    if cached is not None:
        telemetry["status"] = "cached"
        telemetry["count"] = len(cached)
        telemetry["notes"].append("Cache hit; no LLM call billed.")
        return cached, telemetry

    try:
        import anthropic  # type: ignore
    except ImportError:
        telemetry["notes"].append("anthropic SDK not installed; skipping search.")
        return [], telemetry

    prompt = _build_prompt(category, query)
    web_tool = dict(WEB_SEARCH_TOOL)
    web_tool["max_uses"] = max_searches

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        tools=[web_tool],
    ) as stream:
        response = stream.get_final_message()

    text = "\n".join(b.text for b in response.content if getattr(b, "type", "") == "text")
    results = _parse(text)
    telemetry["status"] = "ok" if results else "empty"
    telemetry["count"] = len(results)
    if hasattr(response, "usage"):
        stu = getattr(response.usage, "server_tool_use", None)
        # ServerToolUsage is a namedtuple-ish object — serialize to a plain dict.
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
    if results:
        _cache.put("org_search", results, *cache_parts)
    return results, telemetry
