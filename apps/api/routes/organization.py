"""Organization tab — venues / caterers / sponsors search.

POST /org/search  — body: {category, query, sort?}
                    returns: {ok, category, count, results, telemetry}

Sort happens server-side after cache/results return so the wire format
is consistent regardless of cache hit. Save/shortlist is client-side
(localStorage) — no server route needed for it.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


router = APIRouter(tags=["organization"])

ALLOWED_CATEGORIES = {"venues", "caterers", "sponsors"}
ALLOWED_SORTS = {"relevance", "cost", "rating"}


class OrgSearchRequest(BaseModel):
    category: str = Field(..., description="venues | caterers | sponsors")
    query: dict[str, Any] = Field(default_factory=dict)
    sort: Optional[str] = Field("relevance", description="relevance | cost | rating")


def _cost_key(item: dict, category: str) -> float:
    """Best-effort numeric extraction for cost sorting."""
    import re
    text_field = {
        "venues": "rental_fee",
        "caterers": "price_per_head",
        "sponsors": "typical_sponsorship_amount",
    }.get(category, "")
    text = str(item.get(text_field) or "")
    nums = re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if not nums:
        return float("inf")  # unknowns sort last when ascending
    return float(nums[0])


def _sort_results(results: list[dict], category: str, sort: str) -> list[dict]:
    if sort == "cost":
        return sorted(results, key=lambda r: _cost_key(r, category))
    if sort == "rating":
        return sorted(results, key=lambda r: float(r.get("rating") or 0), reverse=True)
    return results  # relevance = LLM order


@router.post("/org/search")
async def org_search(body: OrgSearchRequest) -> dict:
    if body.category not in ALLOWED_CATEGORIES:
        raise HTTPException(400, f"category must be one of {sorted(ALLOWED_CATEGORIES)}")
    sort = body.sort if body.sort in ALLOWED_SORTS else "relevance"

    def _execute():
        from packages.sourcing.org_search import search
        return search(body.category, body.query)

    try:
        results, telemetry = await run_in_threadpool(_execute)
    except Exception as e:
        msg = str(e) or repr(e)
        if "credit balance is too low" in msg.lower():
            msg = ("Anthropic account is out of credits. Top up at "
                   "https://console.anthropic.com/settings/billing")
        raise HTTPException(502, msg)

    sorted_results = _sort_results(results, body.category, sort)
    return {"ok": True, "category": body.category, "sort": sort,
            "count": len(sorted_results), "results": sorted_results,
            "telemetry": telemetry}
