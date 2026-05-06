"""Outreach endpoints.

POST /contacts/discover  — enrich the latest event's people with public
                           contact info via LLM + web search.
POST /messages/render    — render a template across N selected people.

Sending is intentionally NOT a server endpoint. The browser uses mailto:
URIs so the user's own mail client takes the final action — no SMTP creds,
no automated mass-send.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from packages.shared import tokens as token_mod


router = APIRouter(tags=["outreach"])


_REPO_ROOT = Path(__file__).resolve().parents[3]
_RANKED_CSV = _REPO_ROOT / "data" / "ranked_people.csv"
_EVENT_STATE = _REPO_ROOT / "data" / "event_state.json"


def _load_people() -> list[dict]:
    if not _RANKED_CSV.exists():
        return []
    with _RANKED_CSV.open() as f:
        return list(csv.DictReader(f))


def _load_full_state() -> dict:
    if not _EVENT_STATE.exists():
        return {}
    try:
        return json.loads(_EVENT_STATE.read_text())
    except json.JSONDecodeError:
        return {}


def _load_event() -> dict:
    """Backwards-compat wrapper: returns the legacy event sub-dict.

    Augments it with the new top-level ``event_date`` (passed via the
    ``_event_date`` key the templating module looks at first) so callers that
    still take the old shape get the new placeholder data without code change.
    """
    state = _load_full_state()
    event = dict(state.get("event") or {})
    if state.get("event_date"):
        event["_event_date"] = state["event_date"]
    return event


def _save_people(people: list[dict]) -> None:
    """Rewrite the ranked CSV preserving column order."""
    if not people:
        return
    from packages.shared.event_state import PERSON_CSV_COLUMNS
    # Allow new optional columns to slip in (twitter, github, contact_status).
    extra_cols = []
    for p in people:
        for k in p.keys():
            if k not in PERSON_CSV_COLUMNS and k not in extra_cols:
                extra_cols.append(k)
    cols = list(PERSON_CSV_COLUMNS) + extra_cols
    with _RANKED_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for p in people:
            writer.writerow({c: p.get(c, "") for c in cols})


# -------- Contact discovery --------

class DiscoverRequest(BaseModel):
    only_missing: bool = Field(True, description="Skip people who already have email or LinkedIn.")
    limit: Optional[int] = Field(25, description="Max people to enrich this run (defaults to top 25 to keep cost bounded).")


@router.post("/contacts/discover")
async def discover_contacts_route(body: DiscoverRequest) -> dict:
    people = _load_people()
    if not people:
        raise HTTPException(404, "No ranked people yet — run the pipeline first.")

    targets = people
    if body.only_missing:
        targets = [p for p in people if not (p.get("email") or p.get("linkedin_url"))]
    if body.limit is not None:
        targets = targets[: max(0, int(body.limit))]

    if not targets:
        return {"ok": True, "enriched": 0, "total": len(people),
                "note": "All people already have at least one contact field."}

    def _execute():
        from packages.enrichment.contact_finder import discover_contacts
        return discover_contacts(targets)

    try:
        n_enriched, telemetry = await run_in_threadpool(_execute)
    except Exception as e:
        raise HTTPException(502, f"Contact discovery failed: {e!s}")

    # The targets list is mutated in place — write everything back to CSV.
    _save_people(people)
    return {"ok": True, "enriched": n_enriched, "total": len(people),
            "considered": len(targets), "telemetry": telemetry}


# -------- Template rendering --------

class RenderRequest(BaseModel):
    template: str = Field(..., min_length=1)
    names: Optional[List[str]] = Field(None, description="Names to render for. If None, uses top_n.")
    top_n: Optional[int] = Field(None, description="Render for the first N rows of ranked CSV.")


def _confirm_link_base(request: Request) -> str:
    """Build the absolute URL prefix for /confirm/{token}.

    Honors X-Forwarded-Proto/Host so the link works behind proxies/Railway,
    falling back to the request's scheme + host.
    """
    fwd_proto = request.headers.get("x-forwarded-proto")
    fwd_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if fwd_proto and fwd_host:
        return f"{fwd_proto}://{fwd_host}/confirm/"
    return f"{request.url.scheme}://{request.url.netloc}/confirm/"


@router.post("/messages/render")
async def render_messages(body: RenderRequest, request: Request) -> dict:
    people = _load_people()
    if not people:
        raise HTTPException(404, "No ranked people yet — run the pipeline first.")

    if body.names:
        wanted = {n.strip().lower() for n in body.names if n.strip()}
        selected = [p for p in people if (p.get("name") or "").strip().lower() in wanted]
    elif body.top_n is not None:
        selected = people[: max(0, int(body.top_n))]
    else:
        selected = people[:1]  # default: just the first person

    from packages.shared.templating import render_batch

    state = _load_full_state()
    event = dict(state.get("event") or {})
    event_date = state.get("event_date") or ""
    if event_date:
        event["_event_date"] = event_date

    # Per-recipient confirm link via signed token. Each token is unique to
    # (attendee_id, event identity) so clicking one person's link only ever
    # confirms that person.
    base = _confirm_link_base(request)
    extras: dict[str, dict[str, str]] = {}
    for p in selected:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        aid = token_mod.attendee_id_for(name, p.get("email") or "")
        token = token_mod.issue(aid, event, event_date_iso=event_date)
        extras[name] = {"confirm_link": base + token}

    rendered = render_batch(body.template, selected, event, per_person_extras=extras)
    return {"ok": True, "count": len(rendered), "messages": rendered}
