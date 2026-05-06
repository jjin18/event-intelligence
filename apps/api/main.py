import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI

# Import ``packages.*`` when cwd is apps/api (docker or local uvicorn from api folder).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Auto-load .env from repo root so the API doesn't silently miss
# ANTHROPIC_API_KEY / DATABASE_URL when started via `uvicorn apps.api.main:app`.
try:
    from dotenv import load_dotenv
    _env_path = _REPO_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
except ImportError:
    pass

_log = logging.getLogger("event_intelligence.api")
if not os.environ.get("ANTHROPIC_API_KEY"):
    _log.warning(
        "ANTHROPIC_API_KEY is not set — the LLM curator and audience designer "
        "will fall back to generic offline behavior (0 curated prospects). "
        "Add it to %s or your shell env to enable live curation.",
        _REPO_ROOT / ".env",
    )

from fastapi.responses import HTMLResponse, FileResponse

from apps.api.routes import run as run_routes
from apps.api.routes import messages as messages_routes

app = FastAPI(title="Event Intelligence API", version="0.1.0")

app.include_router(run_routes.router)
app.include_router(messages_routes.router)


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
.contact-icons{font-size:13px;color:#666;letter-spacing:2px}
.contact-icons a{color:#0a7d2c;text-decoration:none;margin-right:3px}
.contact-icons .miss{color:#ccc}
.btn-msg{background:#fff;color:#111;border:1px solid #bbb;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:12px;margin:0}
.btn-msg:hover{background:#f0f0f0}
.btn-msg:disabled{color:#bbb;border-color:#eee;cursor:not-allowed}
.btn-secondary{background:#fff;color:#111;border:1px solid #bbb;padding:6px 12px;border-radius:4px;cursor:pointer;font:inherit;font-size:13px;margin-top:0}
.btn-secondary:hover{background:#f0f0f0}
/* Modal */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:flex-start;justify-content:center;z-index:50;overflow:auto;padding:32px 20px}
.modal-bg.show{display:flex}
.modal{background:#fff;border-radius:8px;max-width:780px;width:100%;padding:24px;box-shadow:0 8px 32px rgba(0,0,0,.2);position:relative}
.modal h2{margin:0 0 12px;font-size:16px}
.modal .close{position:absolute;top:12px;right:14px;background:none;border:0;font-size:22px;cursor:pointer;color:#888;padding:0}
.modal .field{margin-bottom:14px}
.modal label{display:block;font-size:12px;color:#666;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px}
.modal textarea{height:110px}
.placeholders{font-size:12px;color:#888;margin-top:4px}
.placeholders code{background:#f4f4f4;padding:1px 5px;border-radius:3px;color:#0a7d2c}
.slider-row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.slider-row input[type=range]{flex:1}
.preview-list{max-height:300px;overflow:auto;border:1px solid #eee;border-radius:6px;padding:8px;background:#fafafa;font-size:12.5px}
.preview-row{padding:6px 8px;border-bottom:1px solid #eee}
.preview-row:last-child{border:0}
.preview-row .pname{font-weight:600;display:flex;justify-content:space-between;align-items:center}
.preview-row .pmsg{color:#444;margin-top:2px;white-space:pre-wrap}
.preview-row .channel{font-size:11px;color:#888;margin-left:6px}
.action-row{display:flex;gap:8px;align-items:center;margin-top:14px}
</style></head>
<body>
<h1>Event Intelligence</h1>
<div class="sub">Paste an event proposal. Get a curated, ranked list.</div>
<div id="warn"></div>
<textarea id="brief" placeholder="e.g. 100-person crypto hackathon for builders, founders, ZK researchers in SF..."></textarea>
<div><button id="go">Run pipeline</button> <span id="status" style="margin-left:12px;color:#888"></span></div>
<div class="result" id="result"></div>

<!-- Outreach modal -->
<div class="modal-bg" id="msg-modal" onclick="if(event.target===this)closeMsg()">
  <div class="modal">
    <button class="close" onclick="closeMsg()">×</button>
    <h2>Message <span id="msg-focus-name"></span></h2>
    <div style="font-size:12px;color:#888;margin-bottom:4px"><span id="msg-focus-meta"></span></div>
    <div style="margin-bottom:12px">Contact: <span id="msg-focus-contact"></span></div>

    <div class="field">
      <label for="msg-subject">Subject</label>
      <input id="msg-subject" type="text" value="Invitation" style="width:100%;padding:8px;font:inherit;border:1px solid #ccc;border-radius:6px;box-sizing:border-box" oninput="rerenderPreview()">
    </div>

    <div class="field">
      <label for="msg-template">Template</label>
      <textarea id="msg-template" oninput="rerenderPreview()"></textarea>
      <div class="placeholders">Placeholders: <code>{first_name}</code> <code>{name}</code> <code>{company}</code> <code>{role}</code> <code>{persona}</code> <code>{event}</code> <code>{event_type}</code> <code>{city}</code></div>
    </div>

    <div class="field">
      <label>Apply to others — pick how many recipients</label>
      <div class="slider-row">
        <input type="range" id="msg-slider" min="1" max="1" value="1" oninput="document.getElementById('msg-slider-val').textContent=this.value;rerenderPreview()">
        <span><b id="msg-slider-val">1</b> recipients</span>
      </div>
      <div style="font-size:12px;color:#888">Includes the focus person + the next N-1 by fit_score order.</div>
    </div>

    <div class="field">
      <label>Preview</label>
      <div class="preview-list" id="msg-preview-list"></div>
    </div>

    <div class="action-row">
      <button class="btn-secondary" onclick="closeMsg()">Cancel</button>
      <button onclick="openAllMail()" style="margin-top:0">📧 Open drafts in mail client</button>
    </div>
    <div style="font-size:12px;color:#888;margin-top:10px">
      Drafts open in your default mail app pre-filled with subject + body. Nothing is sent automatically — you click Send yourself in each draft.
    </div>
  </div>
</div>

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
  ALL_PEOPLE = people;  // global so modal can rebuild previews
  EVENT_SUMMARY = s;
  let html = `<div class="summary">
    Sourced <b>${s.ranked_count}</b> prospects · <b>${s.high_priority_count}</b> high-priority · top gap: <b>${s.top_gap_persona||'-'}</b><br>
    <a href="/download/ranked_people.csv" download style="display:inline-block;margin-top:8px;margin-right:8px;padding:6px 12px;background:#0a7d2c;color:#fff;text-decoration:none;border-radius:4px;font-size:13px">⬇ ranked_people.csv</a>
    <a href="/download/event_state.json" download style="display:inline-block;margin-top:8px;margin-right:8px;padding:6px 12px;background:#444;color:#fff;text-decoration:none;border-radius:4px;font-size:13px">⬇ event_state.json</a>
    <button class="btn-secondary" id="btn-discover">🔍 Discover contacts</button>
    <span id="discover-status" style="margin-left:10px;color:#888;font-size:12px"></span>
  </div>`;
  if(top.length){
    html += '<table><tr><th>#</th><th>Fit</th><th>Priority</th><th>Persona</th><th>Name</th><th>Role</th><th>Company</th><th>Contact</th><th></th></tr>';
    top.forEach((p,i)=>{
      html += `<tr>
        <td>${i+1}</td><td>${p.fit_score||''}</td>
        <td class="pri-${(p.priority||'').replace(/[^a-z_]/gi,'')}">${p.priority||''}</td>
        <td>${p.persona||''}</td><td>${p.name||''}</td><td>${p.role||''}</td><td>${p.company||''}</td>
        <td>${contactIcons(p)}</td>
        <td><button class="btn-msg" data-name="${escapeHtml(p.name||'')}" onclick="openMsg(this.dataset.name)">✉ Message</button></td>
      </tr>`;
    });
    html += '</table>';
    if(people.length > 30) html += `<p style="color:#888">… ${people.length - 30} more in ranked_people.csv</p>`;
  } else {
    html += '<div class="warn">No prospects — usually means ANTHROPIC_API_KEY isn\\'t set.</div>';
  }
  result.innerHTML = html;
  const dbtn = document.getElementById('btn-discover');
  if(dbtn) dbtn.onclick = discoverContacts;
}

function escapeHtml(s){return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function contactIcons(p){
  const items = [];
  if(p.email) items.push(`<a href="mailto:${escapeHtml(p.email)}" title="${escapeHtml(p.email)}">✉</a>`);
  else items.push('<span class="miss" title="no email">✉</span>');
  if(p.linkedin_url) items.push(`<a href="${escapeHtml(p.linkedin_url)}" target="_blank" title="LinkedIn">in</a>`);
  else items.push('<span class="miss" title="no LinkedIn">in</span>');
  if(p.twitter) items.push(`<a href="https://x.com/${encodeURIComponent(String(p.twitter).replace(/^@/, ''))}" target="_blank" title="X / Twitter">𝕏</a>`);
  else items.push('<span class="miss" title="no X">𝕏</span>');
  return `<span class="contact-icons">${items.join(' ')}</span>`;
}

async function discoverContacts(){
  const dbtn = document.getElementById('btn-discover');
  const dst = document.getElementById('discover-status');
  if(dbtn) dbtn.disabled = true;
  if(dst) dst.textContent = 'searching the web for public contacts… (~30s)';
  try {
    const r = await fetch('/contacts/discover', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({only_missing:true})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'discovery failed');
    if(dst) dst.textContent = `enriched ${data.enriched} of ${data.considered} considered (${data.total} total). Refreshing…`;
    // re-fetch the people list and re-render
    const peopleResp = await fetch('/people');
    const people = (await peopleResp.json()).people || [];
    renderResult(EVENT_SUMMARY, people);
    if(dst) dst.textContent = `enriched ${data.enriched} of ${data.considered} considered.`;
  } catch(e){
    if(dst) dst.textContent = 'discovery failed: ' + e.message;
  } finally { if(dbtn) dbtn.disabled = false; }
}

// ---------- Message modal ----------
let ALL_PEOPLE = [], EVENT_SUMMARY = {}, MSG_FOCUS_NAME = '';
const DEFAULT_TEMPLATE = "Hi {first_name},\\n\\nI'm putting together {event} and would love for you to come — hand-picking other {persona}s building at companies like {company}.\\n\\nIf the timing works, reply and I'll send details.\\n\\nThanks!";

function openMsg(name){
  MSG_FOCUS_NAME = name;
  const focus = ALL_PEOPLE.find(p => (p.name||'').trim() === name) || ALL_PEOPLE[0];
  document.getElementById('msg-focus-name').textContent = focus.name || '';
  document.getElementById('msg-focus-meta').textContent = [focus.role, focus.company, focus.persona].filter(Boolean).join(' · ');
  document.getElementById('msg-focus-contact').innerHTML = contactIcons(focus);
  // Default template if textarea is empty.
  const ta = document.getElementById('msg-template');
  if(!ta.value.trim()) ta.value = DEFAULT_TEMPLATE;
  // Slider: default to "just this one person"
  const slider = document.getElementById('msg-slider');
  slider.max = ALL_PEOPLE.length;
  slider.value = 1;
  document.getElementById('msg-slider-val').textContent = '1';
  document.getElementById('msg-modal').classList.add('show');
  rerenderPreview();
}
function closeMsg(){ document.getElementById('msg-modal').classList.remove('show'); }

function selectedPeople(){
  // Always include the focus person; then top-N by rank order.
  const n = parseInt(document.getElementById('msg-slider').value, 10) || 1;
  const focus = ALL_PEOPLE.find(p => (p.name||'').trim() === MSG_FOCUS_NAME);
  const rest = ALL_PEOPLE.filter(p => p !== focus);
  const picked = focus ? [focus, ...rest.slice(0, Math.max(0, n-1))] : rest.slice(0, n);
  return picked;
}

async function rerenderPreview(){
  const tmpl = document.getElementById('msg-template').value;
  const picked = selectedPeople();
  const names = picked.map(p => p.name);
  const r = await fetch('/messages/render', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({template: tmpl, names})});
  const data = await r.json();
  const list = document.getElementById('msg-preview-list');
  if(!data.messages || !data.messages.length){
    list.innerHTML = '<div style="padding:12px;color:#888">No people matched.</div>';
    return;
  }
  list.innerHTML = data.messages.map(m => `
    <div class="preview-row">
      <div class="pname">
        <span>${escapeHtml(m.name)} <span style="color:#888;font-weight:400">— ${escapeHtml(m.role||'')} @ ${escapeHtml(m.company||'')}</span> <span class="channel">${m.channel}${m.email ? ': ' + escapeHtml(m.email) : ''}</span></span>
        ${m.email ? `<a href="${mailtoFor(m)}" style="font-size:12px;color:#0a7d2c;text-decoration:none;border:1px solid #0a7d2c;padding:2px 8px;border-radius:3px">Open in mail ↗</a>` : '<span style="font-size:11px;color:#a36c00">no email — skip</span>'}
      </div>
      <div class="pmsg">${escapeHtml(m.rendered)}</div>
    </div>
  `).join('');
}

function mailtoFor(m){
  const subject = (document.getElementById('msg-subject').value || 'Invitation').trim();
  const body = m.rendered;
  return `mailto:${encodeURIComponent(m.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

async function openAllMail(){
  const tmpl = document.getElementById('msg-template').value;
  const picked = selectedPeople();
  const names = picked.map(p => p.name);
  const r = await fetch('/messages/render', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({template: tmpl, names})});
  const data = await r.json();
  const withEmail = (data.messages||[]).filter(m => m.email);
  if(!withEmail.length){ alert('No emails available — discover contacts first or skip recipients without email.'); return; }
  if(!confirm(`This will open ${withEmail.length} draft email(s) in your mail client. Each draft is pre-filled but NOT sent — you'll click Send yourself in each one. Continue?`)) return;
  withEmail.forEach((m, i) => setTimeout(() => { window.location.href = mailtoFor(m); }, i * 250));
}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return _INDEX_HTML


@app.get("/people")
async def people():
    """Return the most recent ranked_people.csv as JSON."""
    import csv as _csv
    csv_path = _REPO_ROOT / "data" / "ranked_people.csv"
    if not csv_path.exists():
        return {"people": []}
    with csv_path.open() as f:
        rows = list(_csv.DictReader(f))
    return {"people": rows}


@app.get("/download/ranked_people.csv")
async def download_ranked():
    """Stream the most recent ranked_people.csv as a file download."""
    csv_path = _REPO_ROOT / "data" / "ranked_people.csv"
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
    p = _REPO_ROOT / "data" / "event_state.json"
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
