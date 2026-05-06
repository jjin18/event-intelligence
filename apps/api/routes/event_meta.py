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
    return {
        "ok": True,
        "event_date": iso,
        "event_end_time": state.get("event_end_time"),
        "days_until": _days_until(iso),
        "is_past": (_days_until(iso) is not None and _days_until(iso) < 0),
        "name": (state.get("event") or {}).get("name") or "",
        "city": (state.get("event") or {}).get("city") or "",
        "format": (state.get("event") or {}).get("format") or "",
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
