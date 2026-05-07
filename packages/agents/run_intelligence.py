"""End-to-end Eventful pipeline.

Run with:
    python -m packages.agents.run_intelligence

Inputs (defaults):
    data/event_brief.txt
    data/people_seed.csv  (optional)

Outputs:
    data/event_state.json
    data/ranked_people.csv
    docs/intelligence_summary.md
    docs/agent_activity_log.md  (appended)
    logs/agent_runs.jsonl       (appended)
    docs/structure_map.md       (kept in sync if missing)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.shared.event_state import empty_event_state, save_event_state
from packages.shared.io import (
    read_event_brief,
    write_ranked_people_csv,
)
from packages.shared.visibility import create_run_id, log_agent_run
from packages.agents import (
    objective_agent,
    audience_agent,
    sourcing_agent,
    room_balance_agent,
)
from packages.scoring.attendee_fit import score_all


# --- Default paths ---
BRIEF_PATH = "data/event_brief.txt"
SEED_CSV = "data/people_seed.csv"
EVENT_STATE_PATH = "data/event_state.json"
RANKED_CSV = "data/ranked_people.csv"
SUMMARY_MD = "docs/intelligence_summary.md"
STRUCTURE_MAP = "docs/structure_map.md"


@dataclass(frozen=True)
class PipelineConfig:
    """Output locations — override in tests or alternate deployments."""

    event_state_path: Path = Path(EVENT_STATE_PATH)
    ranked_csv_path: Path = Path(RANKED_CSV)
    summary_md_path: Path = Path(SUMMARY_MD)
    structure_map_path: Path = Path(STRUCTURE_MAP)


def _write_intelligence_summary(state: dict[str, Any], path: Path) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ev = state.get("event", {})
    intel = state.get("intelligence", {})
    people = state.get("people", {})
    ranked = people.get("ranked_prospects", [])
    rb = intel.get("room_balance", {})
    open_qs = state.get("state", {}).get("open_questions", [])

    lines = [
        "# Eventful Summary",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_",
        "",
        "## 1. Organizer intent → structured objective",
        f"- **Event type:** {ev.get('format', '')}",
        f"- **Who we want:** {ev.get('desired_attendees', '') or '_(see full brief / downstream ICP)_'}",
        f"- **Overall goal:** {ev.get('goal', '')}",
        f"- **City:** {ev.get('city', '')}",
        f"- **Target size:** {ev.get('target_size', '')}",
        "- **Success metrics:**",
        *[f"  - {m}" for m in ev.get("success_metrics", [])],
        "",
        "## 2. Target Audience (ICP)",
        *[f"- **{p['name']}** (weight {p['weight']}): {p['description']}"
          for p in intel.get("audience_icp", [])],
        "",
        "## 3. Avoid Personas",
        *[f"- **{p['name']}** (penalty {p['penalty']}): {p['description']}"
          for p in intel.get("avoid_personas", [])],
        "",
        "## 4. Sourcing Strategy",
    ]
    for s in intel.get("sourcing_strategy", []):
        lines.append(f"### {s.get('type', '')}")
        for item in s.get("items", []):
            if isinstance(item, dict):
                lines.append(f"- {item.get('channel', item)} (priority: {item.get('priority', '-')})")
            else:
                lines.append(f"- {item}")
        lines.append("")

    rubric = intel.get("scoring_rubric", {})
    lines += [
        "## 5. Scoring Rubric",
        f"- **Max score:** {rubric.get('max_score', 100)}",
        f"- **High threshold:** {rubric.get('thresholds', {}).get('high', 75)}",
        f"- **Medium threshold:** {rubric.get('thresholds', {}).get('medium', 55)}",
        f"- **Notes:** {rubric.get('notes', '')}",
        "",
        "## 6. Top 10 Ranked Prospects",
        "| # | Name | Company | Role | Persona | Fit | Priority |",
        "|---|------|---------|------|---------|-----|----------|",
    ]
    for i, p in enumerate(ranked[:10], 1):
        lines.append(
            f"| {i} | {p.get('name','')} | {p.get('company','')} | {p.get('role','')} "
            f"| {p.get('persona','')} | {p.get('fit_score','')} | {p.get('priority','')} |"
        )
    lines += [
        "",
        "## 7. Room Balance",
        f"- **Summary:** {rb.get('summary', '')}",
        f"- **Persona breakdown:** {rb.get('persona_breakdown', {})}",
        "- **Gaps:**",
        *[f"  - {g['persona']}: current {g['current']} / target {g['target']} (deficit {g['deficit']})"
          for g in rb.get("gaps", [])],
        "- **Recommendations:**",
        *[f"  - {r}" for r in rb.get("recommendations", [])],
        "",
        "## 8. Open Questions",
        *[f"- {q}" for q in open_qs],
        "",
        "## 9. Next Recommended Ops Actions",
        "- Approve the top high-priority prospects in `data/ranked_people.csv`.",
        "- Hand `data/event_state.json` and `data/ranked_people.csv` to the Agentic Ops branch.",
        "- Run another sourcing pass focused on the top room-balance gap.",
        "",
    ]

    out_path.write_text("\n".join(lines) + "\n")


def _ensure_structure_map(path: Path) -> None:
    """Append/update last-run marker on structure_map."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    marker = f"\n\n<!-- last pipeline run: {datetime.now(timezone.utc).isoformat()} -->\n"
    if p.exists():
        existing = p.read_text()
        if "<!-- last pipeline run:" in existing:
            head = existing.split("<!-- last pipeline run:")[0].rstrip()
            p.write_text(head + marker)
        else:
            with p.open("a") as f:
                f.write(marker)
    else:
        with p.open("a") as f:
            f.write(marker)


def run_pipeline(
    brief_text: str,
    *,
    seed_csv_path: str | Path | None = None,
    config: PipelineConfig | None = None,
    brief_source_label: str = "inline",
    quiet: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Execute objective → audience → sourcing → scoring → room balance + artifact writes.

    Returns ``(exit_code, summary)`` where ``exit_code`` is ``2`` for empty brief, else ``0``.
    ``summary`` includes paths and counts for API/clients.
    """
    cfg = config or PipelineConfig()
    seed_str = str(seed_csv_path) if seed_csv_path else ""
    seed_exists = bool(seed_str and Path(seed_str).exists())

    if not (brief_text or "").strip():
        return 2, {"error": "empty_brief"}

    pipeline_run_id = create_run_id("run_intelligence")
    state = empty_event_state()

    brief = brief_text.strip()

    objective = objective_agent.run(brief, event_state=state)
    if not (state.get("event") or {}).get("name"):
        et = (objective.get("event_type") or "").strip()
        city = (objective.get("city") or "").strip()
        state.setdefault("event", {})["name"] = (
            " — ".join(p for p in (et, city) if p) or "Untitled event"
        )

    audience = audience_agent.run(objective, event_state=state, event_brief=brief)
    sourcing = sourcing_agent.run(
        objective,
        audience,
        seed_csv_path=seed_str if seed_exists else None,
        event_state=state,
        event_brief=brief,
    )

    prospects = state.get("people", {}).get("prospects", []) or sourcing.get("prospects", [])
    ranked = score_all(
        prospects,
        audience.get("audience_icp", []),
        audience.get("scoring_rubric", {}),
        objective,
        avoid_personas=audience.get("avoid_personas", []),
    )
    state.setdefault("people", {})["ranked_prospects"] = ranked

    room_balance_agent.run(ranked, target_size=objective.get("target_size", 100), event_state=state)

    # Contact discovery folded into the pipeline. The standalone "Discover
    # contacts" button is gone — the Contact column has to be populated by
    # the time the EI tab renders, per the cascade-pattern spec.
    # only_missing=True so re-runs don't re-bill for already-enriched people.
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from packages.enrichment.contact_finder import discover_contacts
            targets = [p for p in ranked if not (p.get("email") or p.get("linkedin_url"))]
            # Cap at 25 by default to keep cost bounded — same behavior the
            # standalone /contacts/discover endpoint had.
            contact_limit = int(os.environ.get("EI_CONTACT_LIMIT", "25"))
            if targets and contact_limit > 0:
                discover_contacts(targets[:contact_limit])
        except Exception as exc:  # noqa: BLE001
            # Don't fail the whole pipeline if contact discovery has a hiccup.
            print(f"[run_intelligence] contact discovery error (non-fatal): {exc!r}", file=sys.stderr)

    files_written: list[str] = []
    esp = cfg.event_state_path
    rcp = cfg.ranked_csv_path
    smp = cfg.summary_md_path
    stm = cfg.structure_map_path

    save_event_state(str(esp), state)
    files_written.append(str(esp))
    write_ranked_people_csv(str(rcp), ranked)
    files_written.append(str(rcp))
    _write_intelligence_summary(state, smp)
    files_written.append(str(smp))
    _ensure_structure_map(stm)
    files_written.append(str(stm))

    state.setdefault("visibility", {})["latest_summary_files"] = [str(smp), str(stm)]
    save_event_state(str(esp), state)

    db_status = "skipped"
    try:
        from packages.shared import db as _db
        if _db.is_db_enabled():
            event_id = _db.upsert_event(state, brief_text=brief)
            if event_id is not None:
                state["_db_event_id"] = str(event_id)
                rows = _db.upsert_people(event_id, ranked)
                db_status = f"ok ({rows} people upserted, event_id={event_id})"
            else:
                db_status = "upsert_event returned None"
    except Exception as e:
        db_status = f"error: {e!r}"

    high = [p for p in ranked if p.get("priority") == "high"]
    rb = state.get("intelligence", {}).get("room_balance", {})
    top_gap = rb.get("top_gap")

    files_read = [brief_source_label]
    if seed_exists:
        files_read.append(seed_str)

    log_agent_run(
        "run_intelligence",
        run_id=pipeline_run_id,
        input_summary=f"brief={brief_source_label}, seed={seed_str if seed_exists else 'none'}",
        output_summary=(
            f"Pipeline complete: {len(ranked)} prospects scored, "
            f"{len(high)} high-priority, top_gap={top_gap['persona'] if top_gap else 'none'}."
        ),
        decisions_made=["Ran objective → audience → sourcing → scoring → room_balance pipeline."],
        reasoning_summary="Sequential pipeline; each stage writes to event_state and emits its own visibility trace.",
        confidence="medium",
        files_read=files_read,
        files_written=files_written,
        next_actions=["Hand event_state.json + ranked_people.csv to Agentic Ops branch."],
        event_state=state,
    )
    save_event_state(str(esp), state)

    summary: dict[str, Any] = {
        "event_state_path": str(esp.resolve()),
        "ranked_people_csv_path": str(rcp.resolve()),
        "intelligence_summary_path": str(smp.resolve()),
        "structure_map_path": str(stm.resolve()),
        "ranked_count": len(ranked),
        "high_priority_count": len(high),
        "top_gap_persona": top_gap["persona"] if top_gap else None,
        "db_status": db_status,
        "files_written": files_written,
    }

    if not quiet:
        print()
        print("=" * 60)
        print("Eventful pipeline complete.")
        print("=" * 60)
        print(f"Database              : {db_status}")
        print(f"Prospects scored      : {len(ranked)}")
        print(f"High-priority         : {len(high)}")
        print(f"Top room-balance gap  : {top_gap['persona'] if top_gap else 'none'}")
        print("Files written         :")
        for f in files_written:
            print(f"  - {f}")
        print("  - logs/agent_runs.jsonl")
        print("  - docs/agent_activity_log.md")
        print()
        print("Next: plug this pipeline into your orchestrator (API, MCP tools, or chat UI).")

    return 0, summary


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    brief_path = argv[0] if len(argv) > 0 else BRIEF_PATH
    seed_path = argv[1] if len(argv) > 1 else SEED_CSV

    brief = read_event_brief(brief_path)
    if not brief:
        print(f"[run_intelligence] No brief found at {brief_path}; aborting.", file=sys.stderr)
        return 2

    code, _ = run_pipeline(
        brief,
        seed_csv_path=seed_path if Path(seed_path).exists() else None,
        brief_source_label=str(brief_path),
        quiet=False,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
