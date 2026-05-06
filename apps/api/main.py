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
from apps.api.routes import organization as organization_routes
from apps.api.routes import event_meta as event_meta_routes
from apps.api.routes import budget as budget_routes
from apps.api.routes import attendees as attendees_routes

app = FastAPI(title="Eventful API", version="0.1.0")

app.include_router(run_routes.router)
app.include_router(messages_routes.router)
app.include_router(organization_routes.router)
app.include_router(event_meta_routes.router)
app.include_router(budget_routes.router)
app.include_router(attendees_routes.router)


_INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Eventful</title>
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
/* Tabs */
.tabs{display:flex;gap:4px;border-bottom:1px solid #ddd;margin-bottom:20px}
.tab{padding:10px 18px;cursor:pointer;border:0;background:none;font:inherit;color:#666;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.active{color:#111;border-bottom-color:#111;font-weight:600}
.tab-panel{display:none}
.tab-panel.active{display:block}
/* Org tab */
.org-pills{display:flex;gap:6px;margin-bottom:16px}
.pill{padding:6px 14px;cursor:pointer;border:1px solid #ccc;background:#fff;border-radius:20px;font:inherit;font-size:13px;color:#444}
.pill.active{background:#111;color:#fff;border-color:#111}
.org-form{background:#fafafa;border:1px solid #eee;border-radius:8px;padding:16px;margin-bottom:16px}
.org-form .row{display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap}
.org-form .row > div{flex:1;min-width:180px}
.org-form input,.org-form select{width:100%;padding:7px 9px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
.org-form label{display:block;font-size:11px;color:#666;margin-bottom:3px;text-transform:uppercase;letter-spacing:.5px}
.org-form .actions{display:flex;justify-content:space-between;align-items:center;margin-top:6px}
.org-cards{display:grid;grid-template-columns:1fr;gap:10px}
.org-card{border:1px solid #e2e2e2;border-radius:8px;padding:12px 14px;background:#fff}
.org-card .head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.org-card .name{font-weight:600;font-size:14px;color:#111}
.org-card .meta{font-size:12px;color:#666;margin-top:2px}
.org-card .cost{font-size:13px;color:#0a7d2c;font-weight:600}
.org-card .rating{font-size:12px;color:#a36c00}
.org-card .actions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.org-card .actions .btn-msg,.org-card .actions a.btn-msg{text-decoration:none}
.org-card .desc{font-size:12.5px;color:#444;margin-top:6px;line-height:1.4}
.org-card details{margin-top:8px;font-size:12px;color:#444}
.org-card details summary{cursor:pointer;color:#666;font-size:12px}
.org-card details ul{margin:6px 0 0 18px;padding:0}
.amenity{display:inline-block;font-size:11px;background:#f0f0f0;padding:2px 7px;border-radius:10px;margin:2px 3px 0 0}
.org-tabbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:13px;color:#666}
.saved-pill{font-size:11px;background:#fef7d8;padding:2px 8px;border-radius:10px;color:#a36c00}
.btn-star{background:none;border:0;cursor:pointer;font-size:16px;padding:0 4px;color:#bbb}
.btn-star.saved{color:#f5a623}
/* Budget tab */
.bd-header{font-size:13px;color:#666;margin-bottom:14px}
.bd-totals{margin-bottom:18px}
.bd-bar-wrap{margin-bottom:20px}
.bd-bar{height:14px;width:100%;background:#eee;border-radius:7px;overflow:hidden}
.bd-bar-fill{height:100%;background:#0a7d2c;transition:width .25s ease,background .25s ease;width:0%}
.bd-bar-fill.warn{background:#a36c00}
.bd-bar-fill.over{background:#c33}
.bd-bar-text{margin-top:6px;font-size:13px;color:#444}
.bd-cat{border:1px solid #eee;border-radius:6px;margin-bottom:10px;background:#fff}
.bd-cat summary{padding:10px 14px;cursor:pointer;font-weight:600;display:flex;justify-content:space-between;align-items:center;list-style:none}
.bd-cat summary::-webkit-details-marker{display:none}
.bd-cat .cat-meta{font-size:12px;color:#888;font-weight:400}
.bd-cat .cat-body{padding:6px 14px 14px;border-top:1px solid #f4f4f4}
.bd-li-row{display:grid;grid-template-columns:1fr 110px 130px 60px;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid #f4f4f4;font-size:13px}
.bd-li-row:last-child{border-bottom:0}
.bd-li-name{font-size:13px}
.bd-li-name .src{font-size:11px;color:#888;margin-left:6px}
.bd-li-cost input,.bd-li-status select{width:100%;padding:4px 6px;font:inherit;font-size:12px;border:1px solid #ddd;border-radius:3px}
.bd-li-del{background:none;border:0;cursor:pointer;color:#bbb;font-size:14px}
.bd-li-del:hover{color:#c33}
.bd-add-form{display:grid;grid-template-columns:1fr 110px 80px;gap:8px;margin-top:8px}
.bd-add-form input{padding:5px 7px;font:inherit;font-size:12px;border:1px solid #ddd;border-radius:3px}
.bd-add-form button{font-size:12px;padding:4px 10px}
.bd-sponsor{margin-top:18px;padding:12px;background:#fafafa;border-radius:6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
/* Attendees tab */
.att-header{font-size:13px;margin-bottom:14px}
.att-add{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px}
#att-list th{background:#fafafa;font-size:12px;color:#666;text-transform:uppercase;letter-spacing:.4px}
#att-list td{padding:6px 8px;border-bottom:1px solid #f4f4f4;vertical-align:middle}
#att-list select{padding:3px 6px;font:inherit;font-size:12px;border:1px solid #ddd;border-radius:3px}
#att-list input.att-notes{width:100%;padding:3px 6px;font:inherit;font-size:12px;border:1px solid transparent;border-radius:3px;background:transparent}
#att-list input.att-notes:focus{border-color:#ddd;background:#fff;outline:0}
.att-status-Confirmed{color:#0a7d2c;font-weight:600}
.att-status-Declined{color:#888}
.att-status-Attended{color:#0a7d2c}
.att-status-Invited{color:#a36c00}
.att-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
.att-dot-Invited{background:#bbb}
.att-dot-Confirmed{background:#0a7d2c}
.att-dot-Declined{background:#c33}
.att-dot-Attended{background:#0a7d2c}
</style></head>
<body>
<h1>OneLoop</h1>
<div class="sub">Plan a curated event end-to-end — find the right people, then organize the logistics.</div>

<!-- GLOBAL INPUT — drives both tabs. Above the tab strip on purpose. -->
<div id="warn"></div>
<textarea id="brief" placeholder="e.g. 100-person crypto hackathon for builders, founders, ZK researchers in SF..."></textarea>
<div><button id="go">Run pipeline</button> <span id="status" style="margin-left:12px;color:#888"></span></div>

<!-- EVENT DATE — anchors Budget/Attendees headers and the {event_date} message placeholder. -->
<div class="event-date-row" style="margin-top:18px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
  <label for="ev-date" style="font-size:13px;color:#444">Event date</label>
  <input id="ev-date" type="date" style="padding:6px 8px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px">
  <input id="ev-start" type="time" style="padding:6px 8px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px" title="Start time (optional)">
  <span style="font-size:12px;color:#888">to</span>
  <input id="ev-end" type="time" style="padding:6px 8px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px" title="End time (optional)">
  <span id="ev-date-status" style="font-size:12px;color:#888;margin-left:6px"></span>
</div>

<!-- TABS — pure view-switchers; do not gate the input. -->
<div class="tabs" style="margin-top:24px">
  <button class="tab active" data-tab="ei" onclick="switchTab('ei')">Eventful</button>
  <button class="tab" data-tab="org" onclick="switchTab('org')">Organization</button>
  <button class="tab" data-tab="budget" onclick="switchTab('budget')">Budget</button>
  <button class="tab" data-tab="attendees" onclick="switchTab('attendees')">Attendees</button>
</div>

<!-- TAB: Eventful -->
<div class="tab-panel active" id="panel-ei">
<div class="result" id="result"></div>
</div>

<!-- TAB: Organization -->
<div class="tab-panel" id="panel-org">
  <div class="org-pills">
    <button class="pill active" data-cat="venues" onclick="switchCat('venues')">🏛 Venues</button>
    <button class="pill" data-cat="caterers" onclick="switchCat('caterers')">🍽 Caterers</button>
    <button class="pill" data-cat="sponsors" onclick="switchCat('sponsors')">🤝 Sponsors</button>
  </div>

  <!-- Search forms -->
  <div class="org-form" id="form-venues">
    <div class="row">
      <div><label>Location</label><input id="v-location" placeholder="San Francisco, SoMa"></div>
      <div><label>Capacity</label><input id="v-capacity" type="number" placeholder="100" min="1"></div>
      <div><label>Date / availability</label><input id="v-availability" placeholder="Sat May 17, evening"></div>
    </div>
    <div class="row">
      <div><label>Amenities</label><input id="v-amenities" placeholder="AV, wifi, kitchen"></div>
      <div><label>Budget</label><input id="v-budget" placeholder="up to $5k"></div>
      <div><label>Sort by</label>
        <select id="v-sort"><option value="relevance">relevance</option><option value="cost">cost (low → high)</option><option value="rating">rating</option></select>
      </div>
    </div>
    <div class="actions">
      <span style="font-size:12px;color:#888">~30s · ~$0.30 first time, free if cached</span>
      <button onclick="orgSearch('venues')">Search venues</button>
    </div>
  </div>

  <div class="org-form" id="form-caterers" style="display:none">
    <div class="row">
      <div><label>Location</label><input id="c-location" placeholder="San Francisco"></div>
      <div><label>Cuisine</label><input id="c-cuisine" placeholder="Mediterranean / Pan-Asian"></div>
      <div><label>Headcount</label><input id="c-headcount" type="number" placeholder="100"></div>
    </div>
    <div class="row">
      <div><label>Dietary needs</label><input id="c-dietary" placeholder="vegan, gluten-free"></div>
      <div><label>Budget per head</label><input id="c-budget" placeholder="$30-50pp"></div>
      <div><label>Sort by</label>
        <select id="c-sort"><option value="relevance">relevance</option><option value="cost">cost (low → high)</option><option value="rating">rating</option></select>
      </div>
    </div>
    <div class="actions">
      <span style="font-size:12px;color:#888">~30s · ~$0.30 first time, free if cached</span>
      <button onclick="orgSearch('caterers')">Search caterers</button>
    </div>
  </div>

  <div class="org-form" id="form-sponsors" style="display:none">
    <div class="row">
      <div><label>Industry / theme</label><input id="s-industry" placeholder="crypto / dev tools / AI infra"></div>
      <div><label>Company size</label><input id="s-size" placeholder="Series B+, 200+ emp"></div>
      <div><label>Sponsorship budget</label><input id="s-budget" placeholder="$10-50k tier"></div>
    </div>
    <div class="row">
      <div><label>Notes</label><input id="s-notes" placeholder="hackathons, demo nights"></div>
      <div></div>
      <div><label>Sort by</label>
        <select id="s-sort"><option value="relevance">relevance</option><option value="cost">budget (low → high)</option><option value="rating">rating</option></select>
      </div>
    </div>
    <div class="actions">
      <span style="font-size:12px;color:#888">~30s · ~$0.30 first time, free if cached</span>
      <button onclick="orgSearch('sponsors')">Search sponsors</button>
    </div>
  </div>

  <div id="org-banner" style="display:none;background:#eef7f0;border:1px solid #c5e3cd;color:#0a5d28;padding:8px 12px;border-radius:6px;margin-bottom:12px;font-size:13px;display:flex;justify-content:space-between;align-items:center;gap:8px">
    <span><b>Auto-sourced from your Eventful prompt.</b> <span id="org-banner-meta" style="color:#3d6f4d"></span></span>
    <button class="btn-secondary" onclick="retryCategory(ORG_CAT)" title="Re-run search for the current category" style="padding:4px 10px;font-size:12px">🔄 Re-run this category</button>
  </div>

  <div class="org-tabbar">
    <span id="org-status" style="color:#888"></span>
    <span><button class="btn-secondary" onclick="toggleSaved()" id="btn-show-saved">★ Show saved</button></span>
  </div>

  <div class="org-cards" id="org-results"></div>
</div>

<!-- TAB: Budget -->
<div class="tab-panel" id="panel-budget">
  <div class="bd-header">
    <span id="bd-event-line" style="color:#666"></span>
  </div>
  <div class="bd-totals">
    <label style="display:block;font-size:12px;color:#666;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">What's your total budget?</label>
    <div style="display:flex;align-items:center;gap:8px">
      <span style="font-size:18px;color:#888">$</span>
      <input id="bd-total" type="number" min="0" step="100" placeholder="10000" style="width:160px;padding:8px;font:inherit;font-size:15px;border:1px solid #ccc;border-radius:4px">
      <button class="btn-secondary" onclick="saveBudgetTotal()" style="padding:6px 12px">Save</button>
      <span id="bd-total-status" style="font-size:12px;color:#888"></span>
    </div>
  </div>

  <div class="bd-bar-wrap">
    <div class="bd-bar" id="bd-bar"><div class="bd-bar-fill" id="bd-bar-fill"></div></div>
    <div class="bd-bar-text" id="bd-bar-text"></div>
  </div>

  <div id="bd-categories"></div>

  <div class="bd-sponsor">
    <label style="font-size:13px;color:#444">Sponsor contributions</label>
    <span style="color:#888">$</span>
    <input id="bd-sponsor" type="number" min="0" step="100" placeholder="0" style="width:120px;padding:6px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px">
    <button class="btn-secondary" onclick="saveSponsorIncome()" style="padding:4px 10px;font-size:12px">Save</button>
    <span style="font-size:12px;color:#888">subtracts from total spent</span>
  </div>
</div>

<!-- TAB: Attendees -->
<div class="tab-panel" id="panel-attendees">
  <div class="att-header" id="att-header" style="color:#666"></div>
  <div class="att-add">
    <input id="att-name" placeholder="Name" style="padding:7px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px">
    <input id="att-company" placeholder="Company" style="padding:7px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px">
    <input id="att-email" placeholder="Email (optional)" style="padding:7px;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:4px">
    <button onclick="addAttendee()" style="padding:7px 14px">Add attendee</button>
    <span id="att-add-status" style="font-size:12px;color:#888"></span>
  </div>
  <div id="att-list-wrap">
    <table id="att-list" style="width:100%;border-collapse:collapse;font-size:13px;margin-top:14px">
      <thead><tr><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd">Status</th><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd">Name</th><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd">Company</th><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #ddd">Notes</th></tr></thead>
      <tbody id="att-rows"></tbody>
    </table>
  </div>
</div>

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
    // Refresh event metadata so the date picker reflects any date the
    // objective_agent extracted from the brief.
    loadEventMeta();
    // Auto-fire org searches in parallel — don't await; people table is
    // already on screen and org cards stream in to their pills as each
    // /org/search promise resolves.
    autoFireOrgSearches();
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
const DEFAULT_TEMPLATE = "Hi {first_name},\\n\\nI'm putting together {event} on {event_date} and would love for you to come — hand-picking other {persona}s building at companies like {company}.\\n\\nConfirm here: {confirm_link}\\n\\nThanks!";

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

// ---------- Tabs ----------
function switchTab(name){
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + name));
}

// ---------- Organization tab ----------
let ORG_CAT = 'venues';
let SHOWING_SAVED = false;
// Per-category in-memory store. Persists for the page session so flipping
// pills doesn't refetch. Auto-fired results land here as each promise resolves.
const ORG_STATE = {
  venues:   { status: 'idle', results: [], error: '', sort: 'relevance', autoSourced: false, lastQuery: null, autoBatchId: 0 },
  caterers: { status: 'idle', results: [], error: '', sort: 'relevance', autoSourced: false, lastQuery: null, autoBatchId: 0 },
  sponsors: { status: 'idle', results: [], error: '', sort: 'relevance', autoSourced: false, lastQuery: null, autoBatchId: 0 },
};
let AUTO_BATCH_ID = 0;  // bump when a new EI run kicks off auto-search

function switchCat(cat){
  ORG_CAT = cat;
  document.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p.dataset.cat === cat));
  ['venues','caterers','sponsors'].forEach(c => {
    const f = document.getElementById('form-' + c);
    if(f) f.style.display = (c === cat) ? '' : 'none';
  });
  SHOWING_SAVED = false;
  document.getElementById('btn-show-saved').textContent = '★ Show saved';
  renderOrgCards();
  refreshOrgStatus();
}

function readQuery(cat){
  if(cat === 'venues'){
    return {
      location: v('v-location'),
      capacity: v('v-capacity'),
      availability: v('v-availability'),
      amenities: v('v-amenities'),
      budget: v('v-budget'),
      limit: 12,
    };
  }
  if(cat === 'caterers'){
    return {
      location: v('c-location'),
      cuisine: v('c-cuisine'),
      headcount: v('c-headcount'),
      dietary: v('c-dietary'),
      budget_per_head: v('c-budget'),
      limit: 12,
    };
  }
  if(cat === 'sponsors'){
    return {
      industry: v('s-industry'),
      size: v('s-size'),
      budget: v('s-budget'),
      notes: v('s-notes'),
      limit: 12,
    };
  }
  return {};
}
function v(id){ return (document.getElementById(id)?.value || '').trim(); }

async function orgSearch(cat, opts){
  // opts: { query?, sort?, autoSourced?, suppressActiveSwitch? }
  opts = opts || {};
  const sortEl = document.getElementById({venues:'v-sort',caterers:'c-sort',sponsors:'s-sort'}[cat]);
  const sort = opts.sort || (sortEl ? sortEl.value : 'relevance');
  const query = opts.query || readQuery(cat);
  const autoSourced = !!opts.autoSourced;

  // Manual search overrides any prior auto-fire result for this category.
  const st = ORG_STATE[cat];
  st.status = 'loading';
  st.error = '';
  st.results = [];
  st.sort = sort;
  st.lastQuery = query;
  st.autoSourced = autoSourced;

  if(!opts.suppressActiveSwitch){
    SHOWING_SAVED = false;
    document.getElementById('btn-show-saved').textContent = '★ Show saved';
  }

  // Render the loading state if user is currently looking at this pill.
  if(ORG_CAT === cat) renderOrgCards();
  refreshOrgStatus();
  updatePillBadges();

  const t0 = Date.now();
  try {
    const r = await fetch('/org/search', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({category: cat, query, sort})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'search failed');
    st.status = 'ok';
    st.results = data.results || [];
    st.elapsed = ((Date.now()-t0)/1000).toFixed(1);
    st.cached = !!(data.telemetry && data.telemetry.status === 'cached');
  } catch(e) {
    st.status = 'error';
    st.error = e.message || String(e);
  }
  if(ORG_CAT === cat) renderOrgCards();
  refreshOrgStatus();
  updatePillBadges();
}

function retryCategory(cat){
  const st = ORG_STATE[cat];
  // Use the saved last query (auto-fire or manual). If none, fall back to
  // reading the form.
  const q = st.lastQuery || readQuery(cat);
  orgSearch(cat, {query: q, sort: st.sort, autoSourced: st.autoSourced});
}

function refreshOrgStatus(){
  const st = ORG_STATE[ORG_CAT];
  const s = document.getElementById('org-status');
  if(!s) return;
  if(SHOWING_SAVED){ s.textContent = `${getSaved().length} saved in ${ORG_CAT}`; return; }
  if(st.status === 'idle'){ s.textContent = ''; return; }
  if(st.status === 'loading'){ s.textContent = `searching ${ORG_CAT}…`; return; }
  if(st.status === 'error'){ s.textContent = `failed: ${st.error}`; return; }
  if(st.status === 'ok'){
    s.textContent = `${st.results.length} result(s) · sort: ${st.sort}${st.cached ? ' · cached (free)' : ''}${st.elapsed ? ' · '+st.elapsed+'s' : ''}${st.autoSourced ? ' · auto-sourced' : ''}`;
  }
}

function updatePillBadges(){
  // Show a tiny status dot on each pill so user can see all three categories'
  // progress at a glance even while looking at one of them.
  ['venues','caterers','sponsors'].forEach(c => {
    const pill = document.querySelector(`.pill[data-cat="${c}"]`);
    if(!pill) return;
    const st = ORG_STATE[c];
    // strip any existing dot
    pill.querySelectorAll('.pill-dot').forEach(n => n.remove());
    const dot = document.createElement('span');
    dot.className = 'pill-dot';
    dot.style.cssText = 'display:inline-block;width:7px;height:7px;border-radius:50%;margin-left:6px;vertical-align:middle';
    if(st.status === 'loading'){ dot.style.background = '#a36c00'; dot.title = 'loading'; }
    else if(st.status === 'ok'){ dot.style.background = '#0a7d2c'; dot.title = `${st.results.length} results`; }
    else if(st.status === 'error'){ dot.style.background = '#c33'; dot.title = 'error: ' + st.error; }
    else { return; /* idle: no dot */ }
    pill.appendChild(dot);
  });
}

// Pre-populate forms from event summary so user can see/edit what was searched.
function fillVenueForm(q){
  document.getElementById('v-location').value = q.location || '';
  document.getElementById('v-capacity').value = q.capacity || '';
  document.getElementById('v-availability').value = q.availability || '';
  document.getElementById('v-amenities').value = q.amenities || '';
  document.getElementById('v-budget').value = q.budget || '';
}
function fillCatererForm(q){
  document.getElementById('c-location').value = q.location || '';
  document.getElementById('c-cuisine').value = q.cuisine || '';
  document.getElementById('c-headcount').value = q.headcount || '';
  document.getElementById('c-dietary').value = q.dietary || '';
  document.getElementById('c-budget').value = q.budget_per_head || '';
}
function fillSponsorForm(q){
  document.getElementById('s-industry').value = q.industry || '';
  document.getElementById('s-size').value = q.size || '';
  document.getElementById('s-budget').value = q.budget || '';
  document.getElementById('s-notes').value = q.notes || '';
}

// Build category-specific queries from event summary. Locked-in scope:
//   Venues   = location + capacity + format hint
//   Caterers = location + headcount
//   Sponsors = industry/theme (from format+goal) + notes (goal)
function deriveOrgQueries(summary){
  const fmt = (summary.format || '').trim();
  const city = (summary.city || '').trim();
  const size = summary.target_size || '';
  const goal = (summary.goal || '').trim();
  const themeHint = [fmt, goal].filter(Boolean).join(' — ');
  return {
    venues: {
      location: city + (fmt ? ` (suitable for a ${fmt})` : ''),
      capacity: size,
      availability: '',
      amenities: '',
      budget: '',
      limit: 12,
    },
    caterers: {
      location: city,
      cuisine: '',
      headcount: size,
      dietary: '',
      budget_per_head: '',
      limit: 12,
    },
    sponsors: {
      industry: themeHint,
      size: '',
      budget: '',
      notes: goal,
      limit: 12,
    },
  };
}

async function autoFireOrgSearches(){
  // Pull the latest event summary, derive per-category queries, fan out
  // three parallel searches. Doesn't block — caller already returned.
  let summary;
  try {
    const r = await fetch('/event/summary');
    summary = await r.json();
    if(!summary || !summary.ok) return;  // no event_state → nothing to auto-source
  } catch(_){ return; }

  const queries = deriveOrgQueries(summary);
  AUTO_BATCH_ID++;

  // Show banner on Org tab.
  const banner = document.getElementById('org-banner');
  const meta = document.getElementById('org-banner-meta');
  if(banner) banner.style.display = 'flex';
  if(meta) meta.textContent = [summary.format, summary.city, summary.target_size ? summary.target_size + ' people' : ''].filter(Boolean).join(' · ');

  // Pre-fill forms (user can still edit).
  fillVenueForm(queries.venues);
  fillCatererForm(queries.caterers);
  fillSponsorForm(queries.sponsors);

  // Fan out — each call mutates ORG_STATE[cat] independently.
  // We don't await so failures in one don't delay the others (orgSearch
  // already isolates errors per-category).
  ['venues','caterers','sponsors'].forEach(cat => {
    ORG_STATE[cat].autoBatchId = AUTO_BATCH_ID;
    orgSearch(cat, {query: queries[cat], sort: 'relevance', autoSourced: true, suppressActiveSwitch: true});
  });
}

function savedKey(){ return 'ei.org.saved.' + ORG_CAT; }
function getSaved(){ try{ return JSON.parse(localStorage.getItem(savedKey())||'[]'); }catch(_){ return []; } }
function setSaved(arr){ localStorage.setItem(savedKey(), JSON.stringify(arr)); }
function isSaved(item){ return getSaved().some(s => s.name === item.name); }
function toggleSave(idx){
  const item = (SHOWING_SAVED ? getSaved() : ORG_STATE[ORG_CAT].results)[idx];
  if(!item) return;
  let saved = getSaved();
  if(saved.some(s => s.name === item.name)){
    saved = saved.filter(s => s.name !== item.name);
  } else {
    saved.push(item);
  }
  setSaved(saved);
  renderOrgCards();
}
function toggleSaved(){
  SHOWING_SAVED = !SHOWING_SAVED;
  document.getElementById('btn-show-saved').textContent = SHOWING_SAVED ? '⊕ Show search results' : '★ Show saved';
  renderOrgCards();
  refreshOrgStatus();
}

function renderOrgCards(){
  const root = document.getElementById('org-results');
  const st = ORG_STATE[ORG_CAT];

  if(SHOWING_SAVED){
    const list = getSaved();
    root.innerHTML = list.length
      ? list.map((it, i) => orgCardHtml(it, i)).join('')
      : '<div style="color:#888;padding:12px">No saved items in this category yet. Run a search and click ★ on results to shortlist.</div>';
    return;
  }

  if(st.status === 'loading'){
    root.innerHTML = `<div style="padding:14px;color:#888">⏳ searching ${ORG_CAT}… (typical 20–40s, free if cached)</div>`;
    return;
  }
  if(st.status === 'error'){
    root.innerHTML = `<div class="warn err" style="display:flex;justify-content:space-between;align-items:center"><span>${escapeHtml(st.error||'search failed')}</span><button class="btn-secondary" onclick="retryCategory('${ORG_CAT}')" style="padding:4px 10px;font-size:12px">Retry</button></div>`;
    return;
  }
  if(st.status === 'ok'){
    root.innerHTML = st.results.length
      ? st.results.map((it, i) => orgCardHtml(it, i)).join('')
      : '<div style="color:#888;padding:12px">No results — try broadening the query or removing filters.</div>';
    return;
  }
  // idle
  root.innerHTML = '';
}

function orgCardHtml(it, i){
  const cost = costLine(it);
  const rating = it.rating ? `<span class="rating">★ ${(+it.rating).toFixed(1)}</span>` : '';
  const saved = isSaved(it);
  const meta = metaLine(it);
  const desc = it.description ? `<div class="desc">${escapeHtml(it.description)}</div>` : '';
  const details = detailsHtml(it);
  const contactBtn = (it.contact_email || it.website)
    ? (it.contact_email
        ? `<a class="btn-msg" href="${mailtoOrg(it)}">✉ Contact</a>`
        : `<a class="btn-msg" href="${escapeHtml(it.website)}" target="_blank">↗ Open site</a>`)
    : '<span style="font-size:11px;color:#a36c00">no contact found</span>';
  return `
    <div class="org-card">
      <div class="head">
        <div>
          <div class="name">${escapeHtml(it.name||'(no name)')} ${saved ? '<span class="saved-pill">saved</span>':''}</div>
          <div class="meta">${meta}</div>
        </div>
        <div style="text-align:right">
          <div class="cost">${escapeHtml(cost)}</div>
          ${rating}
          <div><button class="btn-star ${saved?'saved':''}" onclick="toggleSave(${i})" title="${saved?'Unshortlist':'Shortlist'}">★</button></div>
        </div>
      </div>
      ${desc}
      ${details}
      <div class="actions">
        ${contactBtn}
        ${it.website ? `<a class="btn-msg" href="${escapeHtml(it.website)}" target="_blank">↗ Website</a>` : ''}
        ${it.source_url ? `<a class="btn-msg" href="${escapeHtml(it.source_url)}" target="_blank">↗ Source</a>` : ''}
      </div>
    </div>`;
}

function metaLine(it){
  if(ORG_CAT === 'venues'){
    return [it.address, it.city && it.address?.includes(it.city) ? '' : it.city, it.capacity ? `cap ${it.capacity}` : ''].filter(Boolean).map(escapeHtml).join(' · ');
  }
  if(ORG_CAT === 'caterers'){
    return [it.cuisine_type, it.location, it.minimum_order ? `min ${it.minimum_order}` : ''].filter(Boolean).map(escapeHtml).join(' · ');
  }
  if(ORG_CAT === 'sponsors'){
    return [it.industry, it.company_size, it.budget_range].filter(Boolean).map(escapeHtml).join(' · ');
  }
  return '';
}
function costLine(it){
  if(ORG_CAT === 'venues') return it.rental_fee || '';
  if(ORG_CAT === 'caterers') return it.price_per_head || '';
  if(ORG_CAT === 'sponsors') return it.typical_sponsorship_amount || '';
  return '';
}
function detailsHtml(it){
  const parts = [];
  if(ORG_CAT === 'venues'){
    if(Array.isArray(it.amenities) && it.amenities.length){
      parts.push(it.amenities.map(a => `<span class="amenity">${escapeHtml(a)}</span>`).join(''));
    }
    if(it.minimum_spend) parts.push(`<div>Minimum spend: ${escapeHtml(it.minimum_spend)}</div>`);
  }
  if(ORG_CAT === 'caterers'){
    if(Array.isArray(it.dietary_accommodations) && it.dietary_accommodations.length){
      parts.push(it.dietary_accommodations.map(d => `<span class="amenity">${escapeHtml(d)}</span>`).join(''));
    }
    if(Array.isArray(it.pricing_tiers) && it.pricing_tiers.length){
      parts.push('<ul>' + it.pricing_tiers.map(t => `<li>${escapeHtml(t.name||'')}: ${escapeHtml(t.price||'')}</li>`).join('') + '</ul>');
    }
  }
  if(ORG_CAT === 'sponsors'){
    if(Array.isArray(it.past_events_sponsored) && it.past_events_sponsored.length){
      parts.push('<div><b>Past events:</b> ' + it.past_events_sponsored.slice(0,5).map(escapeHtml).join(', ') + '</div>');
    }
    if(it.contact_person) parts.push(`<div><b>Likely contact:</b> ${escapeHtml(it.contact_person)}</div>`);
  }
  if(!parts.length) return '';
  return `<details><summary>more details</summary><div style="margin-top:6px">${parts.join('')}</div></details>`;
}
function mailtoOrg(it){
  const subject = `Inquiry — event ${ORG_CAT === 'venues' ? 'venue' : ORG_CAT === 'caterers' ? 'catering' : 'sponsorship'}`;
  const body = `Hi ${it.contact_person || 'there'},\\n\\nI'm planning an event and would love to talk about ${ORG_CAT === 'sponsors' ? 'a possible sponsorship partnership' : ORG_CAT === 'caterers' ? 'catering options' : 'availability and pricing for ' + (it.name||'your space')}.\\n\\nQuick details about the event:\\n- ...\\n\\nHow does your team like to take inquiries?\\n\\nThanks!`;
  return `mailto:${encodeURIComponent(it.contact_email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

// ---------- Event date (anchors Budget + Attendees headers) ----------
let EVENT_META = {event_date:'', event_end_time:null, days_until:null, name:'', city:'', format:''};

function fmtEventLine(prefix){
  if(!EVENT_META.event_date) return prefix + ' (no date set)';
  const d = EVENT_META.event_date;
  const days = EVENT_META.days_until;
  let dayPart = '';
  if(days === 0) dayPart = ' · today';
  else if(days === 1) dayPart = ' · tomorrow';
  else if(typeof days === 'number' && days > 0) dayPart = ` · ${days} days away`;
  else if(typeof days === 'number' && days < 0) dayPart = ` · ${Math.abs(days)} days ago`;
  return `${prefix} ${d}${dayPart}`;
}

async function loadEventMeta(){
  try{
    const r = await fetch('/event');
    if(!r.ok) return;
    EVENT_META = await r.json();
    // Reflect into the date picker without overwriting user's in-progress edit.
    const inp = document.getElementById('ev-date');
    if(inp && document.activeElement !== inp){
      inp.value = (EVENT_META.event_date||'').slice(0,10);
    }
    refreshDateStatus();
    refreshBudgetHeader();
    refreshAttendeesHeader();
  }catch(_){/* noop */}
}

function refreshDateStatus(){
  const el = document.getElementById('ev-date-status');
  if(!el) return;
  if(!EVENT_META.event_date){ el.textContent = ''; return; }
  if(EVENT_META.is_past){
    el.textContent = '⚠ This date is in the past — is that intentional?';
    el.style.color = '#a36c00';
  } else {
    const days = EVENT_META.days_until;
    el.textContent = days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : (days > 0 ? `${days} days away` : '');
    el.style.color = '#888';
  }
}

async function saveEventDate(){
  const dateVal = document.getElementById('ev-date').value;
  const startVal = document.getElementById('ev-start').value;
  const endVal = document.getElementById('ev-end').value;
  let event_date = dateVal || '';
  if(event_date && startVal) event_date = event_date + 'T' + startVal;
  let event_end_time = null;
  if(dateVal && endVal) event_end_time = dateVal + 'T' + endVal;
  try{
    const r = await fetch('/event/date', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({event_date, event_end_time})});
    if(!r.ok) return;
    await loadEventMeta();
  }catch(_){/* noop */}
}

document.addEventListener('DOMContentLoaded', () => {
  ['ev-date','ev-start','ev-end'].forEach(id => {
    const el = document.getElementById(id);
    if(el) el.addEventListener('change', saveEventDate);
  });
  loadEventMeta();
});

// ---------- Budget tab ----------
const BUDGET_CATS = ["Venue","Food","A/V","Marketing","Other"];
let BD_STATE = {summary:{total_budget:0,spent:0,remaining:0,sponsor_income:0}, line_items:[]};

function refreshBudgetHeader(){
  const el = document.getElementById('bd-event-line');
  if(!el) return;
  el.textContent = fmtEventLine('Event:');
}

async function loadBudget(){
  // Push any shortlisted vendors over before loading; idempotent server-side.
  await pushShortlistToBudget();
  try{
    const r = await fetch('/budget');
    if(!r.ok) return;
    BD_STATE = await r.json();
  }catch(_){return;}
  const totalInp = document.getElementById('bd-total');
  if(totalInp && document.activeElement !== totalInp) totalInp.value = BD_STATE.summary.total_budget || '';
  const sponsorInp = document.getElementById('bd-sponsor');
  if(sponsorInp && document.activeElement !== sponsorInp) sponsorInp.value = BD_STATE.summary.sponsor_income || '';
  renderBudgetBar();
  renderBudgetCategories();
}

function renderBudgetBar(){
  const s = BD_STATE.summary || {};
  const total = +s.total_budget || 0;
  const spent = +s.spent || 0;
  const pct = total > 0 ? (spent / total) * 100 : 0;
  const fill = document.getElementById('bd-bar-fill');
  fill.style.width = Math.min(100, Math.max(0, pct)).toFixed(1) + '%';
  fill.classList.remove('warn','over');
  if(pct >= 100) fill.classList.add('over');
  else if(pct >= 80) fill.classList.add('warn');
  const text = document.getElementById('bd-bar-text');
  text.innerHTML = `<b>$${fmtMoney(spent)}</b> of <b>$${fmtMoney(total)}</b> spent · $${fmtMoney(s.remaining||0)} left`;
}

function fmtMoney(n){
  n = +n || 0;
  return n.toLocaleString('en-US', {maximumFractionDigits:0});
}

function renderBudgetCategories(){
  const root = document.getElementById('bd-categories');
  const itemsByCat = {};
  BUDGET_CATS.forEach(c => itemsByCat[c] = []);
  (BD_STATE.line_items||[]).forEach(it => {
    if(itemsByCat[it.category]) itemsByCat[it.category].push(it);
  });
  root.innerHTML = BUDGET_CATS.map(cat => {
    const items = itemsByCat[cat];
    const total = items.reduce((a,b) => a + (+b.cost||0), 0);
    const status = items.length
      ? `${items.length} item${items.length===1?'':'s'} · $${fmtMoney(total)}`
      : 'no items yet';
    const rows = items.map(it => budgetItemRow(it)).join('');
    return `<details class="bd-cat" ${items.length ? 'open' : ''}>
      <summary>
        <span>${cat}</span>
        <span class="cat-meta">${status}</span>
      </summary>
      <div class="cat-body">
        ${rows || '<div style="color:#888;font-size:12px;padding:6px 0">No items.</div>'}
        ${budgetAddForm(cat)}
      </div>
    </details>`;
  }).join('');
}

function budgetItemRow(it){
  const src = it.source === 'org_shortlist'
    ? `<span class="src">↳ from Org shortlist${it.source_ref ? ': '+escapeHtml(it.source_ref) : ''}</span>`
    : '';
  const statusOpts = ['Planned','Booked','Paid'].map(s => `<option value="${s}" ${it.status===s?'selected':''}>${s}</option>`).join('');
  return `<div class="bd-li-row">
    <div class="bd-li-name">${escapeHtml(it.name||'')}${src}</div>
    <div class="bd-li-cost">$<input type="number" min="0" step="50" value="${it.cost||0}" onchange="updateBudgetCost('${it.id}', this.value)"></div>
    <div class="bd-li-status"><select onchange="updateBudgetStatus('${it.id}', this.value)">${statusOpts}</select></div>
    <button class="bd-li-del" onclick="deleteBudgetItem('${it.id}')" title="Delete">×</button>
  </div>`;
}

function budgetAddForm(cat){
  return `<div class="bd-add-form">
    <input id="bd-add-name-${cat}" placeholder="Add line item (e.g. Catering deposit)">
    <input id="bd-add-cost-${cat}" type="number" placeholder="Cost" min="0" step="50">
    <button onclick="addBudgetItem('${cat}')">Add</button>
  </div>`;
}

async function saveBudgetTotal(){
  const v = parseFloat(document.getElementById('bd-total').value || '0') || 0;
  const status = document.getElementById('bd-total-status');
  status.textContent = 'saving…';
  await fetch('/budget/total', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({total_budget: v})});
  await loadBudget();
  status.textContent = 'saved';
  setTimeout(() => { if(status.textContent === 'saved') status.textContent = ''; }, 1500);
}

async function saveSponsorIncome(){
  const v = parseFloat(document.getElementById('bd-sponsor').value || '0') || 0;
  await fetch('/budget/sponsor_income', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sponsor_income: v})});
  await loadBudget();
}

async function addBudgetItem(cat){
  const name = (document.getElementById('bd-add-name-'+cat).value || '').trim();
  const cost = parseFloat(document.getElementById('bd-add-cost-'+cat).value || '0') || 0;
  if(!name){ alert('Give the line item a name first.'); return; }
  await fetch('/budget/line_item', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({category: cat, name, cost})});
  await loadBudget();
}

async function updateBudgetCost(id, v){
  const cost = parseFloat(v || '0') || 0;
  await fetch('/budget/line_item/'+encodeURIComponent(id), {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({cost})});
  await loadBudget();
}

async function updateBudgetStatus(id, status){
  await fetch('/budget/line_item/'+encodeURIComponent(id), {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({status})});
  await loadBudget();
}

async function deleteBudgetItem(id){
  if(!confirm('Delete this line item?')) return;
  await fetch('/budget/line_item/'+encodeURIComponent(id), {method:'DELETE'});
  await loadBudget();
}

// Best-effort numeric extraction from a free-form quote string ("$3,500/day", "$45-65/person").
function parseCostText(s){
  if(!s) return 0;
  const m = String(s).match(/\\$?\\s*([0-9][0-9,]*)/);
  if(!m) return 0;
  return parseInt(m[1].replace(/,/g,''), 10) || 0;
}

async function pushShortlistToBudget(){
  const vendors = [];
  ['venues','caterers'].forEach(cat => {
    const key = 'ei.org.saved.' + cat;
    let saved = [];
    try{ saved = JSON.parse(localStorage.getItem(key) || '[]'); }catch(_){}
    saved.forEach(it => {
      const targetCat = cat === 'venues' ? 'Venue' : 'Food';
      const quote = cat === 'venues' ? (it.rental_fee||'') : (it.price_per_head||'');
      vendors.push({
        category: targetCat,
        name: it.name || '(unnamed)',
        cost: parseCostText(quote),
        cost_text: quote,
        source_ref: it.name || '',
      });
    });
  });
  if(!vendors.length) return;
  try{
    await fetch('/budget/autofill_from_shortlist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({vendors})});
  }catch(_){}
}

// ---------- Attendees tab ----------
let ATT_STATE = {attendees:[], summary:{total:0,invited:0,confirmed:0,declined:0,attended:0}};
let ATT_POLL_TIMER = null;

function refreshAttendeesHeader(){
  const el = document.getElementById('att-header');
  if(!el) return;
  const s = ATT_STATE.summary;
  const date = fmtEventLine('Event:');
  el.innerHTML = `${date} · <b>${s.total||0}</b> invited · <b style="color:#0a7d2c">${s.confirmed||0}</b> confirmed · <b style="color:#888">${s.declined||0}</b> said no`;
}

async function loadAttendees(){
  try{
    const r = await fetch('/attendees');
    if(!r.ok) return;
    ATT_STATE = await r.json();
  }catch(_){return;}
  refreshAttendeesHeader();
  renderAttendees();
}

function renderAttendees(){
  const tbody = document.getElementById('att-rows');
  const list = ATT_STATE.attendees || [];
  if(!list.length){
    tbody.innerHTML = '<tr><td colspan="4" style="color:#888;padding:14px">No attendees yet — run the pipeline or add one above.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(a => {
    const opts = ['Invited','Confirmed','Declined','Attended']
      .map(s => `<option value="${s}" ${a.status===s?'selected':''}>${s}</option>`).join('');
    return `<tr data-id="${escapeHtml(a.id)}">
      <td><span class="att-dot att-dot-${escapeHtml(a.status||'Invited')}"></span><select class="att-status-${escapeHtml(a.status||'Invited')}" onchange="updateAttendeeStatus('${escapeHtml(a.id)}', this.value)">${opts}</select></td>
      <td>${escapeHtml(a.name||'')}</td>
      <td style="color:#666">${escapeHtml(a.company||'')}</td>
      <td><input class="att-notes" placeholder="add note…" value="${escapeHtml(a.notes||'')}" onchange="updateAttendeeNotes('${escapeHtml(a.id)}', this.value)"></td>
    </tr>`;
  }).join('');
}

async function addAttendee(){
  const name = (document.getElementById('att-name').value||'').trim();
  if(!name){ alert('Name is required.'); return; }
  const company = (document.getElementById('att-company').value||'').trim();
  const email = (document.getElementById('att-email').value||'').trim();
  const status = document.getElementById('att-add-status');
  status.textContent = 'adding…';
  try{
    const r = await fetch('/attendees', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, company, email})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'failed');
    document.getElementById('att-name').value = '';
    document.getElementById('att-company').value = '';
    document.getElementById('att-email').value = '';
    status.textContent = 'added';
    await loadAttendees();
    setTimeout(() => { if(status.textContent === 'added') status.textContent = ''; }, 1500);
  }catch(e){
    status.textContent = 'failed: ' + e.message;
  }
}

async function updateAttendeeStatus(id, status){
  await fetch('/attendees/'+encodeURIComponent(id), {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({status})});
  await loadAttendees();
}

async function updateAttendeeNotes(id, notes){
  await fetch('/attendees/'+encodeURIComponent(id), {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({notes})});
  // Don't reload — we don't want to disrupt the typing flow. Just save.
}

function startAttendeePoll(){
  stopAttendeePoll();
  ATT_POLL_TIMER = setInterval(loadAttendees, 10000);
}
function stopAttendeePoll(){
  if(ATT_POLL_TIMER){ clearInterval(ATT_POLL_TIMER); ATT_POLL_TIMER = null; }
}

// Hook into switchTab so Budget/Attendees data loads when their tab opens.
const _origSwitchTab = switchTab;
switchTab = function(name){
  _origSwitchTab(name);
  stopAttendeePoll();
  if(name === 'budget') loadBudget();
  if(name === 'attendees'){ loadAttendees(); startAttendeePoll(); }
};
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


@app.get("/event/summary")
async def event_summary():
    """Return the latest extracted event metadata.

    Used by the Organization tab to auto-fire venues/caterers/sponsors searches
    after an Eventful run completes. Returns only the fields needed
    for org search query construction.
    """
    import json as _json
    p = _REPO_ROOT / "data" / "event_state.json"
    if not p.exists():
        return {"ok": False, "reason": "no_event_state"}
    try:
        state = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return {"ok": False, "reason": "invalid_event_state"}
    ev = (state.get("event") or {})
    return {
        "ok": True,
        "name": ev.get("name") or "",
        "city": ev.get("city") or "",
        "target_size": ev.get("target_size") or 0,
        "format": ev.get("format") or "",
        "goal": ev.get("goal") or "",
    }


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
