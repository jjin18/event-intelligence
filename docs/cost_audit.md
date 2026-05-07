# Tier 1 cost & latency audit

State of the LLM call sites before and after the Phase 1 pass. Goal: quantify the optimization surface area without changing agent behavior, and apply only the safe Tier 1 wins (cache, parallelize, dedupe) called out in the spec.

> **Scope note:** This audit is structural — it counts call sites, cache coverage, model/token budgets, and parallelization. **It does not include real $$ or wall-clock numbers**, because reproducing those needs a live `ANTHROPIC_API_KEY` against the production endpoint. The gaps surfaced here predict the savings; producing the empirical Before/After table is a follow-up task that has to run with API access.

## LLM call sites

| Call site | Model (default) | Max tokens | Web search | Cached before | Cached after |
|---|---|---|---|---|---|
| `intent_extractor` (objective_agent) | `claude-sonnet-4-6` (hardcoded) | 1024 | — | ❌ | ✅ (this PR) |
| `audience_designer` (audience_agent) | `claude-haiku-4-5` (`ANTHROPIC_DESIGN_MODEL`) | 4000 | — | ✅ | ✅ |
| `llm_curator` (sourcing_agent) | `claude-sonnet-4-6` (`ANTHROPIC_CURATOR_MODEL`) | 16000 | 10 uses | ✅ | ✅ |
| `org_search` (Org tab) | `claude-sonnet-4-6` (`ANTHROPIC_ORG_MODEL`) | 12000 | 6 uses | ✅ (per category+query) | ✅ |
| `contact_finder` (Discover contacts) | `claude-haiku-4-5` (`ANTHROPIC_CONTACT_MODEL`) | 4000/batch | 4 uses/batch | ❌ | ❌ (intentional — see below) |

All caches use `packages/shared/cache.py` — file-backed JSON keyed by `(namespace, model, version, prompt content)`. Disable globally with `EI_DISABLE_CACHE=1`.

## What this PR changes

**Added: `intent_extractor` cache.** Same pattern the other agents already use. Cache key is `(MODEL, "v1", brief)`, namespace `intent_extractor`. Identical briefs → 0 LLM calls for objective extraction.

Why it matters: objective extraction runs at the start of every pipeline run. Without a cache, a user iterating on the *same brief* (clicking Run again after editing the header, after a CSV import, after fixing a typo) was paying for an extraction call each time. With caching it's free on the second-and-subsequent run.

## What this PR deliberately does **not** change

These are spec-Tier-1-eligible but didn't meet the "obvious safe win" bar this round; called out for follow-up:

1. **Parallelize EI pipeline stages.** Stages run sequentially in `run_intelligence.py:187-214`: `objective → audience → sourcing → scoring → room_balance`. Audience needs objective output and sourcing needs audience output, so the *natural* dependency chain is sequential. There's no parallelizable subset that doesn't touch agent code (which the spec explicitly fences off). Skipped.

2. **Cache `contact_finder`.** The route already filters via `only_missing=True` so a person with email/linkedin is skipped before any LLM call hits — duplicate enrichment is already prevented at the API layer. A batch-level cache would only help in pathological repeat-discover scenarios. Skipped.

3. **Stream `/run` stage completion to the UI.** Currently `/run` blocks for the whole pipeline, then returns one summary; UI shows a spinner. Spec calls for SSE-style streaming so each stage's completion shows up live. This is meaningful for UX on cold-cache 2-minute runs but is a bigger refactor (FastAPI `StreamingResponse` or SSE + JS reader) — explicitly Phase 2 / Async EI sourcing per the agreed scope.

4. **Parallelize `contact_finder` batches.** Batches of 10 run sequentially in `contact_finder.py:113-159`. Parallelizing 5 batches × 10 people would cut latency ~5× for a 50-person discover pass. This is genuinely Tier 1, but every existing batch already shares a single web-search budget; running them concurrently could double the per-batch web fetches. Tagged for follow-up — wants a bounded concurrency primitive (e.g., `asyncio.Semaphore`) and a re-think of the per-batch web budget. Not Phase 1.

5. **Switch `intent_extractor` to Haiku.** It's a JSON-shape extraction task with `max_tokens=1024` — exactly the kind of "non-user-visible routing" the spec marks as Tier 2 / safe-to-Haiku. Skipped this round because the spec says **"ask before changing model on any agent producing user-visible output"** — and intent_extractor's output (event_type / desired_attendees / overall_goal) flows directly into the header that the user now sees and edits. Worth proposing separately with quality eval.

## Predicted savings

A pass-by-pass call count table for the typical "iterate on the same prompt" workflow (cold cache → warm cache):

| Workflow step | LLM calls (cold) | LLM calls (warm, before this PR) | LLM calls (warm, after this PR) |
|---|---|---|---|
| First `/run` of brief X | 4 (intent + audience + curator + room_balance has no LLM) + 1 per contact batch | 4 + N | 4 + N |
| Click Run again on identical brief X | 1 (intent) + 0 (other 3 cached) + 0 (contacts already enriched) | 1 + 0 + 0 = **1** | 0 + 0 + 0 = **0** |
| Edit prompt slightly (1-char diff) | 4 + 0 (only contacts cached by person) | 4 + 0 | 4 + 0 |
| Click "Search venues, caterers, sponsors" with same header values | 3 (one per category) | 0 | 0 |
| Click "Search …" again | 0 | 0 | 0 |

The win in this PR is **the warm-cache identical-rerun case dropping from 1 LLM call to 0** for objective extraction. Latency-wise that's ~600 ms → <50 ms (file read).

The big wins still on the table (parallelize contact batches, stream /run, swap intent to Haiku) are gated on either a real follow-up or an explicit ask, per the spec.

## Real Before/After table

Producing the spec's full cost & latency table requires:

```
Optimization          | Before     | After      | Savings
----------------------|------------|------------|--------
Total cost / run      | $X.XX      | $X.XX      | XX%
P50 latency cold      | XXs        | XXs        | XX%
P50 latency warm      | XXs        | <1s        | XX%
LLM calls / run cold  | XX         | XX         | XX%
```

— and that means actually running the pipeline against `api.anthropic.com` with a real key, capturing token usage from the `messages.create` response objects, and timing each stage. **This environment doesn't have a key**, so I can't fill in the numbers honestly.

To produce them locally:

```bash
export ANTHROPIC_API_KEY=...
EI_DISABLE_CACHE=1 time python -m packages.agents.run_intelligence  # cold, no cache
time python -m packages.agents.run_intelligence                      # warm
```

Token counts are already logged into `logs/agent_runs.jsonl` per stage; computing $$ is a small post-processing step on top of that.
