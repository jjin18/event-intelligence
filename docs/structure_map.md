# Structure Map — Agentic Ops

**Repo note:** Empty placeholder modules under `packages/integrations/` were removed from this
repository; add real connectors incrementally as tools. The rest of this file describes the
Agentic Ops layer (branch: `feature/agentic-ops-mvp`)
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

<!-- last pipeline run: 2026-05-06T04:24:40.610493+00:00 -->
