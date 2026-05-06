# Eventful

Prompt-driven event intelligence: derive **who belongs in the room**, score prospects, and emit
structured artifacts. The product direction is **Cowork-like**—an orchestrator you talk to that
**calls tools and integrations as you add them**, not a pile of unused screens and stubs.

## What ships today

- **Pipeline:** `python -m packages.agents.run_intelligence` (objective → audience → sourcing → scoring → room balance).
- **Outputs:** `data/event_state.json`, `data/ranked_people.csv`, summaries and traces under `docs/` and `logs/`.
- **Optional:** Postgres persistence when `DATABASE_URL` is set; **Redis** in compose for future jobs.
- **API:** FastAPI with `/health` and **`POST /run`** — JSON body `{ "brief_text": "...", "seed_csv_path": null }` runs the full pipeline (same as CLI); returns absolute paths and counts. Example:

  ```bash
  cd /path/to/event-intelligence
  PYTHONPATH=. uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
  curl -s -X POST http://127.0.0.1:8000/run -H 'Content-Type: application/json' \
    -d '{"brief_text":"Event type: salon\nPeople we want: founders\nGoal: peer learning\n"}' | jq
  ```

  Docker Compose mounts the repo at `/workspace` and sets `PYTHONPATH=/workspace` so `packages.*` imports resolve.

Deliberately **not** included yet: React app, CRM connectors, sponsor-brief generators, and unused agent class stubs. Add those **one integration at a time**.

## Structure

```
event-intelligence/
├── apps/
│   └── api/              # FastAPI (health); db/ for SQLAlchemy when you use DATABASE_URL
├── packages/
│   ├── agents/           # Pipeline stages + run_intelligence
│   ├── enrichment/       # LLM audience designer + web-search curator
│   ├── scoring/          # Rule-based attendee_fit scoring
│   ├── report-gen/       # Reserved for future LLM reports (empty)
│   ├── integrations/     # Reserved for connectors (empty)
│   └── shared/           # event_state, visibility, db helpers, io
├── data/                 # brief, seeds, outputs
├── docs/                 # summaries, architecture, structure_map (ops coordination)
├── logs/
└── infra/                # Docker, init_db.sql, migrate_files_to_db.py
```

## Quickstart

```bash
pip install -r apps/api/requirements.txt

docker compose -f infra/docker/docker-compose.dev.yml up   # api + db + redis
```

## Eventful run

```bash
cp .env.example .env && export $(grep -v '^#' .env | xargs)

# optional schema
psql "$DATABASE_URL" -f infra/scripts/init_db.sql

python -m packages.agents.run_intelligence
# optional: python -m packages.agents.run_intelligence <brief_path> <seed_csv_path>

# Preview how agents interpret your brief — no prospect curation, no writes to ranked CSV / logs
python -m packages.agents.preview_intent data/event_brief.txt
python -m packages.agents.preview_intent data/event_brief.txt --audience   # adds LLM ICP design (+tokens)
python -m packages.agents.preview_intent data/event_brief.txt -i             # same + prompts each open question in terminal

python -m infra.scripts.migrate_files_to_db   # optional backfill into Postgres
```

**Inputs:** `data/event_brief.txt` (free prose works best with `ANTHROPIC_API_KEY`; offline-friendly labeled sections are in `data/event_brief.template.txt`). The pipeline extracts **event type**, **who you want in the room**, and **overall goal**, then builds ICPs and sourcing around them. Optional `data/people_seed.csv` skips LLM curation when present.

**Sourcing:** LLM + web search when `ANTHROPIC_API_KEY` is set and no seed CSV; CSV or offline otherwise (see pipeline stderr / summaries).

## Handoff / coordination

- **`packages/shared/event_state.py`** and **`visibility`** are the contract for other automation (e.g. ops branch).
- **`docs/structure_map.md`** describes how Agentic Ops can consume outputs (branch-specific).

## Docs

See `/docs` for architecture and data model.
