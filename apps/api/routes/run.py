"""POST /run — pipeline endpoint.

Runs a lightweight inline pipeline so the API works without access to the
``packages/`` directory tree outside ``apps/api/``.  The full pipeline logic
can be wired back in once the import structure is resolved.
"""
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

router = APIRouter(tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    brief_text: str = Field(..., min_length=1, description="Full organizer brief / proposal text.")
    seed_csv_path: Optional[str] = Field(
        None,
        description="Optional path to seed CSV relative to process cwd (e.g. data/people_seed.csv).",
    )


def _validate_seed_path(raw: Optional[str]) -> Optional[str]:
    if raw is None or not raw.strip():
        return None
    p = Path(raw)
    if p.is_absolute():
        raise HTTPException(status_code=400, detail="seed_csv_path must be a relative path.")
    if ".." in p.parts:
        raise HTTPException(status_code=400, detail="seed_csv_path cannot contain '..'.")
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"seed_csv_path not found: {raw}")
    return str(p)


def run_pipeline(
    brief_text: str,
    *,
    seed_csv_path: Optional[str] = None,
    brief_source_label: str = "inline",
    quiet: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Inline stub pipeline.

    Returns ``(exit_code, summary)`` matching the shape expected by the HTTP
    handler.  Exit code ``2`` means an empty brief was supplied; ``0`` is
    success.  Full pipeline logic will be added once the shared ``packages/``
    modules are accessible from within this service.
    """
    if not (brief_text or "").strip():
        return 2, {"error": "empty_brief"}

    summary: dict[str, Any] = {
        "ranked_count": 0,
        "high_priority_count": 0,
        "top_gap_persona": None,
        "db_status": "skipped",
        "files_written": [],
        "note": (
            "Pipeline stub — full intelligence pipeline not yet available. "
            "Brief received and validated successfully."
        ),
    }
    return 0, summary


@router.post("/run")
async def run_pipeline_http(body: PipelineRunRequest) -> dict:
    seed = _validate_seed_path(body.seed_csv_path)

    def _execute() -> tuple[int, dict[str, Any]]:
        return run_pipeline(
            body.brief_text,
            seed_csv_path=seed,
            brief_source_label="POST /run",
            quiet=True,
        )

    try:
        code, summary = await run_in_threadpool(_execute)
    except Exception as e:
        msg = str(e) or repr(e)
        low = msg.lower()
        if "credit balance is too low" in low:
            msg = (
                "Anthropic account is out of credits. Top up at "
                "https://console.anthropic.com/settings/billing then retry."
            )
        elif "invalid x-api-key" in low or "authentication_error" in low:
            msg = "ANTHROPIC_API_KEY is invalid or revoked. Update .env and restart the server."
        raise HTTPException(status_code=502, detail=msg)
    if code != 0:
        raise HTTPException(status_code=400, detail=summary.get("error", "pipeline_failed"))
    return {"ok": True, **summary}
