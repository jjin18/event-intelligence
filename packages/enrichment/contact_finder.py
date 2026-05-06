"""LLM + web-search contact enrichment.

For each ranked person, ask Claude to find publicly listed contact info:
work email (only if publicly posted), LinkedIn, X/Twitter, GitHub. We never
guess emails — only return what's verifiable from public sources.

Updates each person dict in place with `email`, `linkedin_url`, `twitter`,
`github`, `contact_sources`, `contact_status`. The CSV column set is
unchanged for the existing fields; new ones land in the `notes` blob and
the JSONB `raw` column when persisted.

Cost: roughly $0.01–0.05 per ~50 people in batches of 10. Requires
ANTHROPIC_API_KEY. Falls back to a no-op if missing.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any


MODEL = "claude-sonnet-4-6"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
BATCH_SIZE = 10


def _build_prompt(people_batch: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f"{i+1}. {p.get('name','')} — {p.get('role','')} @ {p.get('company','')}"
        f"{' — ' + p['linkedin_url'] if p.get('linkedin_url') else ''}"
        for i, p in enumerate(people_batch)
    )
    return f"""For each of the following people, search the public web for
their contact information. Return ONLY publicly posted information — never
fabricate or guess emails.

# People
{rows}

# What to find for each person
- email          (only if publicly posted on a personal site, GitHub
                  profile, conference bio, or similar — NOT scraped from
                  LinkedIn or guessed via firstname@company.com)
- linkedin_url   (canonical https://www.linkedin.com/in/... URL if not
                  already provided)
- twitter        (X/Twitter handle, with leading @)
- github         (GitHub username, no @)
- contact_sources (1-2 short URLs or labels showing where you verified)

# Output
Return STRICTLY a JSON array, one object per person in the SAME order:
[
  {{
    "name": "...",
    "email": "" | "real@email",
    "linkedin_url": "" | "https://...",
    "twitter": "" | "@handle",
    "github": "" | "username",
    "contact_sources": ["url-or-label", "..."]
  }}
]
Empty strings for fields you couldn't verify. NO markdown, NO prose, NO
explanation. Return the array and nothing else."""


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


def discover_contacts(people: list[dict[str, Any]],
                      *,
                      model: str = MODEL,
                      max_searches_per_batch: int = 8,
                      max_tokens: int = 8000) -> tuple[int, dict[str, Any]]:
    """Mutates `people` in-place. Returns (n_enriched, telemetry)."""
    telemetry: dict[str, Any] = {"status": "skipped", "model": model, "batches": 0,
                                 "people_total": len(people), "people_enriched": 0,
                                 "notes": []}

    if not people:
        telemetry["notes"].append("Empty input.")
        return 0, telemetry

    if not os.environ.get("ANTHROPIC_API_KEY"):
        telemetry["notes"].append("ANTHROPIC_API_KEY not set; skipping enrichment.")
        return 0, telemetry

    try:
        import anthropic  # type: ignore
    except ImportError:
        telemetry["notes"].append("anthropic SDK not installed; skipping enrichment.")
        return 0, telemetry

    client = anthropic.Anthropic()
    enriched_count = 0

    for batch_start in range(0, len(people), BATCH_SIZE):
        batch = people[batch_start:batch_start + BATCH_SIZE]
        prompt = _build_prompt(batch)
        web_tool = dict(WEB_SEARCH_TOOL)
        web_tool["max_uses"] = max_searches_per_batch

        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=[web_tool],
            ) as stream:
                response = stream.get_final_message()
        except Exception as e:
            telemetry["notes"].append(f"batch {batch_start}: {e!r}")
            continue

        text = "\n".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        rows = _parse(text)
        # Pair returned rows with input batch by index.
        for i, p in enumerate(batch):
            if i >= len(rows):
                break
            r = rows[i]
            if not isinstance(r, dict):
                continue
            # Only fill empty fields — don't clobber existing data.
            if not p.get("email") and r.get("email"):
                p["email"] = r["email"].strip()
            if not p.get("linkedin_url") and r.get("linkedin_url"):
                p["linkedin_url"] = r["linkedin_url"].strip()
            if r.get("twitter"):
                p["twitter"] = r["twitter"].strip()
            if r.get("github"):
                p["github"] = r["github"].strip()
            srcs = r.get("contact_sources") or []
            if srcs:
                p["contact_sources"] = list(srcs)
            # mark status
            has_any = bool(p.get("email") or p.get("linkedin_url") or p.get("twitter") or p.get("github"))
            p["contact_status"] = "found" if has_any else "not_found"
            if has_any:
                enriched_count += 1

        telemetry["batches"] += 1

    telemetry["status"] = "ok" if enriched_count else "empty"
    telemetry["people_enriched"] = enriched_count
    return enriched_count, telemetry
