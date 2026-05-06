import logging
import os
from pathlib import Path

from fastapi import FastAPI

# Auto-load .env if present alongside (or above) this file.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / ".env"
    if not _env_path.exists():
        # fall back one level up (repo root when running locally)
        _env_path = Path(__file__).resolve().parents[2] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
except ImportError:
    pass

_log = logging.getLogger("event_intelligence.api")
if not os.environ.get("ANTHROPIC_API_KEY"):
    _log.warning(
        "ANTHROPIC_API_KEY is not set — pipeline will return stub results. "
        "Add it to your environment or a .env file and restart the server.",
    )

from fastapi.responses import HTMLResponse, FileResponse

from routes import run as run_routes

app = FastAPI(title="Event Intelligence API", version="0.1.0")

app.include_router(run_routes.router)


_INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Event Intelligence</title>
<style>
body{font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-width:880px;margin:40px auto;padding:0 20px;color:#222}
h1{font-size:18px;margin:0 0 4px}
.sub{color:#888;margin-bottom:24px}
textarea{width:100%;height:200px;padding:12px;font:inherit;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}
button{margin-top:12px;padding:10px 18px;font:inherit;background:#111;color:#fff;border:0;border-radius:6px;cursor:pointer}
button:disabled{background:#888}
.warn{background:#fff7d6;border:1px solid #e8c97b;padding:8px 12px;border-radius:6px;margin-bottom:16px;font-size:13px}
.result{margin-top:24px}
.summary{background:#f4f4f4;padding:10px 14px;border-radius:6px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #eee;vertical-align:top}
th{background:#fafafa}
.pri-high{color:#0a7d2c;font-weight:600}.pri-medium{color:#a36c00}.pri-low{color:#888}.pri-needs_review{color:#c33}
.err{background:#fde}
</style></head>
<body>
<h1>Event Intelligence</h1>
<div class="sub">Paste an event proposal. Get a curated, ranked list.</div>
<div id="warn"></div>
<textarea id="brief" placeholder="e.g. 100-person crypto hackathon for builders, founders, ZK researchers in SF..."></textarea>
<div><button id="go">Run pipeline</button> <span id="status" style="margin-left:12px;color:#888"></span></div>
<div class="result" id="result"></div>
<script>
fetch('/health').then(r=>r.json()).then(h=>{
  if(!h.anthropic_key_set){
    document.getElementById('warn').innerHTML =
      '<div class="warn">ANTHROPIC_API_KEY is not set on the server — the curator will skip and you\\'ll get 0 prospects. Add it to <code>.env</code> and restart.</div>';
  }
});
const btn=document.getElementById('go'), status=document.getElementById('status'), result=document.getElementById('result');
btn.onclick = async () => {
  const brief = document.getElementById('brief').value.trim();
  if(!brief){alert('Paste a brief first');return}
  btn.disabled = true; result.innerHTML='';
  const t0 = Date.now();
  // live elapsed counter so the page doesn't look hung during the 1-2 min wait
  const tick = setInterval(() => {
    const s = Math.floor((Date.now()-t0)/1000);
    const m = Math.floor(s/60), r = s%60;
    status.textContent = `running… ${m>0?m+'m ':''}${r}s elapsed (typical 1-2 min for 100 people)`;
  }, 250);
  try {
    const r = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brief_text: brief})});
    const data = await r.json();
    if(!r.ok){ throw new Error(data.detail || 'pipeline failed'); }
    clearInterval(tick);
    status.textContent = `done in ${((Date.now()-t0)/1000).toFixed(1)}s`;
    const peopleResp = await fetch('/people');
    const people = (await peopleResp.json()).people || [];
    renderResult(data, people);
  } catch(e) {
    clearInterval(tick);
    status.textContent = '';
    result.innerHTML = `<div class="warn err">${e.message}</div>`;
  } finally { btn.disabled = false; }
};
function renderResult(s, people){
  const top = people.slice(0, 30);
  let html = `<div class="summary">
    Sourced <b>${s.ranked_count}</b> prospects · <b>${s.high_priority_count}</b> high-priority · top gap: <b>${s.top_gap_persona||'-'}</b><br>
    <a href="/download/ranked_people.csv" download style="display:inline-block;margin-top:8px;margin-right:8px;padding:6px 12px;background:#0a7d2c;color:#fff;text-decoration:none;border-radius:4px;font-size:13px">⬇ ranked_people.csv</a>
    <a href="/download/event_state.json" download style="display:inline-block;margin-top:8px;padding:6px 12px;background:#444;color:#fff;text-decoration:none;border-radius:4px;font-size:13px">⬇ event_state.json</a>
  </div>`;
  if(top.length){
    html += '<table><tr><th>#</th><th>Fit</th><th>Priority</th><th>Persona</th><th>Name</th><th>Role</th><th>Company</th></tr>';
    top.forEach((p,i)=>{
      html += `<tr>
        <td>${i+1}</td><td>${p.fit_score||''}</td>
        <td class="pri-${(p.priority||'').replace(/[^a-z_]/gi,'')}">${p.priority||''}</td>
        <td>${p.persona||''}</td><td>${p.name||''}</td><td>${p.role||''}</td><td>${p.company||''}</td>
      </tr>`;
    });
    html += '</table>';
    if(people.length > 30) html += `<p style="color:#888">… ${people.length - 30} more in ranked_people.csv</p>`;
  } else {
    html += '<div class="warn">No prospects — usually means ANTHROPIC_API_KEY isn\\'t set.</div>';
  }
  result.innerHTML = html;
}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return _INDEX_HTML


_DATA_DIR = Path(__file__).resolve().parent / "data"


@app.get("/people")
async def people():
    """Return the most recent ranked_people.csv as JSON."""
    import csv as _csv
    csv_path = _DATA_DIR / "ranked_people.csv"
    if not csv_path.exists():
        return {"people": []}
    with csv_path.open() as f:
        rows = list(_csv.DictReader(f))
    return {"people": rows}


@app.get("/download/ranked_people.csv")
async def download_ranked():
    """Stream the most recent ranked_people.csv as a file download."""
    csv_path = _DATA_DIR / "ranked_people.csv"
    if not csv_path.exists():
        return {"error": "no ranked CSV yet — run the pipeline first"}
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="ranked_people.csv",
    )


@app.get("/download/event_state.json")
async def download_state():
    """Stream the most recent event_state.json as a file download."""
    p = _DATA_DIR / "event_state.json"
    if not p.exists():
        return {"error": "no event_state yet — run the pipeline first"}
    return FileResponse(
        path=p,
        media_type="application/json",
        filename="event_state.json",
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "database_url_set": bool(os.environ.get("DATABASE_URL")),
    }
