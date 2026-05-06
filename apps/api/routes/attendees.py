"""Attendees tab endpoints + confirm-via-link flow.

GET    /attendees           — list attendees (auto-syncs from EI ranked people).
POST   /attendees           — add a manual attendee.
PATCH  /attendees/{id}      — update status / notes.
POST   /attendees/confirm   — accept a signed token (with ``status``) and apply
                              the confirm/decline.
GET    /confirm/{token}     — minimal HTML confirm page.
"""
from __future__ import annotations

import csv
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from apps.api.routes._state import EVENT_STATE_PATH, REPO_ROOT, mutate_state, read_state
from packages.shared import tokens as token_mod


router = APIRouter(tags=["attendees"])


_RANKED_CSV = REPO_ROOT / "data" / "ranked_people.csv"
_VALID_STATUSES = {"Invited", "Confirmed", "Declined", "Attended"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_ranked() -> list[dict]:
    if not _RANKED_CSV.exists():
        return []
    with _RANKED_CSV.open() as f:
        return list(csv.DictReader(f))


def _attendee_from_person(p: dict) -> dict:
    name = (p.get("name") or "").strip()
    email = (p.get("email") or "").strip()
    return {
        "id": token_mod.attendee_id_for(name, email),
        "name": name,
        "company": (p.get("company") or "").strip(),
        "email": email,
        "status": "Invited",
        "notes": "",
        "source": "ei",
        "added_at": _now_iso(),
        "confirmed_at": None,
    }


def _sync_from_ei(state: dict) -> list[dict]:
    """Ensure every ranked-prospect person has a row in attendees.

    Adds missing rows; never overwrites existing status/notes. Returns the
    full attendees list after sync.
    """
    attendees = state.setdefault("attendees", [])
    by_id = {a.get("id"): a for a in attendees}
    for p in _load_ranked():
        att = _attendee_from_person(p)
        if att["id"] not in by_id and att["name"]:
            attendees.append(att)
            by_id[att["id"]] = att
    return attendees


def _summary(attendees: list[dict]) -> dict:
    invited = confirmed = declined = attended = 0
    for a in attendees:
        s = a.get("status") or ""
        if s == "Invited":
            invited += 1
        elif s == "Confirmed":
            confirmed += 1
        elif s == "Declined":
            declined += 1
        elif s == "Attended":
            attended += 1
    return {
        "total": len(attendees),
        "invited": invited,
        "confirmed": confirmed,
        "declined": declined,
        "attended": attended,
    }


# -------- list / sync --------

@router.get("/attendees")
async def list_attendees() -> dict:
    def _apply(state: dict) -> dict:
        attendees = _sync_from_ei(state)
        return {"attendees": attendees}

    res = mutate_state(_apply)
    return {"ok": True, "attendees": res["attendees"], "summary": _summary(res["attendees"])}


# -------- manual add --------

class AttendeeAdd(BaseModel):
    name: str = Field(..., min_length=1)
    company: Optional[str] = None
    email: Optional[str] = None


@router.post("/attendees")
async def add_attendee(body: AttendeeAdd) -> dict:
    name = body.name.strip()
    email = (body.email or "").strip()
    new_id = token_mod.attendee_id_for(name, email)

    def _apply(state: dict) -> dict:
        attendees = state.setdefault("attendees", [])
        if any(a.get("id") == new_id for a in attendees):
            raise HTTPException(409, f"attendee {new_id} already exists")
        att = {
            "id": new_id,
            "name": name,
            "company": (body.company or "").strip(),
            "email": email,
            "status": "Invited",
            "notes": "",
            "source": "manual",
            "added_at": _now_iso(),
            "confirmed_at": None,
        }
        attendees.append(att)
        return {"attendee": att, "attendees": attendees}

    res = mutate_state(_apply)
    return {"ok": True, "attendee": res["attendee"], "summary": _summary(res["attendees"])}


# -------- patch status / notes --------

class AttendeePatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.patch("/attendees/{attendee_id}")
async def patch_attendee(attendee_id: str, body: AttendeePatch) -> dict:
    if body.status is not None and body.status not in _VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {sorted(_VALID_STATUSES)}")

    def _apply(state: dict) -> dict:
        attendees = state.setdefault("attendees", [])
        for a in attendees:
            if a.get("id") == attendee_id:
                if body.status is not None:
                    a["status"] = body.status
                    if body.status == "Confirmed" and not a.get("confirmed_at"):
                        a["confirmed_at"] = _now_iso()
                if body.notes is not None:
                    a["notes"] = body.notes
                return {"attendee": a, "attendees": attendees}
        raise HTTPException(404, f"attendee {attendee_id} not found")

    res = mutate_state(_apply)
    return {"ok": True, "attendee": res["attendee"], "summary": _summary(res["attendees"])}


# -------- confirm-via-link --------

class ConfirmBody(BaseModel):
    token: str
    status: str = Field(..., description="'Confirmed' or 'Declined'.")


def _apply_confirm(state: dict, attendee_id: str, status: str) -> dict:
    attendees = state.setdefault("attendees", [])
    # Auto-add if EI hasn't been synced yet (covers the case where someone
    # clicks a link before the next /attendees GET runs the sync).
    record: Optional[dict] = next((a for a in attendees if a.get("id") == attendee_id), None)
    if record is None:
        record = {
            "id": attendee_id,
            "name": "",
            "company": "",
            "email": "",
            "status": status,
            "notes": "",
            "source": "confirm_link",
            "added_at": _now_iso(),
            "confirmed_at": _now_iso() if status == "Confirmed" else None,
        }
        attendees.append(record)
    else:
        already = record.get("status")
        if already in ("Confirmed", "Declined"):
            return {"attendee": record, "already": True, "previous": already}
        record["status"] = status
        if status == "Confirmed":
            record["confirmed_at"] = _now_iso()
    return {"attendee": record, "already": False, "previous": None}


@router.post("/attendees/confirm")
async def confirm_attendee(body: ConfirmBody) -> dict:
    if body.status not in ("Confirmed", "Declined"):
        raise HTTPException(400, "status must be 'Confirmed' or 'Declined'")
    state = read_state()
    event = (state.get("event") or {})
    try:
        payload = token_mod.verify(body.token, event)
    except token_mod.TokenError as e:
        raise HTTPException(400, f"token invalid: {e}")

    def _apply(s: dict) -> dict:
        return _apply_confirm(s, payload["aid"], body.status)

    res = mutate_state(_apply)
    return {"ok": True, "attendee_id": res["attendee"].get("id"), "status": res["attendee"].get("status"),
            "already_recorded": res["already"], "previous_status": res["previous"]}


# -------- confirm HTML page --------

_CONFIRM_PAGE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RSVP</title>
<style>
:root{color-scheme:light}
body{font:15px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-width:520px;margin:60px auto;padding:0 20px;color:#222}
h1{font-size:22px;margin:0 0 8px;color:__COLOR__}
.event{background:#f4f4f4;padding:14px 18px;border-radius:8px;margin:18px 0}
.event div{margin:2px 0}
.event b{color:#666;font-weight:500}
button{padding:14px 22px;font:inherit;font-size:15px;border:0;border-radius:6px;cursor:pointer;margin:6px 4px 0 0}
.yes{background:#0a7d2c;color:#fff}
.no{background:#fff;color:#c33;border:1px solid #c33}
.muted{color:#888;font-size:13px;margin-top:14px}
</style></head><body>
<h1>__TITLE__</h1>
__BODY__
<div style="margin-top:18px">__BUTTONS__</div>
<div class="muted">No login required — this link is unique to you.</div>
<script>
const TOKEN = "__TOKEN__";
async function rsvp(status){
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  try{
    const r = await fetch('/attendees/confirm', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({token: TOKEN, status})
    });
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'failed');
    const msg = data.already_recorded
      ? ('Status already recorded as ' + (data.previous_status || data.status) + '.')
      : (status === 'Confirmed' ? "You're confirmed — thanks!" : "Got it — sorry you can't make it.");
    document.body.innerHTML = '<h1 style="color:#0a7d2c">Thanks!</h1><p>' + msg + '</p>';
  }catch(e){
    document.body.innerHTML = '<h1 style="color:#c33">Something went wrong</h1><p>' + e.message + '</p>';
  }
}
</script></body></html>"""


def _render_confirm_page(*,
                         title_html: str,
                         body_html: str,
                         buttons_html: str = "",
                         token: str = "",
                         status_color: str = "#0a7d2c") -> str:
    return (
        _CONFIRM_PAGE_TEMPLATE
        .replace("__COLOR__", status_color)
        .replace("__TITLE__", title_html)
        .replace("__BODY__", body_html)
        .replace("__BUTTONS__", buttons_html)
        .replace("__TOKEN__", token)
    )


@router.get("/confirm/{token}", response_class=HTMLResponse)
async def confirm_page(token: str) -> HTMLResponse:
    state = read_state()
    event = state.get("event") or {}
    try:
        token_mod.verify(token, event)
    except token_mod.TokenError as e:
        msg = "This link has expired" if "expired" in str(e) else "This link is no longer valid"
        body = f"<p>{html.escape(msg)}.</p><p class=\"muted\">If this seems wrong, ask the organizer to re-send the invite.</p>"
        return HTMLResponse(_render_confirm_page(
            title_html="Link unavailable",
            body_html=body,
            status_color="#c33",
        ), status_code=410)

    name = html.escape((event.get("name") or "the event").strip() or "the event")
    when = html.escape((state.get("event_date") or "TBD").strip() or "TBD")
    where = html.escape((event.get("city") or "").strip())
    where_row = f"<div><b>Where:</b> {where}</div>" if where else ""
    body = (
        f"<p>You've been invited to <b>{name}</b>.</p>"
        f'<div class="event">'
        f"<div><b>What:</b> {name}</div>"
        f"<div><b>When:</b> {when}</div>"
        f"{where_row}"
        f"</div>"
        f"<p>Will you be there?</p>"
    )
    buttons = (
        "<button class=\"yes\" onclick=\"rsvp('Confirmed')\">I'll be there</button>"
        " <button class=\"no\" onclick=\"rsvp('Declined')\">Can't make it</button>"
    )
    page = _render_confirm_page(
        title_html="You're invited",
        body_html=body,
        buttons_html=buttons,
        token=html.escape(token, quote=True),
    )
    return HTMLResponse(page)
