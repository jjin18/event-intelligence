"""Budget tab endpoints.

Single resource at event_state["budget"]:
  {
    "total_budget": 0.0,
    "sponsor_income": 0.0,
    "line_items": [
      {"id", "category", "name", "cost", "cost_text", "status", "source", "source_ref"}
    ]
  }

Status values: "Planned" | "Booked" | "Paid".
Categories are fixed (BUDGET_CATEGORIES); requests with other categories 400.
"""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.routes._state import BUDGET_CATEGORIES, mutate_state, read_state


router = APIRouter(prefix="/budget", tags=["budget"])


_VALID_STATUSES = {"Planned", "Booked", "Paid"}


def _summary(budget: dict) -> dict:
    items = budget.get("line_items") or []
    total = float(budget.get("total_budget") or 0)
    sponsor = float(budget.get("sponsor_income") or 0)
    spent_paid = sum(float(it.get("cost") or 0) for it in items if it.get("status") == "Paid")
    committed = sum(float(it.get("cost") or 0) for it in items if it.get("status") in ("Booked", "Paid"))
    planned = sum(float(it.get("cost") or 0) for it in items if it.get("status") == "Planned")
    # "Spent" for the progress bar = Booked + Paid - Sponsor income (per spec).
    net_spent = max(0.0, committed - sponsor)
    return {
        "total_budget": total,
        "sponsor_income": sponsor,
        "spent": net_spent,
        "spent_paid": spent_paid,
        "committed": committed,
        "planned": planned,
        "remaining": total - net_spent,
        "categories": BUDGET_CATEGORIES,
    }


@router.get("")
async def get_budget() -> dict:
    state = read_state()
    budget = state.get("budget") or {}
    items = budget.get("line_items") or []
    return {
        "ok": True,
        "summary": _summary(budget),
        "line_items": items,
    }


class TotalBody(BaseModel):
    total_budget: float = Field(..., ge=0)


@router.put("/total")
async def put_total(body: TotalBody) -> dict:
    def _apply(state: dict) -> dict:
        state.setdefault("budget", {})["total_budget"] = float(body.total_budget)
        return state["budget"]

    budget = mutate_state(_apply)
    return {"ok": True, "summary": _summary(budget)}


class SponsorBody(BaseModel):
    sponsor_income: float = Field(..., ge=0)


@router.put("/sponsor_income")
async def put_sponsor_income(body: SponsorBody) -> dict:
    def _apply(state: dict) -> dict:
        state.setdefault("budget", {})["sponsor_income"] = float(body.sponsor_income)
        return state["budget"]

    budget = mutate_state(_apply)
    return {"ok": True, "summary": _summary(budget)}


class LineItemBody(BaseModel):
    category: str
    name: str = Field(..., min_length=1)
    cost: float = Field(0.0, ge=0)
    cost_text: Optional[str] = None
    status: str = Field("Planned")
    source: str = Field("manual")
    source_ref: Optional[str] = None


def _validate_category(cat: str) -> str:
    if cat not in BUDGET_CATEGORIES:
        raise HTTPException(400, f"category must be one of {BUDGET_CATEGORIES}")
    return cat


def _validate_status(s: str) -> str:
    if s not in _VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {sorted(_VALID_STATUSES)}")
    return s


@router.post("/line_item")
async def post_line_item(body: LineItemBody) -> dict:
    cat = _validate_category(body.category)
    status = _validate_status(body.status)
    new_id = "li_" + secrets.token_hex(6)
    item = {
        "id": new_id,
        "category": cat,
        "name": body.name.strip(),
        "cost": float(body.cost or 0),
        "cost_text": (body.cost_text or "").strip(),
        "status": status,
        "source": body.source or "manual",
        "source_ref": (body.source_ref or "").strip() or None,
    }

    def _apply(state: dict) -> dict:
        budget = state.setdefault("budget", {"line_items": []})
        budget.setdefault("line_items", []).append(item)
        return budget

    budget = mutate_state(_apply)
    return {"ok": True, "item": item, "summary": _summary(budget)}


class LineItemPatch(BaseModel):
    name: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    cost_text: Optional[str] = None
    status: Optional[str] = None


@router.patch("/line_item/{item_id}")
async def patch_line_item(item_id: str, body: LineItemPatch) -> dict:
    if body.status is not None:
        _validate_status(body.status)

    def _apply(state: dict) -> dict:
        budget = state.setdefault("budget", {"line_items": []})
        items = budget.setdefault("line_items", [])
        for it in items:
            if it.get("id") == item_id:
                if body.name is not None:
                    it["name"] = body.name.strip()
                if body.cost is not None:
                    it["cost"] = float(body.cost)
                if body.cost_text is not None:
                    it["cost_text"] = body.cost_text
                if body.status is not None:
                    it["status"] = body.status
                return {"budget": budget, "item": it}
        raise HTTPException(404, f"line_item {item_id} not found")

    res = mutate_state(_apply)
    return {"ok": True, "item": res["item"], "summary": _summary(res["budget"])}


@router.delete("/line_item/{item_id}")
async def delete_line_item(item_id: str) -> dict:
    def _apply(state: dict) -> dict:
        budget = state.setdefault("budget", {"line_items": []})
        items = budget.setdefault("line_items", [])
        before = len(items)
        budget["line_items"] = [it for it in items if it.get("id") != item_id]
        if len(budget["line_items"]) == before:
            raise HTTPException(404, f"line_item {item_id} not found")
        return budget

    budget = mutate_state(_apply)
    return {"ok": True, "summary": _summary(budget)}


class AutofillVendor(BaseModel):
    """One shortlisted vendor coming from the Org tab's localStorage."""
    category: str
    name: str
    cost: float = 0.0
    cost_text: Optional[str] = None
    source_ref: Optional[str] = None


class AutofillBody(BaseModel):
    vendors: list[AutofillVendor]


@router.post("/autofill_from_shortlist")
async def autofill_from_shortlist(body: AutofillBody) -> dict:
    """Append any shortlisted vendors not already represented in line_items.

    Idempotent: skips vendors whose source_ref/name combination already exists
    as an org_shortlist line item, so calling this on every Budget tab open
    won't create duplicates.
    """
    added: list[dict] = []

    def _apply(state: dict) -> dict:
        budget = state.setdefault("budget", {"line_items": []})
        items = budget.setdefault("line_items", [])
        existing_keys = {
            (it.get("source"), (it.get("source_ref") or "").lower())
            for it in items
            if it.get("source") == "org_shortlist"
        }
        for v in body.vendors:
            if v.category not in BUDGET_CATEGORIES:
                continue
            key = ("org_shortlist", (v.source_ref or v.name or "").lower())
            if key in existing_keys:
                continue
            new_item = {
                "id": "li_" + secrets.token_hex(6),
                "category": v.category,
                "name": v.name.strip(),
                "cost": float(v.cost or 0),
                "cost_text": (v.cost_text or "").strip(),
                "status": "Planned",
                "source": "org_shortlist",
                "source_ref": (v.source_ref or v.name or "").strip(),
            }
            items.append(new_item)
            added.append(new_item)
            existing_keys.add(key)
        return budget

    budget = mutate_state(_apply)
    return {"ok": True, "added": added, "summary": _summary(budget)}
