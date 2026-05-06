"""Top-level orchestrator: run all Agentic Ops agents in order."""
from __future__ import annotations

import sys
from pathlib import Path

from packages.shared.event_state import (
    empty_event_state, load_event_state, save_event_state,
)
from packages.shared import visibility
from . import _common
from ._common import (
    DATA_DIR, DOCS_DIR, EVENT_STATE_PATH, INTELLIGENCE_SUMMARY_PATH,
    RANKED_PEOPLE_PATH, rel,
)
from . import (
    pm_agent, outreach_agent, venue_agent,
    sponsor_partner_agent, retention_agent, basic_ops_agent,
)
from packages.integrations import (
    google_sheets_stub, gmail_stub, poke_stub, luma_stub,
)


def _seed_event_state_if_missing() -> dict:
    if EVENT_STATE_PATH.exists():
        return load_event_state(EVENT_STATE_PATH)
    print(
        "[run_ops] data/event_state.json not found.\n"
        "  Run the Eventful pipeline first to produce event_state.json + ranked_people.csv.\n"
        "  Falling back to a minimal sample so ops can still run end-to-end.",
        file=sys.stderr,
    )
    state = empty_event_state()
    state["event"] = {
        "name": "AI Builders Night",
        "goal": "agent infrastructure and devtools",
        "city": "SF",
        "date": "next week",
        "target_size": 100,
        "format": "curated evening reception",
        "success_metrics": ["100 attendees", ">=70% show-up", "5+ partner intros"],
    }
    save_event_state(EVENT_STATE_PATH, state)
    return state


def _write_ops_summary(event_state: dict, results: dict) -> Path:
    event = event_state.get("event", {}) or {}
    state = event_state.get("state", {}) or {}
    last = state.get("last_agent_run", {}) or {}
    out = DOCS_DIR / "ops_summary.md"
    blockers_lines = [f"- {b}" for b in state.get("blockers", [])] or ["- (none)"]
    approval_lines = [f"- {a.get('item')} ({a.get('status')})" for a in state.get("approval_queue", [])] or ["- (empty)"]
    next_lines = [f"- {n}" for n in state.get("next_actions", [])] or ["- (none)"]
    workstream_lines = [f"- {w['name']} ({w.get('status','active')})" for w in (event_state.get('ops', {}) or {}).get('workstreams', [])]
    lines = [
        f"# Ops Summary — {event.get('name','(event)')}\n",
        f"_Last agent run: {last.get('agent_name','-')} @ {last.get('timestamp','-')}_\n",
        "## 1. Current event status",
        f"- City: {event.get('city','-')}",
        f"- Date: {event.get('date','-')}",
        f"- Target size: {event.get('target_size','-')}",
        f"- Format: {event.get('format','-')}",
        "",
        "## 2. Workstreams",
        *workstream_lines,
        "",
        "## 3. Outreach queue",
        f"- Total drafts: {results['outreach']['queue_count']}",
        f"- High priority: {results['outreach']['high']}",
        f"- Medium priority: {results['outreach']['medium']}",
        f"- Low priority: {results['outreach']['low']}",
        "",
        "## 4. Venue pipeline",
        f"- Candidates: {results['venue']['candidates']} (see data/venue_crm.csv, drafts/venue_outreach_email.md)",
        "",
        "## 5. Sponsor / partner pipeline",
        f"- Partners: {results['sponsor']['partners']} (see data/sponsor_partner_crm.csv)",
        "",
        "## 6. RSVP / retention math",
        f"- Target attendance: {results['retention']['target']}",
        f"- Accepted RSVPs needed: ~{results['retention']['accepted_target']}",
        f"- Guests tracked: {results['retention']['tracked']}",
        f"- High-risk guests: {results['retention']['high_risk']}",
        "",
        "## 7. Basic ops",
        "- See docs/basic_ops_checklist.md, docs/run_of_show.md, docs/one_week_timeline.md",
        "",
        "## 8. Blockers",
        *blockers_lines,
        "",
        "## 9. Approval queue",
        *approval_lines,
        "",
        "## 10. Next actions",
        *next_lines,
        "",
    ]
    out.write_text("\n".join(lines))
    return out


def _write_structure_map() -> Path:
    out = DOCS_DIR / "structure_map.md"
    out.write_text(STRUCTURE_MAP)
    return out


def main() -> int:
    _common.ensure_dirs()
    event_state = _seed_event_state_if_missing()

    results = {}
    pm_agent.run(event_state)
    results["outreach"] = outreach_agent.run(event_state)
    results["venue"] = venue_agent.run(event_state)
    results["sponsor"] = sponsor_partner_agent.run(event_state)
    results["retention"] = retention_agent.run(event_state)
    basic_ops_agent.run(event_state)

    # Visibility pointer for both branches.
    vis = event_state.setdefault("visibility", {})
    vis["latest_summary_files"] = [
        rel(DOCS_DIR / "ops_summary.md"),
        rel(DOCS_DIR / "structure_map.md"),
        rel(DOCS_DIR / "agent_activity_log.md"),
    ]

    save_event_state(EVENT_STATE_PATH, event_state)
    summary_path = _write_ops_summary(event_state, results)
    map_path = _write_structure_map()

    # Run integration stubs (no real network).
    google_sheets_stub.write_csv_to_sheet_stub(DATA_DIR / "guest_crm.csv", "Guest CRM")
    google_sheets_stub.write_csv_to_sheet_stub(DATA_DIR / "venue_crm.csv", "Venue CRM")
    gmail_stub.create_email_drafts_stub(DATA_DIR / "outreach_queue.csv")
    poke_stub.create_poke_message_queue_stub(DATA_DIR / "outreach_queue.csv")
    luma_stub.create_luma_event_copy_stub(event_state)

    blockers = event_state.get("state", {}).get("blockers", [])
    next_actions = event_state.get("state", {}).get("next_actions", [])
    print()
    print("=" * 60)
    print("Agentic Ops run complete")
    print("=" * 60)
    print(f"- Outreach drafts created: {results['outreach']['queue_count']} "
          f"(high={results['outreach']['high']}, med={results['outreach']['medium']}, low={results['outreach']['low']})")
    print(f"- Venue candidates: {results['venue']['candidates']}")
    print(f"- Sponsor/partner targets: {results['sponsor']['partners']}")
    print(f"- Retention forecast: target {results['retention']['target']} attendees, "
          f"~{results['retention']['accepted_target']} accepted RSVPs needed")
    print(f"- Blockers: {blockers or '(none)'}")
    print(f"- Files written: data/, drafts/, docs/{summary_path.name}, docs/{map_path.name}, "
          f"logs/agent_runs.jsonl, docs/agent_activity_log.md")
    if next_actions:
        print(f"- Next suggested action: {next_actions[0]}")
    return 0


STRUCTURE_MAP = """# Structure Map — Agentic Ops

This document is the map of the Agentic Ops layer (branch: `feature/agentic-ops-mvp`)
and the contract it shares with Eventful (branch: `feature/event-intelligence-mvp`).

## 1. Repo areas touched

| Path | Purpose | Inputs | Outputs | Shared contract? |
|---|---|---|---|---|
| `packages/shared/event_state.py` | Canonical EventState schema | — | dataclass + IO helpers | yes |
| `packages/shared/visibility.py` | Trace + activity log helpers | — | `logs/`, `docs/agent_activity_log.md` | yes |
| `packages/shared/io.py` | CSV / state IO helpers | — | — | yes |
| `packages/ops/pm_agent.py` | Workstreams, blockers, timeline | event_state | `docs/one_week_timeline.md` | no |
| `packages/ops/outreach_agent.py` | Outreach drafts + guest CRM | `data/ranked_people.csv` | `data/outreach_queue.csv`, `data/guest_crm.csv` | no |
| `packages/ops/venue_agent.py` | Venue CRM + outreach email | `data/venue_seed.csv` (opt) | `data/venue_crm.csv`, `drafts/venue_outreach_email.md` | no |
| `packages/ops/sponsor_partner_agent.py` | Partner ICP + CRM | event_state | `data/sponsor_partner_crm.csv`, `drafts/sponsor_partner_outreach.md` | no |
| `packages/ops/retention_agent.py` | RSVP math + retention plan | `data/guest_crm.csv` | `data/retention_tracker.csv`, `docs/retention_plan.md` | no |
| `packages/ops/basic_ops_agent.py` | Checklist + run-of-show | event_state | `docs/basic_ops_checklist.md`, `docs/run_of_show.md` | no |
| `packages/ops/reply_tracker.py` | Apply replies to CRMs | `data/replies.csv` | updates `data/guest_crm.csv`, `data/outreach_queue.csv`, `data/retention_tracker.csv` | no |
| `packages/ops/run_ops.py` | Top-level orchestrator | all of the above | `docs/ops_summary.md`, `docs/structure_map.md`, updated `event_state.json` | no |
| `packages/integrations/google_sheets_stub.py` | Sync stub | csv path | print intent | no |
| `packages/integrations/gmail_stub.py` | Draft stub | `data/outreach_queue.csv` | `drafts/emails/*.md` | no |
| `packages/integrations/poke_stub.py` | Poke/LI queue stub | `data/outreach_queue.csv` | `drafts/poke_messages.csv` | no |
| `packages/integrations/luma_stub.py` | Luma page stub | event_state | `drafts/luma_event_page.md` | no |

## 2. Agentic Ops module

`packages/ops/` contains six agents + a reply tracker + a runner. Each agent is a
single Python module exposing a `run(event_state)` function. The runner wires them
together against the shared `data/event_state.json` and `data/ranked_people.csv`.

`packages/integrations/` adds four stubs (no real auth) so the system has a clear
seam for plugging in Gmail / Sheets / Poke / Luma later. Each stub takes the same
CSV / state inputs the real connector would, and writes a local file describing
the action it *would* take.

### Data flow

```
data/event_state.json
data/ranked_people.csv         ─────►  pm_agent ──────► state.workstreams, next_actions, blockers
docs/intelligence_summary.md            outreach_agent ─► data/outreach_queue.csv, data/guest_crm.csv
                                        venue_agent ────► data/venue_crm.csv, drafts/venue_outreach_email.md
                                        sponsor_partner_agent
                                                       ─► data/sponsor_partner_crm.csv, drafts/sponsor_partner_outreach.md
                                        retention_agent ► data/retention_tracker.csv, docs/retention_plan.md
                                        basic_ops_agent ► docs/basic_ops_checklist.md, run_of_show.md, one_week_timeline.md
                                                  │
                                                  └────► updated data/event_state.json
                                                         docs/ops_summary.md
                                                         docs/structure_map.md
                                                         logs/agent_runs.jsonl
                                                         docs/agent_activity_log.md
```

### CSV outputs and column meanings

- **outreach_queue.csv** — one row per prospect: `name,company,role,channel,priority,fit_score,outreach_angle,message,follow_up_message,status,last_touch,notes`
- **guest_crm.csv** — `name,company,role,email,linkedin_url,priority,fit_score,channel,status,last_touch,rsvp_status,notes`
- **venue_crm.csv** — `venue_name,contact_name,contact_email,location,capacity,estimated_cost,availability,food_policy,av,status,last_touch,reply_summary,next_step`
- **sponsor_partner_crm.csv** — `organization,category,poc_name,poc_email,warm_intro,value_prop,status,last_touch,next_step,notes`
- **retention_tracker.csv** — `name,rsvp_status,accepted_date,calendar_invite_sent,reminder_48h_sent,day_of_reminder_sent,show_up_probability,risk_level,recommended_action`

### How to modify behavior

- **Outreach copy:** edit `_message`, `_follow_up`, `_subject` in `packages/ops/outreach_agent.py`.
- **Venue questions / email:** edit `_outreach_email` and `VENUE_CRM_COLUMNS` in `packages/ops/venue_agent.py`.
- **Retention assumptions:** edit `_show_up_rate` and `_risk` in `packages/ops/retention_agent.py`.
- **Checklist / run-of-show:** edit `_checklist` and `RUN_OF_SHOW` in `packages/ops/basic_ops_agent.py`.
- **Replace stubs:** swap `packages/integrations/*_stub.py` calls in `run_ops.py` with real connectors.

## 3. Agent structure

Each agent shares the same shape:

| Agent | Responsibility | Inputs | Outputs | Trace |
|---|---|---|---|---|
| pm_agent | Workstreams, blockers, next actions, weekly timeline | event_state, ranked_people, intelligence_summary | docs/one_week_timeline.md, event_state.state | logs/agent_runs.jsonl + docs/agent_activity_log.md |
| outreach_agent | Personalized drafts + guest CRM | data/ranked_people.csv (or event_state.people.ranked_prospects) | data/outreach_queue.csv, data/guest_crm.csv, event_state.ops.outreach_queue | same |
| venue_agent | Venue CRM + outreach email | data/venue_seed.csv (optional) | data/venue_crm.csv, drafts/venue_outreach_email.md, event_state.venues | same |
| sponsor_partner_agent | Partner ICP + CRM + outreach | event_state | data/sponsor_partner_crm.csv, drafts/sponsor_partner_outreach.md, event_state.sponsors | same |
| retention_agent | RSVP math + per-guest risk | data/guest_crm.csv, event_state | data/retention_tracker.csv, docs/retention_plan.md, event_state.ops.retention_plan | same |
| basic_ops_agent | Checklist + run-of-show | event_state | docs/basic_ops_checklist.md, docs/run_of_show.md, event_state.ops.basic_ops_checklist | same |
| reply_tracker | Ingest replies, update CRMs | data/replies.csv | updates guest_crm.csv, outreach_queue.csv, retention_tracker.csv, event_state | same |

## 4. Shared contracts

`event_state.json` top-level keys: `event, intelligence, people, ops, venues, sponsors, state, visibility`.
`state` carries `open_questions, risks, blockers, next_actions, approval_queue, activity_log, last_agent_run`.
`visibility` carries `latest_summary_files, latest_trace_file, latest_activity_log`.

Agentic Ops only writes under `ops`, `venues`, `sponsors`, `state`, and `visibility`.
It does not overwrite `event`, `intelligence`, or `people`.

## 5. Branch coordination

**This branch (`feature/agentic-ops-mvp`) produces:**
- `data/outreach_queue.csv`, `data/guest_crm.csv`, `data/venue_crm.csv`,
  `data/sponsor_partner_crm.csv`, `data/retention_tracker.csv`
- `docs/run_of_show.md`, `docs/basic_ops_checklist.md`, `docs/one_week_timeline.md`,
  `docs/retention_plan.md`, `docs/ops_summary.md`, `docs/structure_map.md`
- `drafts/venue_outreach_email.md`, `drafts/sponsor_partner_outreach.md`,
  `drafts/luma_event_page.md`, `drafts/poke_messages.csv`, `drafts/emails/*.md`
- updates to `data/event_state.json` (only `ops`, `venues`, `sponsors`, `state`, `visibility`)
- appends to `logs/agent_runs.jsonl`, `docs/agent_activity_log.md`

**This branch consumes (from Eventful):**
- `data/event_state.json` (especially `event`, `intelligence`, `people`)
- `data/ranked_people.csv`
- `docs/intelligence_summary.md`

**Eventful should NOT overwrite:**
- `event_state.ops`, `event_state.venues`, `event_state.sponsors`
- the ops-owned CSVs and docs listed above
- prior entries in `state.activity_log` (always append)

**Likely merge conflicts:**
- `packages/shared/event_state.py`, `packages/shared/visibility.py`, `packages/shared/io.py` — both branches may carry these. They were authored as the joint contract; expect them to be near-identical. Resolve by taking the superset and keeping `set_branch_context` exposed.
- `data/event_state.json` — regenerated on each run; do not commit conflicting fixtures.
- `docs/agent_activity_log.md`, `logs/agent_runs.jsonl` — append-only logs; resolve by concatenating both sides.
- `README.md` — both branches add sections; keep both.

## 6. How to run

```bash
# from repo root
python -m packages.ops.run_ops
```

Requires Python 3.10+. No external services are called.

To ingest replies once they arrive:

```bash
# put rows in data/replies.csv with columns: name, reply_status, notes
python -m packages.ops.reply_tracker
```

## 7. How to inspect outputs

- Human summary: `docs/ops_summary.md`
- Activity log: `docs/agent_activity_log.md`
- Machine trace: `logs/agent_runs.jsonl` (one JSON object per agent run)
- Per-agent outputs: see CSV / docs paths in section 1

## 8. Current limitations / stubs

- No real Gmail / Sheets / Poke / Luma calls — see `packages/integrations/*_stub.py`.
- Reply tracking is file-based (`data/replies.csv`), not webhook-driven.
- Venue and sponsor candidate lists are sample data unless `data/venue_seed.csv` is provided.
- No frontend; the system is CLI + files.

## 9. Next integration points

- Replace `gmail_stub.create_email_drafts_stub` with Gmail API drafts.
- Replace `google_sheets_stub.write_csv_to_sheet_stub` with Sheets API sync.
- Replace `luma_stub.create_luma_event_copy_stub` with Luma API event creation.
- Wire `reply_tracker.run` to a Gmail/Poke webhook instead of `replies.csv`.
"""


if __name__ == "__main__":
    raise SystemExit(main())
