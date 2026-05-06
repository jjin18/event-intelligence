"""Event-level metadata endpoints (date, end-time).

GET  /event       — current event date + key fields used by Budget/Attendees
                    headers and the {event_date} message placeholder.
PUT  /event/date  — set event_date (and optional event_end_time).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.routes._state import mutate_state, read_state


router = APIRouter(tags=["event"])


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _days_until(iso: str) -> Optional[int]:
    if not iso:
        return None
    try:
        s = iso.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            d = dt.date()
        except ValueError:
            d = date.fromisoformat(iso)
    except Exception:
        return None
    return (d - _today()).days


@router.get("/event")
async def get_event() -> dict:
    state = read_state()
    iso = state.get("event_date") or ""
    ev = state.get("event") or {}
    return {
        "ok": True,
        "event_date": iso,
        "event_end_time": state.get("event_end_time"),
        "days_until": _days_until(iso),
        "is_past": (_days_until(iso) is not None and _days_until(iso) < 0),
        "name": ev.get("name") or "",
        "city": ev.get("city") or "",
        "format": ev.get("format") or "",
        "target_size": ev.get("target_size") or 0,
    }


class EventDateBody(BaseModel):
    event_date: str = Field("", description="ISO 8601 date or datetime; empty string clears.")
    event_end_time: Optional[str] = Field(None, description="ISO 8601 datetime or null.")


def _validate_iso(s: str, field: str) -> str:
    if not s:
        return ""
    try:
        s2 = s.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(s2)
        except ValueError:
            date.fromisoformat(s)
    except Exception:
        raise HTTPException(400, f"{field} must be ISO 8601 (got {s!r})")
    return s


@router.put("/event/date")
async def put_event_date(body: EventDateBody) -> dict:
    iso = _validate_iso(body.event_date, "event_date")
    end = _validate_iso(body.event_end_time or "", "event_end_time") if body.event_end_time else None

    def _apply(state: dict) -> dict:
        state["event_date"] = iso
        state["event_end_time"] = end
        return state

    mutate_state(_apply)
    return {"ok": True, "event_date": iso, "event_end_time": end, "days_until": _days_until(iso)}


class EventInfoBody(BaseModel):
    """User-editable header fields. Only provided fields are touched —
    omitting a field leaves the existing value alone so the popover can
    submit just the field that changed."""
    name: Optional[str] = None
    city: Optional[str] = None
    format: Optional[str] = None
    target_size: Optional[int] = None


@router.put("/event/info")
async def put_event_info(body: EventInfoBody) -> dict:
    def _apply(state: dict) -> dict:
        ev = state.setdefault("event", {})
        if body.name is not None:
            ev["name"] = body.name.strip()
        if body.city is not None:
            ev["city"] = body.city.strip()
        if body.format is not None:
            ev["format"] = body.format.strip()
        if body.target_size is not None:
            ev["target_size"] = max(0, int(body.target_size))
        return ev

    ev = mutate_state(_apply)
    return {
        "ok": True,
        "name": ev.get("name", ""),
        "city": ev.get("city", ""),
        "format": ev.get("format", ""),
        "target_size": ev.get("target_size", 0),
    }
