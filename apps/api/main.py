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
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eventful</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#FFFFFF;--bg-alt:#FAFAFA;--bg-soft:#F5F5F5;
  --text:#0A0A0A;--text-2:#525252;--text-3:#A3A3A3;
  --border:#EAEAEA;
  --primary:#0A0A0A;--primary-hover:#262626;
  --r-sm:6px;--r:8px;--r-pill:9999px;
  --shadow:0 1px 3px rgba(0,0,0,0.04);
  --shadow-pop:0 4px 16px rgba(0,0,0,0.08);
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  --t:150ms ease;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font:400 14px/1.5 var(--font);font-variant-numeric:tabular-nums;color:var(--text);background:var(--bg)}
button,input,select,textarea{font-family:var(--font)}
.container{max-width:1200px;margin:0 auto;padding:0 32px}
h1,h2,h3{margin:0;font-weight:600}
.muted{color:var(--text-2)}
.dim{color:var(--text-3)}
hr{border:0;border-top:1px solid var(--border);margin:24px 0}

/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:8px 14px;font:500 13px var(--font);border-radius:var(--r-sm);cursor:pointer;transition:all var(--t);border:1px solid transparent;background:transparent;color:var(--text);text-decoration:none;white-space:nowrap}
.btn:disabled{cursor:not-allowed;opacity:.5}
.btn-primary{background:var(--primary);color:#fff;border-color:var(--primary)}
.btn-primary:hover:not(:disabled){background:var(--primary-hover);border-color:var(--primary-hover)}
.btn-secondary{background:var(--bg);color:var(--text);border-color:var(--text)}
.btn-secondary:hover:not(:disabled){background:var(--bg-alt)}
.btn-tertiary{padding:6px 8px;color:var(--text);font-weight:500}
.btn-tertiary:hover:not(:disabled){text-decoration:underline;text-underline-offset:2px}
.btn-icon{padding:6px;color:var(--text-2);border-radius:var(--r-sm)}
.btn-icon:hover{background:var(--bg-alt);color:var(--text)}
.btn-sm{padding:4px 10px;font-size:12px}

/* Inputs */
.input,textarea,select{font:inherit;padding:8px 12px;border:1px solid var(--border);border-radius:var(--r-sm);background:var(--bg);color:var(--text);transition:border-color var(--t);width:auto}
.input:focus,textarea:focus,select:focus{outline:0;border-color:var(--text)}
textarea{resize:vertical;min-height:90px}
.input-lg{padding:14px 16px;font-size:14px}
.input-sm{padding:4px 8px;font-size:12px}
input[type=number]{font-variant-numeric:tabular-nums}
input::placeholder,textarea::placeholder{color:var(--text-3)}

/* Page header */
.page-header{padding:40px 0 24px}
.event-name{display:inline-block;font-size:32px;line-height:1.15;letter-spacing:-0.02em;cursor:text;padding:2px 6px;margin:-2px -6px;border-radius:var(--r-sm);transition:background var(--t);min-width:60px;outline:0}
.event-name:hover{background:var(--bg-alt)}
.event-name:focus{background:var(--bg-alt)}
.event-name[data-empty="true"]{color:var(--text-3)}
.event-meta{margin-top:10px;font-size:14px;color:var(--text-2);display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.event-meta .sep{color:var(--text-3)}
.event-meta .meta-link{color:var(--text-2);cursor:pointer;padding:2px 6px;margin:-2px -6px;border-radius:var(--r-sm);transition:background var(--t)}
.event-meta .meta-link:hover{background:var(--bg-alt);color:var(--text)}
.event-meta .meta-link[data-empty="true"]{color:var(--text-3)}
.event-meta .meta-link[data-empty="true"]:hover{color:var(--text)}

/* Stat tiles */
.stat-tiles{margin-top:24px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.stat-tile{padding:16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--r);transition:border-color var(--t)}
.stat-tile .stat-num{font-size:28px;font-weight:600;line-height:1.1;letter-spacing:-0.01em;font-variant-numeric:tabular-nums}
.stat-tile .stat-num .stat-of{font-size:14px;color:var(--text-2);font-weight:500;margin-left:4px}
.stat-tile .stat-label{margin-top:4px;font-size:12px;color:var(--text-2)}

/* Prompt section */
.prompt-section{margin:24px 0 32px;padding:20px;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--r)}
.prompt-section textarea{width:100%;height:90px;background:var(--bg)}
.prompt-section .prompt-actions{margin-top:12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}

/* Sticky header */
.sticky-bar{position:sticky;top:0;z-index:30;background:rgba(255,255,255,0.94);backdrop-filter:saturate(160%) blur(8px);-webkit-backdrop-filter:saturate(160%) blur(8px);border-bottom:1px solid transparent;transition:border-color var(--t),background var(--t)}
.sticky-bar.scrolled{border-bottom-color:var(--border)}
.sticky-inner{display:flex;align-items:center;gap:32px;height:48px}
.sticky-event{font-size:13px;font-weight:500;color:var(--text);white-space:nowrap;opacity:0;transition:opacity var(--t);overflow:hidden;text-overflow:ellipsis;max-width:340px}
.sticky-bar.scrolled .sticky-event{opacity:1}

/* Tabs */
.tabs{display:flex;gap:24px;border-bottom:0}
.tab{padding:14px 0;border:0;background:none;font:500 14px var(--font);color:var(--text-2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:all var(--t)}
.tab:hover{color:var(--text)}
.tab.active{color:var(--text);border-bottom-color:var(--text)}

/* Tab panels */
.tab-panel{display:none;padding:32px 0 80px;animation:fadeIn var(--t)}
.tab-panel.active{display:block}

/* Cards */
.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--r);padding:16px;transition:border-color var(--t)}

/* Tables */
table.list{width:100%;border-collapse:collapse}
table.list th{font:500 11px var(--font);text-transform:uppercase;letter-spacing:0.05em;color:var(--text-2);text-align:left;padding:10px 12px 8px;border-bottom:1px solid var(--border)}
table.list td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle}
table.list tr{transition:background var(--t)}
table.list tbody tr:hover{background:var(--bg-alt)}
table.list tbody tr:last-child td{border-bottom:0}
table.list .row-actions{opacity:0;transition:opacity var(--t);text-align:right;white-space:nowrap}
table.list tr:hover .row-actions{opacity:1}

/* Avatar */
.avatar{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--bg-soft);color:var(--text);font:600 11px var(--font);flex-shrink:0;letter-spacing:0}
.avatar-sm{width:24px;height:24px;font-size:10px}
.cell-name{display:flex;align-items:center;gap:10px}
.cell-name .name-main{font-weight:500;color:var(--text)}
.cell-name .name-sub{font-size:12px;color:var(--text-2)}

/* Status chip */
.chip{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;font:500 11px var(--font);border:1px solid var(--border);color:var(--text);border-radius:var(--r-pill);background:var(--bg);white-space:nowrap}
.chip-strong{background:var(--text);color:var(--bg);border-color:var(--text)}
.chip-weak{color:var(--text-2)}

/* Filter chips */
.filter-chips{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.filter-chip{padding:5px 14px;font:500 12px var(--font);border:1px solid var(--border);color:var(--text-2);background:var(--bg);border-radius:var(--r-pill);cursor:pointer;transition:all var(--t)}
.filter-chip:hover{color:var(--text);border-color:var(--text-3)}
.filter-chip.active{background:var(--text);color:var(--bg);border-color:var(--text)}

/* Empty state */
.empty{text-align:center;padding:64px 32px;color:var(--text-2)}
.empty svg{width:40px;height:40px;color:var(--text-3);margin-bottom:16px;stroke-width:1.5}
.empty .empty-line{font-size:14px;margin-bottom:16px}

/* Banner */
.banner{padding:10px 14px;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--r);font-size:13px;color:var(--text-2);margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.banner-error{background:var(--bg);border-color:var(--text);color:var(--text)}

/* Popover */
.popover{position:absolute;z-index:40;background:var(--bg);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--shadow-pop);padding:16px;min-width:280px;display:none}
.popover.show{display:block;animation:fadeIn var(--t)}
.popover label{display:block;font-size:11px;color:var(--text-2);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;margin-top:10px}
.popover label:first-child{margin-top:0}
.popover .input{width:100%}
.popover .pop-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}

/* Modal */
.modal-bg{position:fixed;inset:0;background:rgba(10,10,10,0.5);display:none;align-items:flex-start;justify-content:center;z-index:50;padding:64px 16px;overflow:auto}
.modal-bg.show{display:flex;animation:fadeIn var(--t)}
.modal{background:var(--bg);border-radius:var(--r);max-width:720px;width:100%;padding:24px;position:relative;box-shadow:var(--shadow-pop)}
.modal h2{font-size:20px;font-weight:600;margin-bottom:6px}
.modal .modal-sub{font-size:13px;color:var(--text-2);margin-bottom:16px}
.modal .close{position:absolute;top:14px;right:14px;padding:6px 10px;background:none;border:0;font-size:16px;cursor:pointer;color:var(--text-2);border-radius:var(--r-sm);transition:background var(--t);line-height:1}
.modal .close:hover{background:var(--bg-alt);color:var(--text)}
.modal .field{margin-bottom:16px}
.modal .field-row{display:flex;gap:12px;align-items:center;margin-bottom:8px}
.modal label{font-size:11px;color:var(--text-2);text-transform:uppercase;letter-spacing:0.05em;display:block;margin-bottom:6px}
.modal .placeholders{font-size:12px;color:var(--text-3);margin-top:6px}
.modal .placeholders code{background:var(--bg-soft);padding:1px 6px;border-radius:4px;color:var(--text-2);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
.modal .preview-list{max-height:280px;overflow:auto;border:1px solid var(--border);border-radius:var(--r-sm);background:var(--bg-alt)}
.modal .preview-row{padding:10px 14px;border-bottom:1px solid var(--border)}
.modal .preview-row:last-child{border-bottom:0}
.modal .preview-row .pname{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px}
.modal .preview-row .pmsg{font-size:12px;color:var(--text-2);white-space:pre-wrap}
.modal .channel{font-size:11px;color:var(--text-3)}
.modal .slider-row{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.modal .slider-row input[type=range]{flex:1}
.modal .action-row{display:flex;gap:8px;align-items:center;margin-top:18px;justify-content:flex-end}

/* EI tab */
.ei-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.ei-summary-text{font-size:13px;color:var(--text-2)}
.ei-summary-text b{color:var(--text);font-weight:600}
.ei-actions{display:flex;gap:8px;flex-wrap:wrap}
.ei-fit{font-weight:500;font-variant-numeric:tabular-nums}
.ei-priority{display:inline-flex;padding:2px 8px;font-size:11px;font-weight:500;border:1px solid var(--border);border-radius:var(--r-pill);color:var(--text)}
.ei-priority[data-pri="high"]{background:var(--text);color:var(--bg);border-color:var(--text)}
.ei-priority[data-pri="needs_review"]{font-style:italic;color:var(--text-2)}
.contact-icons{display:inline-flex;align-items:center;gap:4px;color:var(--text-3)}
.contact-icons a,.contact-icons span{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:var(--r-sm);text-decoration:none;color:inherit;transition:all var(--t)}
.contact-icons a{color:var(--text)}
.contact-icons a:hover{background:var(--bg-alt)}
.contact-icons svg{width:14px;height:14px;stroke-width:1.8}

/* Org tab */
.org-pills{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.org-pill{padding:5px 14px;font:500 13px var(--font);border:1px solid var(--border);color:var(--text-2);background:var(--bg);border-radius:var(--r-pill);cursor:pointer;transition:all var(--t)}
.org-pill:hover{color:var(--text);border-color:var(--text-3)}
.org-pill.active{background:var(--text);color:var(--bg);border-color:var(--text)}
.org-form{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:16px;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--r);margin-bottom:16px}
.org-form .field-col{display:flex;flex-direction:column;gap:4px}
.org-form .field-col label{font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-2)}
.org-form .field-col input,.org-form .field-col select{padding:6px 10px;font-size:13px}
.org-form .form-actions{grid-column:1 / -1;display:flex;justify-content:space-between;align-items:center;margin-top:4px}
.org-form .form-actions .muted{font-size:12px}
.org-status-row{display:flex;justify-content:space-between;align-items:center;margin:16px 0;font-size:12px;color:var(--text-2)}
.org-cards{display:grid;grid-template-columns:1fr;gap:12px}
.org-card{background:var(--bg);border:1px solid var(--border);border-radius:var(--r);padding:16px;transition:border-color var(--t)}
.org-card:hover{border-color:var(--text-3)}
.org-card .head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.org-card .org-card-name{font-weight:600;font-size:15px;display:flex;align-items:center;gap:8px}
.org-card .org-meta{font-size:13px;color:var(--text-2);margin-top:4px}
.org-card .right{text-align:right;flex-shrink:0;display:flex;align-items:flex-start;gap:8px}
.org-card .right-stack{text-align:right}
.org-card .org-cost{font-size:14px;font-weight:500}
.org-card .org-rating{font-size:12px;color:var(--text-2);margin-top:2px}
.org-card .desc{font-size:13px;color:var(--text-2);margin-top:10px;line-height:1.55}
.org-card details{margin-top:10px;font-size:12px;color:var(--text-2)}
.org-card details summary{cursor:pointer;user-select:none;color:var(--text-2)}
.org-card details summary:hover{color:var(--text)}
.org-card details > div{margin-top:8px}
.org-card details ul{margin:6px 0 0 18px;padding:0}
.org-card .actions{display:flex;gap:8px;margin-top:14px;align-items:center;flex-wrap:wrap}
.org-card .save-btn{background:none;border:0;padding:6px;cursor:pointer;color:var(--text-3);border-radius:var(--r-sm);transition:all var(--t);display:inline-flex;align-items:center;justify-content:center}
.org-card .save-btn:hover{color:var(--text);background:var(--bg-alt)}
.org-card .save-btn.saved{color:var(--text)}
.amenity{display:inline-block;padding:2px 8px;font-size:11px;color:var(--text-2);background:var(--bg-soft);border-radius:var(--r-pill);margin:2px 4px 0 0}

/* Budget tab */
.bd-summary{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:12px;flex-wrap:wrap}
.bd-total-row{display:flex;align-items:center;gap:8px}
.bd-total-row .input{width:140px}
.bd-bar{height:6px;width:100%;background:var(--bg-soft);border-radius:var(--r-pill);overflow:visible;position:relative}
.bd-bar-fill{height:100%;background:var(--text);transition:width var(--t);width:0%;border-radius:var(--r-pill);max-width:100%}
.bd-bar-text{display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:13px;color:var(--text-2)}
.bd-bar-text b{color:var(--text);font-weight:600}
.bd-over-label{font-weight:600;color:var(--text)}
.bd-cat{background:var(--bg);border:1px solid var(--border);border-radius:var(--r);margin-bottom:10px;transition:border-color var(--t);overflow:hidden}
.bd-cat:hover{border-color:var(--text-3)}
.bd-cat[open]{border-color:var(--text-3)}
.bd-cat summary{list-style:none;padding:14px 16px;cursor:pointer;display:grid;grid-template-columns:1fr 200px 130px;gap:16px;align-items:center}
.bd-cat summary::-webkit-details-marker{display:none}
.bd-cat .cat-name{font-weight:500;font-size:15px}
.bd-cat .cat-bar{height:4px;background:var(--bg-soft);border-radius:var(--r-pill);overflow:hidden}
.bd-cat .cat-bar-fill{height:100%;background:var(--text);border-radius:var(--r-pill);transition:width var(--t)}
.bd-cat .cat-amount{text-align:right;font-weight:500}
.bd-cat .cat-amount .cat-count{color:var(--text-2);font-weight:400;font-size:12px;display:block}
.bd-cat .cat-body{padding:0 16px 16px;border-top:1px solid var(--border)}
.bd-li-row{display:grid;grid-template-columns:1fr 110px 110px 32px;gap:12px;padding:10px 0;border-bottom:1px solid var(--border);align-items:center;font-size:13px}
.bd-li-row:last-child{border-bottom:0}
.bd-li-name{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.bd-li-name .src-tag{font-size:11px;color:var(--text-2);border:1px solid var(--border);padding:1px 8px;border-radius:var(--r-pill);font-weight:400}
.bd-li-cost-input{width:100%}
.bd-li-status select{width:100%}
.bd-li-del{background:none;border:0;color:var(--text-3);cursor:pointer;padding:6px;border-radius:var(--r-sm);font-size:14px;transition:all var(--t);line-height:1}
.bd-li-del:hover{background:var(--bg-alt);color:var(--text)}
.bd-add-trigger{padding:8px 0;cursor:pointer;color:var(--text-2);font-size:13px;font-weight:500;transition:color var(--t);border:0;background:none;display:block;margin-top:8px}
.bd-add-trigger:hover{color:var(--text);text-decoration:underline;text-underline-offset:2px}
.bd-add-form{display:grid;grid-template-columns:1fr 110px 80px 60px;gap:8px;margin-top:10px;padding-top:10px;border-top:1px dashed var(--border)}
.bd-add-form input{padding:6px 10px;font-size:13px}
.bd-add-form.hidden{display:none}
.bd-sponsor{display:flex;align-items:center;gap:12px;padding:14px 16px;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--r);margin-top:24px;flex-wrap:wrap}
.bd-sponsor .sponsor-input{display:flex;align-items:center;gap:6px}
.bd-sponsor .sponsor-input .input{width:120px}

/* Attendees tab */
.att-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;flex-wrap:wrap}
.att-summary-text{font-size:14px;color:var(--text-2)}
.att-summary-text b{color:var(--text);font-weight:600}
.att-add-form{display:grid;grid-template-columns:1fr 1fr 1fr 80px 80px;gap:8px;padding:14px;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--r);margin-bottom:16px}
.att-add-form input{padding:7px 10px;font-size:13px}
.att-add-form.hidden{display:none}
.att-status-cell{display:flex;align-items:center;gap:8px}
.att-notes-input{width:100%;padding:5px 8px;font-size:12px;border:1px solid transparent;background:transparent;border-radius:var(--r-sm);transition:all var(--t)}
.att-notes-input:focus,.att-notes-input:hover{background:var(--bg);border-color:var(--border)}
.att-status-icon{width:14px;height:14px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;color:var(--text-2)}
.att-status-icon[data-status="Confirmed"]{color:var(--text)}
.att-status-icon[data-status="Attended"]{color:var(--text)}
.att-status-icon[data-status="Declined"]{color:var(--text-3)}
.att-status-icon[data-status="Invited"]{color:var(--text-3)}
.att-row{animation:fadeIn var(--t)}

/* Animations */
@keyframes fadeIn{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:translateY(0)}}

/* Misc */
.spinner{display:inline-block;width:12px;height:12px;border:1.5px solid var(--border);border-top-color:var(--text);border-radius:50%;animation:spin 600ms linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
.kbd-hint{font-size:11px;color:var(--text-3);margin-left:4px}
</style>
</head><body>

<div class="container">

<header class="page-header" id="page-header">
  <h1 class="event-name" id="event-name" data-empty="true" contenteditable="false" spellcheck="false">Untitled event</h1>
  <div class="event-meta" id="event-meta">
    <span class="meta-link" id="meta-date" data-empty="true" onclick="openDatePopover(event)">Set event date</span>
    <span class="sep">·</span>
    <span class="meta-link" id="meta-city" data-empty="true" onclick="openInfoPopover('city',event)">Add location</span>
    <span class="sep">·</span>
    <span class="meta-link" id="meta-format" data-empty="true" onclick="openInfoPopover('format',event)">Add format</span>
    <span class="sep">·</span>
    <span class="meta-link" id="meta-size" data-empty="true" onclick="openInfoPopover('target_size',event)">— people</span>
  </div>
  <div class="stat-tiles">
    <div class="stat-tile">
      <div class="stat-num" id="stat-days">—</div>
      <div class="stat-label" id="stat-days-label">days away</div>
    </div>
    <div class="stat-tile">
      <div class="stat-num"><span id="stat-confirmed">—</span><span class="stat-of" id="stat-confirmed-of"></span></div>
      <div class="stat-label">confirmed</div>
    </div>
    <div class="stat-tile">
      <div class="stat-num"><span id="stat-spent">—</span><span class="stat-of" id="stat-spent-of"></span></div>
      <div class="stat-label">spent</div>
    </div>
    <div class="stat-tile">
      <div class="stat-num"><span id="stat-vendors">—</span><span class="stat-of">/3</span></div>
      <div class="stat-label">vendors booked</div>
    </div>
  </div>
</header>

<section class="prompt-section">
  <textarea id="brief" placeholder="100-person crypto hackathon for builders, founders, ZK researchers in SF…"></textarea>
  <div class="prompt-actions">
    <button id="go" class="btn btn-primary">Run pipeline</button>
    <span id="status" class="muted"></span>
  </div>
  <div id="warn"></div>
</section>

</div>

<div class="sticky-bar" id="sticky-bar">
  <div class="container sticky-inner">
    <span class="sticky-event" id="sticky-event"></span>
    <nav class="tabs">
      <button class="tab active" data-tab="ei" onclick="switchTab('ei')">Event Intelligence</button>
      <button class="tab" data-tab="org" onclick="switchTab('org')">Organization</button>
      <button class="tab" data-tab="budget" onclick="switchTab('budget')">Budget</button>
      <button class="tab" data-tab="attendees" onclick="switchTab('attendees')">Attendees</button>
    </nav>
  </div>
</div>

<div class="container">

<main>

<!-- TAB: Event Intelligence -->
<section class="tab-panel active" id="panel-ei">
  <div id="result"></div>
</section>

<!-- TAB: Organization -->
<section class="tab-panel" id="panel-org">
  <div class="org-pills">
    <button class="org-pill active" data-cat="venues" onclick="switchCat('venues')">Venues</button>
    <button class="org-pill" data-cat="caterers" onclick="switchCat('caterers')">Caterers</button>
    <button class="org-pill" data-cat="sponsors" onclick="switchCat('sponsors')">Sponsors</button>
  </div>

  <div class="org-form" id="form-venues">
    <div class="field-col"><label>Location</label><input id="v-location" placeholder="San Francisco, SoMa"></div>
    <div class="field-col"><label>Capacity</label><input id="v-capacity" type="number" placeholder="100" min="1"></div>
    <div class="field-col"><label>Date / availability</label><input id="v-availability" placeholder="Sat May 17, evening"></div>
    <div class="field-col"><label>Amenities</label><input id="v-amenities" placeholder="AV, wifi, kitchen"></div>
    <div class="field-col"><label>Budget</label><input id="v-budget" placeholder="up to $5k"></div>
    <div class="field-col"><label>Sort by</label>
      <select id="v-sort"><option value="relevance">relevance</option><option value="cost">cost (low → high)</option><option value="rating">rating</option></select>
    </div>
    <div class="form-actions">
      <span class="muted">~30s · ~$0.30 first time, free if cached</span>
      <button class="btn btn-primary" onclick="orgSearch('venues')">Search venues</button>
    </div>
  </div>

  <div class="org-form" id="form-caterers" style="display:none">
    <div class="field-col"><label>Location</label><input id="c-location" placeholder="San Francisco"></div>
    <div class="field-col"><label>Cuisine</label><input id="c-cuisine" placeholder="Mediterranean / Pan-Asian"></div>
    <div class="field-col"><label>Headcount</label><input id="c-headcount" type="number" placeholder="100"></div>
    <div class="field-col"><label>Dietary needs</label><input id="c-dietary" placeholder="vegan, gluten-free"></div>
    <div class="field-col"><label>Budget per head</label><input id="c-budget" placeholder="$30-50pp"></div>
    <div class="field-col"><label>Sort by</label>
      <select id="c-sort"><option value="relevance">relevance</option><option value="cost">cost (low → high)</option><option value="rating">rating</option></select>
    </div>
    <div class="form-actions">
      <span class="muted">~30s · ~$0.30 first time, free if cached</span>
      <button class="btn btn-primary" onclick="orgSearch('caterers')">Search caterers</button>
    </div>
  </div>

  <div class="org-form" id="form-sponsors" style="display:none">
    <div class="field-col"><label>Industry / theme</label><input id="s-industry" placeholder="crypto / dev tools / AI infra"></div>
    <div class="field-col"><label>Company size</label><input id="s-size" placeholder="Series B+, 200+ emp"></div>
    <div class="field-col"><label>Sponsorship budget</label><input id="s-budget" placeholder="$10-50k tier"></div>
    <div class="field-col"><label>Notes</label><input id="s-notes" placeholder="hackathons, demo nights"></div>
    <div class="field-col"></div>
    <div class="field-col"><label>Sort by</label>
      <select id="s-sort"><option value="relevance">relevance</option><option value="cost">budget (low → high)</option><option value="rating">rating</option></select>
    </div>
    <div class="form-actions">
      <span class="muted">~30s · ~$0.30 first time, free if cached</span>
      <button class="btn btn-primary" onclick="orgSearch('sponsors')">Search sponsors</button>
    </div>
  </div>

  <div id="org-banner" class="banner" style="display:none">
    <span><b>Auto-sourced from your prompt.</b> <span class="muted" id="org-banner-meta"></span></span>
    <button class="btn btn-secondary btn-sm" onclick="retryCategory(ORG_CAT)">Re-run this category</button>
  </div>

  <div class="org-status-row">
    <span id="org-status"></span>
    <button class="btn btn-tertiary btn-sm" onclick="toggleSaved()" id="btn-show-saved">Show saved</button>
  </div>

  <div class="org-cards" id="org-results"></div>
</section>

<!-- TAB: Budget -->
<section class="tab-panel" id="panel-budget">
  <div class="bd-summary">
    <div class="bd-total-row">
      <span class="muted">Total budget</span>
      <span class="muted">$</span>
      <input id="bd-total" type="number" min="0" step="100" class="input" placeholder="10,000">
      <button class="btn btn-tertiary btn-sm" onclick="saveBudgetTotal()">Save</button>
      <span id="bd-total-status" class="dim" style="font-size:12px"></span>
    </div>
  </div>
  <div class="bd-bar"><div class="bd-bar-fill" id="bd-bar-fill"></div></div>
  <div class="bd-bar-text" id="bd-bar-text"></div>

  <div id="bd-categories" style="margin-top:24px"></div>

  <div class="bd-sponsor">
    <span class="muted">Sponsor contributions</span>
    <div class="sponsor-input">
      <span class="muted">$</span>
      <input id="bd-sponsor" type="number" min="0" step="100" class="input" placeholder="0">
      <button class="btn btn-tertiary btn-sm" onclick="saveSponsorIncome()">Save</button>
    </div>
    <span class="dim" style="font-size:12px;flex:1;min-width:160px">Subtracts from total spent.</span>
  </div>
</section>

<!-- TAB: Attendees -->
<section class="tab-panel" id="panel-attendees">
  <div class="att-summary">
    <div class="att-summary-text" id="att-summary-text">No attendees yet.</div>
    <button class="btn btn-primary" id="att-add-toggle" onclick="toggleAddAttendee()">+ Add attendee</button>
  </div>
  <div class="filter-chips" id="att-filter-chips">
    <button class="filter-chip active" data-filter="all" onclick="setAttendeeFilter('all')">All</button>
    <button class="filter-chip" data-filter="Invited" onclick="setAttendeeFilter('Invited')">Invited</button>
    <button class="filter-chip" data-filter="Confirmed" onclick="setAttendeeFilter('Confirmed')">Confirmed</button>
    <button class="filter-chip" data-filter="Declined" onclick="setAttendeeFilter('Declined')">Declined</button>
    <button class="filter-chip" data-filter="Attended" onclick="setAttendeeFilter('Attended')">Attended</button>
  </div>
  <div class="att-add-form hidden" id="att-add-form">
    <input id="att-name" placeholder="Name">
    <input id="att-company" placeholder="Company">
    <input id="att-email" placeholder="Email (optional)">
    <button class="btn btn-primary btn-sm" onclick="addAttendee()">Add</button>
    <button class="btn btn-tertiary btn-sm" onclick="toggleAddAttendee()">Cancel</button>
  </div>
  <div id="att-list-wrap"></div>
</section>

</main>

</div>

<!-- Date popover -->
<div class="popover" id="date-popover">
  <label>Event date</label>
  <input id="ev-date" type="date" class="input">
  <label>Start time</label>
  <input id="ev-start" type="time" class="input">
  <label>End time (optional)</label>
  <input id="ev-end" type="time" class="input">
  <div class="pop-actions">
    <button class="btn btn-tertiary" onclick="closeDatePopover()">Cancel</button>
    <button class="btn btn-primary" onclick="saveDatePopover()">Save</button>
  </div>
</div>

<!-- Info popover (city / format) -->
<div class="popover" id="info-popover">
  <label id="info-popover-label">Location</label>
  <input id="info-popover-input" class="input" type="text">
  <div class="pop-actions">
    <button class="btn btn-tertiary" onclick="closeInfoPopover()">Cancel</button>
    <button class="btn btn-primary" onclick="saveInfoPopover()">Save</button>
  </div>
</div>

<!-- Outreach modal -->
<div class="modal-bg" id="msg-modal" onclick="if(event.target===this)closeMsg()">
  <div class="modal">
    <button class="close" onclick="closeMsg()">×</button>
    <h2>Message <span id="msg-focus-name"></span></h2>
    <div class="modal-sub" id="msg-focus-meta"></div>
    <div class="modal-sub">Contact: <span id="msg-focus-contact"></span></div>

    <div class="field">
      <label>Subject</label>
      <input id="msg-subject" type="text" value="Invitation" class="input" style="width:100%" oninput="rerenderPreview()">
    </div>

    <div class="field">
      <label>Template</label>
      <textarea id="msg-template" oninput="rerenderPreview()"></textarea>
      <div class="placeholders">Placeholders: <code>{first_name}</code> <code>{name}</code> <code>{company}</code> <code>{role}</code> <code>{persona}</code> <code>{event}</code> <code>{event_date}</code> <code>{city}</code> <code>{confirm_link}</code></div>
    </div>

    <div class="field">
      <label>Apply to others — pick how many recipients</label>
      <div class="slider-row">
        <input type="range" id="msg-slider" min="1" max="1" value="1" oninput="document.getElementById('msg-slider-val').textContent=this.value;rerenderPreview()">
        <span><b id="msg-slider-val">1</b> recipients</span>
      </div>
      <div class="dim" style="font-size:12px">Includes the focus person + the next N-1 by fit_score order.</div>
    </div>

    <div class="field">
      <label>Preview</label>
      <div class="preview-list" id="msg-preview-list"></div>
    </div>

    <div class="action-row">
      <button class="btn btn-tertiary" onclick="closeMsg()">Cancel</button>
      <button class="btn btn-primary" onclick="openAllMail()">Open drafts in mail client</button>
    </div>
    <div class="dim" style="font-size:12px;margin-top:10px;text-align:right">
      Drafts open in your default mail app pre-filled. Nothing is sent automatically — you click Send yourself in each one.
    </div>
  </div>
</div>

<script>
// ---------- helpers ----------
function escapeHtml(s){return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmtMoney(n){ n = +n||0; return n.toLocaleString('en-US',{maximumFractionDigits:0}); }
function fmtDateHuman(iso){
  if(!iso) return '';
  const d = new Date(iso.length === 10 ? iso + 'T00:00' : iso);
  if(isNaN(+d)) return iso;
  return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
}
function initials(name){
  if(!name) return '–';
  const parts = String(name).trim().split(/\s+/);
  if(parts.length >= 2) return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
  return parts[0].slice(0,2).toUpperCase();
}
function avatar(name, cls){
  return `<span class="avatar ${cls||''}">${escapeHtml(initials(name))}</span>`;
}

// ---------- State ----------
let EVENT_META = {event_date:'',event_end_time:null,days_until:null,name:'',city:'',format:'',is_past:false};
let EVENT_SUMMARY_DATA = null;
let ALL_PEOPLE = [], EVENT_SUMMARY = {}, MSG_FOCUS_NAME = '';
let TARGET_SIZE = 0;
let BD_STATE = {summary:{total_budget:0,spent:0,remaining:0,sponsor_income:0},line_items:[]};
let ATT_STATE = {attendees:[],summary:{total:0,invited:0,confirmed:0,declined:0,attended:0}};
let ATT_FILTER = 'all';
let ATT_POLL_TIMER = null;

const DEFAULT_TEMPLATE = "Hi {first_name},\\n\\nI'm putting together {event} on {event_date} and would love for you to come — hand-picking other {persona}s building at companies like {company}.\\n\\nConfirm here: {confirm_link}\\n\\nThanks!";

// ---------- Health banner ----------
fetch('/health').then(r=>r.json()).then(h=>{
  if(!h.anthropic_key_set){
    document.getElementById('warn').innerHTML =
      '<div class="banner banner-error" style="margin-top:14px">ANTHROPIC_API_KEY is not set. The curator will skip and you\\'ll get 0 prospects. Add it to <code style="background:var(--bg-soft);padding:1px 5px;border-radius:3px">.env</code> and restart.</div>';
  }
});

// ---------- Run pipeline ----------
const btn = document.getElementById('go'), statusEl = document.getElementById('status');
btn.onclick = async () => {
  const brief = document.getElementById('brief').value.trim();
  if(!brief){ alert('Paste a brief first'); return; }
  btn.disabled = true;
  document.getElementById('result').innerHTML = '';
  const t0 = Date.now();
  const tick = setInterval(() => {
    const s = Math.floor((Date.now()-t0)/1000);
    const m = Math.floor(s/60), r = s%60;
    statusEl.innerHTML = `<span class="spinner"></span>running… ${m>0?m+'m ':''}${r}s`;
  }, 250);
  try{
    const r = await fetch('/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brief_text:brief})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'pipeline failed');
    clearInterval(tick);
    statusEl.textContent = `done in ${((Date.now()-t0)/1000).toFixed(1)}s`;
    const peopleResp = await fetch('/people');
    const people = (await peopleResp.json()).people || [];
    renderResult(data, people);
    loadEventMeta();
    refreshAllStats();
    autoFireOrgSearches();
  }catch(e){
    clearInterval(tick);
    statusEl.textContent = '';
    document.getElementById('result').innerHTML = `<div class="banner banner-error">${escapeHtml(e.message)}</div>`;
  }finally{ btn.disabled = false; }
};

function renderResult(s, people){
  const top = people.slice(0,30);
  ALL_PEOPLE = people; EVENT_SUMMARY = s;
  const root = document.getElementById('result');
  if(!people.length){
    root.innerHTML = emptyState('No prospects yet', 'Run a brief above to source attendees, or add people manually in the Attendees tab.', 'people');
    return;
  }
  let html = `<div class="ei-summary">
    <div class="ei-summary-text">Sourced <b>${s.ranked_count||people.length}</b> prospects · <b>${s.high_priority_count||0}</b> high-priority${s.top_gap_persona ? ' · top gap: <b>'+escapeHtml(s.top_gap_persona)+'</b>' : ''}</div>
    <div class="ei-actions">
      <a class="btn btn-secondary btn-sm" href="/download/ranked_people.csv" download>Download CSV</a>
      <a class="btn btn-tertiary btn-sm" href="/download/event_state.json" download>event_state.json</a>
      <button class="btn btn-secondary btn-sm" id="btn-discover">Discover contacts</button>
      <span id="discover-status" class="dim" style="font-size:12px"></span>
    </div>
  </div>`;
  html += `<table class="list">
    <thead><tr><th style="width:32px"></th><th>Name</th><th>Persona</th><th>Fit</th><th>Priority</th><th>Contact</th><th></th></tr></thead><tbody>`;
  top.forEach(p => {
    const pri = (p.priority||'').replace(/[^a-z_]/gi,'');
    html += `<tr>
      <td>${avatar(p.name)}</td>
      <td><div class="cell-name"><div><div class="name-main">${escapeHtml(p.name||'')}</div><div class="name-sub">${escapeHtml(p.role||'')}${p.role && p.company ? ' · ' : ''}${escapeHtml(p.company||'')}</div></div></div></td>
      <td class="muted">${escapeHtml(p.persona||'')}</td>
      <td class="ei-fit">${escapeHtml(p.fit_score||'')}</td>
      <td>${pri ? `<span class="ei-priority" data-pri="${pri}">${escapeHtml(p.priority)}</span>` : ''}</td>
      <td>${contactIcons(p)}</td>
      <td class="row-actions"><button class="btn btn-secondary btn-sm" onclick="openMsg('${escapeHtml(p.name||'').replace(/'/g, "&#39;")}')">Message</button></td>
    </tr>`;
  });
  html += '</tbody></table>';
  if(people.length > 30) html += `<div class="dim" style="font-size:12px;margin-top:10px">${people.length - 30} more in ranked_people.csv</div>`;
  root.innerHTML = html;
  document.getElementById('btn-discover').onclick = discoverContacts;
}

function contactIcons(p){
  const SVG_MAIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>';
  const SVG_LINK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 11v5"/><path d="M8 8v.01"/><path d="M12 16v-5"/><path d="M16 16v-3a2 2 0 1 0-4 0"/></svg>';
  const SVG_X = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16"/><path d="M4 20L20 4"/></svg>';
  const items = [];
  if(p.email) items.push(`<a href="mailto:${escapeHtml(p.email)}" title="${escapeHtml(p.email)}">${SVG_MAIL}</a>`);
  else items.push(`<span title="no email">${SVG_MAIL}</span>`);
  if(p.linkedin_url) items.push(`<a href="${escapeHtml(p.linkedin_url)}" target="_blank" title="LinkedIn">${SVG_LINK}</a>`);
  else items.push(`<span title="no LinkedIn">${SVG_LINK}</span>`);
  if(p.twitter) items.push(`<a href="https://x.com/${encodeURIComponent(String(p.twitter).replace(/^@/,''))}" target="_blank" title="X">${SVG_X}</a>`);
  else items.push(`<span title="no X">${SVG_X}</span>`);
  return `<span class="contact-icons">${items.join('')}</span>`;
}

async function discoverContacts(){
  const dbtn = document.getElementById('btn-discover');
  const dst = document.getElementById('discover-status');
  if(dbtn) dbtn.disabled = true;
  if(dst) dst.innerHTML = '<span class="spinner"></span>searching the web…';
  try{
    const r = await fetch('/contacts/discover',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({only_missing:true})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail||'discovery failed');
    if(dst) dst.textContent = `enriched ${data.enriched} of ${data.considered}`;
    const peopleResp = await fetch('/people');
    const people = (await peopleResp.json()).people || [];
    renderResult(EVENT_SUMMARY, people);
  }catch(e){
    if(dst) dst.textContent = 'failed: ' + e.message;
  }finally{ if(dbtn) dbtn.disabled = false; }
}

function emptyState(title, line, icon){
  const ICONS = {
    people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>',
    budget: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9 14h4.5a2 2 0 0 0 0-4h-3a2 2 0 0 1 0-4H15"/></svg>',
    list: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r=".5" fill="currentColor"/><circle cx="3.5" cy="12" r=".5" fill="currentColor"/><circle cx="3.5" cy="18" r=".5" fill="currentColor"/></svg>',
  };
  return `<div class="empty">${ICONS[icon]||ICONS.list}<div style="font-weight:500;font-size:15px;color:var(--text);margin-bottom:6px">${escapeHtml(title)}</div><div class="empty-line">${escapeHtml(line)}</div></div>`;
}

// ---------- Event header / meta / stat tiles ----------
async function loadEventMeta(){
  try{
    const r = await fetch('/event'); if(!r.ok) return;
    EVENT_META = await r.json();
    const sumr = await fetch('/event/summary');
    if(sumr.ok){ EVENT_SUMMARY_DATA = await sumr.json(); }
    refreshHeader();
  }catch(_){}
}

function refreshHeader(){
  const e = EVENT_META || {};
  const s = EVENT_SUMMARY_DATA || {};
  // Event name
  const nameEl = document.getElementById('event-name');
  const name = (e.name || s.name || '').trim();
  if(name){ nameEl.textContent = name; nameEl.dataset.empty = 'false'; }
  else { nameEl.textContent = 'Untitled event'; nameEl.dataset.empty = 'true'; }

  // Date
  const dateEl = document.getElementById('meta-date');
  if(e.event_date){
    const human = fmtDateHuman(e.event_date);
    let suffix = '';
    if(e.event_end_time){ suffix = ' · ' + new Date(e.event_end_time).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'}); }
    else if(e.event_date.includes('T')){ suffix = ' · ' + new Date(e.event_date).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'}); }
    dateEl.textContent = human + suffix;
    dateEl.dataset.empty = 'false';
  } else {
    dateEl.textContent = 'Set event date';
    dateEl.dataset.empty = 'true';
  }

  // City
  const cityEl = document.getElementById('meta-city');
  const city = (e.city || s.city || '').trim();
  if(city){ cityEl.textContent = city; cityEl.dataset.empty = 'false'; }
  else { cityEl.textContent = 'Add location'; cityEl.dataset.empty = 'true'; }

  // Format
  const fmtEl = document.getElementById('meta-format');
  const fmt = (e.format || s.format || '').trim();
  if(fmt){ fmtEl.textContent = fmt; fmtEl.dataset.empty = 'false'; }
  else { fmtEl.textContent = 'Add format'; fmtEl.dataset.empty = 'true'; }

  // Size
  TARGET_SIZE = +((e.target_size!=null?e.target_size:s.target_size)||0) || 0;
  const sizeEl = document.getElementById('meta-size');
  sizeEl.textContent = TARGET_SIZE ? `${TARGET_SIZE} people` : '— people';
  sizeEl.dataset.empty = TARGET_SIZE ? 'false' : 'true';

  // Days tile
  const daysEl = document.getElementById('stat-days');
  const labelEl = document.getElementById('stat-days-label');
  if(typeof e.days_until === 'number'){
    if(e.days_until < 0){ daysEl.textContent = Math.abs(e.days_until); labelEl.textContent = 'days ago'; }
    else if(e.days_until === 0){ daysEl.textContent = 'Today'; labelEl.textContent = ''; }
    else if(e.days_until === 1){ daysEl.textContent = 'Tomorrow'; labelEl.textContent = ''; }
    else { daysEl.textContent = e.days_until; labelEl.textContent = 'days away'; }
  } else {
    daysEl.textContent = '—'; labelEl.textContent = 'days away';
  }

  // Sticky text
  const stick = [];
  if(name) stick.push(name);
  if(e.event_date) stick.push(fmtDateHuman(e.event_date));
  document.getElementById('sticky-event').textContent = stick.join(' · ');
}

async function refreshAllStats(){
  // Confirmed (from /attendees summary)
  try{
    const r = await fetch('/attendees');
    if(r.ok){
      const data = await r.json();
      ATT_STATE = data;
      document.getElementById('stat-confirmed').textContent = data.summary.confirmed || 0;
      document.getElementById('stat-confirmed-of').textContent = ` / ${data.summary.total||0}`;
    }
  }catch(_){}
  // Spent (from /budget summary)
  try{
    const r = await fetch('/budget');
    if(r.ok){
      const data = await r.json();
      BD_STATE = data;
      const spent = +(data.summary.spent||0);
      const total = +(data.summary.total_budget||0);
      document.getElementById('stat-spent').textContent = total ? '$'+fmtMoney(spent) : '—';
      document.getElementById('stat-spent-of').textContent = total ? ` / $${fmtMoney(total)}` : '';
    }
  }catch(_){}
  // Vendors booked: count distinct categories with at least one Booked or Paid line item
  // (Venue, Food map to org categories venues, caterers; Sponsors counted separately if any.)
  try{
    const items = (BD_STATE.line_items || []);
    const bookedCats = new Set();
    items.forEach(it => {
      if(it.status === 'Booked' || it.status === 'Paid'){
        if(it.category === 'Venue') bookedCats.add('venue');
        else if(it.category === 'Food') bookedCats.add('catering');
      }
    });
    // Sponsors: count if sponsor_income > 0
    if(+(BD_STATE.summary && BD_STATE.summary.sponsor_income) > 0) bookedCats.add('sponsor');
    document.getElementById('stat-vendors').textContent = bookedCats.size;
  }catch(_){}
}

// ---------- Inline edit event name ----------
const eventNameEl = document.getElementById('event-name');
eventNameEl.addEventListener('click', () => {
  if(eventNameEl.contentEditable !== 'true'){
    eventNameEl.contentEditable = 'true';
    eventNameEl.dataset.empty = 'false';
    if(eventNameEl.textContent === 'Untitled event') eventNameEl.textContent = '';
    eventNameEl.focus();
    document.execCommand('selectAll', false, null);
  }
});
eventNameEl.addEventListener('keydown', (e) => {
  if(e.key === 'Enter'){ e.preventDefault(); eventNameEl.blur(); }
  if(e.key === 'Escape'){ eventNameEl.textContent = (EVENT_META.name || '') || 'Untitled event'; eventNameEl.dataset.empty = (EVENT_META.name?'false':'true'); eventNameEl.blur(); }
});
eventNameEl.addEventListener('blur', async () => {
  eventNameEl.contentEditable = 'false';
  const newName = eventNameEl.textContent.trim();
  if(newName === (EVENT_META.name || '').trim()){
    refreshHeader(); return;
  }
  await fetch('/event/info',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newName})});
  await loadEventMeta();
});

// ---------- Date popover ----------
function openDatePopover(ev){
  ev && ev.stopPropagation();
  const pop = document.getElementById('date-popover');
  const target = ev ? ev.currentTarget : document.getElementById('meta-date');
  const rect = target.getBoundingClientRect();
  pop.style.top = (window.scrollY + rect.bottom + 6) + 'px';
  pop.style.left = (window.scrollX + rect.left) + 'px';
  // Pre-fill with current values
  const e = EVENT_META || {};
  const ed = e.event_date || '';
  document.getElementById('ev-date').value = ed.slice(0,10);
  if(ed.includes('T')){
    document.getElementById('ev-start').value = ed.slice(11,16);
  } else { document.getElementById('ev-start').value = ''; }
  if(e.event_end_time){
    document.getElementById('ev-end').value = String(e.event_end_time).slice(11,16);
  } else { document.getElementById('ev-end').value = ''; }
  pop.classList.add('show');
  setTimeout(() => document.addEventListener('click', closeDatePopoverOnOutside, {once:true}), 0);
}
function closeDatePopoverOnOutside(e){
  const pop = document.getElementById('date-popover');
  if(!pop.contains(e.target)) closeDatePopover();
  else setTimeout(() => document.addEventListener('click', closeDatePopoverOnOutside, {once:true}), 0);
}
function closeDatePopover(){ document.getElementById('date-popover').classList.remove('show'); }
async function saveDatePopover(){
  const dateVal = document.getElementById('ev-date').value;
  const startVal = document.getElementById('ev-start').value;
  const endVal = document.getElementById('ev-end').value;
  let event_date = dateVal || '';
  if(event_date && startVal) event_date = event_date + 'T' + startVal;
  let event_end_time = null;
  if(dateVal && endVal) event_end_time = dateVal + 'T' + endVal;
  await fetch('/event/date',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_date,event_end_time})});
  closeDatePopover();
  loadEventMeta();
  refreshAllStats();
}

// ---------- Info popover (city, format, target_size) ----------
let INFO_POP_FIELD = '';
function openInfoPopover(field, ev){
  ev && ev.stopPropagation();
  INFO_POP_FIELD = field;
  const pop = document.getElementById('info-popover');
  const target = ev ? ev.currentTarget : document.getElementById('meta-'+(field==='target_size'?'size':field));
  const rect = target.getBoundingClientRect();
  pop.style.top = (window.scrollY + rect.bottom + 6) + 'px';
  pop.style.left = (window.scrollX + rect.left) + 'px';
  const labels = {city:'Location', format:'Format', target_size:'Target size'};
  document.getElementById('info-popover-label').textContent = labels[field] || field;
  const inp = document.getElementById('info-popover-input');
  if(field === 'target_size'){
    inp.type = 'number'; inp.min = '0'; inp.step = '1';
    inp.value = (EVENT_META.target_size || '');
    inp.placeholder = '100';
  } else {
    inp.type = 'text';
    inp.removeAttribute('min'); inp.removeAttribute('step');
    inp.value = (EVENT_META[field] || '');
    inp.placeholder = field === 'city' ? 'San Francisco' : 'hackathon, dinner, summit…';
  }
  pop.classList.add('show');
  inp.focus();
  inp.select();
  setTimeout(() => document.addEventListener('click', closeInfoPopoverOnOutside, {once:true}), 0);
}
function closeInfoPopoverOnOutside(e){
  const pop = document.getElementById('info-popover');
  if(!pop.contains(e.target)) closeInfoPopover();
  else setTimeout(() => document.addEventListener('click', closeInfoPopoverOnOutside, {once:true}), 0);
}
function closeInfoPopover(){ document.getElementById('info-popover').classList.remove('show'); }
async function saveInfoPopover(){
  const raw = document.getElementById('info-popover-input').value;
  let val = (raw || '').trim();
  if(INFO_POP_FIELD === 'target_size') val = parseInt(val || '0', 10) || 0;
  await fetch('/event/info',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({[INFO_POP_FIELD]:val})});
  closeInfoPopover();
  loadEventMeta();
}
document.getElementById('info-popover-input').addEventListener('keydown', (e) => {
  if(e.key === 'Enter') saveInfoPopover();
  if(e.key === 'Escape') closeInfoPopover();
});

// ---------- Sticky header behavior ----------
const stickyBar = document.getElementById('sticky-bar');
const pageHeader = document.getElementById('page-header');
window.addEventListener('scroll', () => {
  if(window.scrollY > pageHeader.offsetHeight - 30){
    stickyBar.classList.add('scrolled');
  } else {
    stickyBar.classList.remove('scrolled');
  }
}, {passive:true});

// ---------- Tabs ----------
function switchTab(name){
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + name));
  stopAttendeePoll();
  if(name === 'budget') loadBudget();
  if(name === 'attendees'){ loadAttendees(); startAttendeePoll(); }
  if(name === 'ei' && ALL_PEOPLE.length === 0){
    document.getElementById('result').innerHTML = emptyState('No prospects yet','Run a brief above to source attendees.','people');
  }
}

// ---------- Message modal ----------
function openMsg(name){
  MSG_FOCUS_NAME = name;
  const focus = ALL_PEOPLE.find(p => (p.name||'').trim() === name) || ALL_PEOPLE[0];
  document.getElementById('msg-focus-name').textContent = focus.name || '';
  document.getElementById('msg-focus-meta').textContent = [focus.role, focus.company, focus.persona].filter(Boolean).join(' · ');
  document.getElementById('msg-focus-contact').innerHTML = contactIcons(focus);
  const ta = document.getElementById('msg-template');
  if(!ta.value.trim()) ta.value = DEFAULT_TEMPLATE;
  const slider = document.getElementById('msg-slider');
  slider.max = ALL_PEOPLE.length; slider.value = 1;
  document.getElementById('msg-slider-val').textContent = '1';
  document.getElementById('msg-modal').classList.add('show');
  rerenderPreview();
}
function closeMsg(){ document.getElementById('msg-modal').classList.remove('show'); }
function selectedPeople(){
  const n = parseInt(document.getElementById('msg-slider').value, 10) || 1;
  const focus = ALL_PEOPLE.find(p => (p.name||'').trim() === MSG_FOCUS_NAME);
  const rest = ALL_PEOPLE.filter(p => p !== focus);
  return focus ? [focus, ...rest.slice(0, Math.max(0,n-1))] : rest.slice(0,n);
}
async function rerenderPreview(){
  const tmpl = document.getElementById('msg-template').value;
  const picked = selectedPeople();
  const names = picked.map(p => p.name);
  const r = await fetch('/messages/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template:tmpl,names})});
  const data = await r.json();
  const list = document.getElementById('msg-preview-list');
  if(!data.messages || !data.messages.length){
    list.innerHTML = '<div class="empty" style="padding:24px">No people matched.</div>';
    return;
  }
  list.innerHTML = data.messages.map(m => `
    <div class="preview-row">
      <div class="pname">
        <span style="display:inline-flex;align-items:center;gap:8px">${avatar(m.name,'avatar-sm')}<b>${escapeHtml(m.name)}</b> <span class="muted">${escapeHtml(m.role||'')}${m.company?' @ '+escapeHtml(m.company):''}</span> <span class="channel">${m.channel}${m.email?': '+escapeHtml(m.email):''}</span></span>
        ${m.email ? `<a class="btn btn-tertiary btn-sm" href="${mailtoFor(m)}">Open in mail</a>` : '<span class="dim" style="font-size:11px">no email</span>'}
      </div>
      <div class="pmsg">${escapeHtml(m.rendered)}</div>
    </div>`).join('');
}
function mailtoFor(m){
  const subject = (document.getElementById('msg-subject').value || 'Invitation').trim();
  return `mailto:${encodeURIComponent(m.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(m.rendered)}`;
}
async function openAllMail(){
  const tmpl = document.getElementById('msg-template').value;
  const picked = selectedPeople();
  const names = picked.map(p => p.name);
  const r = await fetch('/messages/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template:tmpl,names})});
  const data = await r.json();
  const withEmail = (data.messages||[]).filter(m => m.email);
  if(!withEmail.length){ alert('No emails available — discover contacts first or skip recipients without email.'); return; }
  if(!confirm(`This will open ${withEmail.length} draft email(s) in your mail client. Each is pre-filled but NOT sent — you'll click Send yourself. Continue?`)) return;
  withEmail.forEach((m, i) => setTimeout(() => { window.location.href = mailtoFor(m); }, i * 250));
}

// ---------- Organization tab ----------
let ORG_CAT = 'venues';
let ORG_STATE = {venues:{status:'idle',results:[],error:'',sort:'relevance',autoSourced:false},
                 caterers:{status:'idle',results:[],error:'',sort:'relevance',autoSourced:false},
                 sponsors:{status:'idle',results:[],error:'',sort:'relevance',autoSourced:false}};
let SHOWING_SAVED = false;

function switchCat(cat){
  ORG_CAT = cat; SHOWING_SAVED = false;
  document.getElementById('btn-show-saved').textContent = 'Show saved';
  document.querySelectorAll('.org-pill').forEach(b => b.classList.toggle('active', b.dataset.cat === cat));
  ['venues','caterers','sponsors'].forEach(c => {
    document.getElementById('form-'+c).style.display = c === cat ? 'grid' : 'none';
  });
  renderOrgCards();
  refreshOrgStatus();
  // Toggle banner visibility based on whether this cat was auto-sourced
  const banner = document.getElementById('org-banner');
  banner.style.display = ORG_STATE[cat].autoSourced ? 'flex' : 'none';
}

function buildQuery(cat){
  const v = id => (document.getElementById(id).value||'').trim();
  if(cat==='venues') return {location:v('v-location'),capacity:v('v-capacity'),availability:v('v-availability'),amenities:v('v-amenities'),budget:v('v-budget')};
  if(cat==='caterers') return {location:v('c-location'),cuisine:v('c-cuisine'),headcount:v('c-headcount'),dietary:v('c-dietary'),budget:v('c-budget')};
  return {industry:v('s-industry'),size:v('s-size'),budget:v('s-budget'),notes:v('s-notes')};
}
async function orgSearch(cat, opts){
  opts = opts || {};
  const q = opts.query || buildQuery(cat);
  const sortId = cat==='venues'?'v-sort':cat==='caterers'?'c-sort':'s-sort';
  const sort = opts.sort || (document.getElementById(sortId).value||'relevance');
  ORG_STATE[cat] = {status:'loading',results:[],error:'',sort,autoSourced:!!opts.autoSourced};
  if(!opts.suppressActiveSwitch && ORG_CAT !== cat) switchCat(cat);
  if(ORG_CAT === cat){ renderOrgCards(); refreshOrgStatus(); }
  try{
    const r = await fetch('/org/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category:cat,query:q,sort})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'search failed');
    ORG_STATE[cat] = {status:'ok',results:data.results||[],error:'',sort,autoSourced:!!opts.autoSourced,telemetry:data.telemetry};
  }catch(e){
    ORG_STATE[cat] = {status:'error',results:[],error:e.message,sort,autoSourced:!!opts.autoSourced};
  }
  if(ORG_CAT === cat){ renderOrgCards(); refreshOrgStatus(); }
}
function retryCategory(cat){ orgSearch(cat,{}); }
function refreshOrgStatus(){
  const st = ORG_STATE[ORG_CAT];
  const el = document.getElementById('org-status');
  const banner = document.getElementById('org-banner');
  const meta = document.getElementById('org-banner-meta');
  banner.style.display = st.autoSourced ? 'flex' : 'none';
  if(SHOWING_SAVED){ el.textContent = `${getSaved().length} saved`; return; }
  if(st.status === 'loading'){ el.innerHTML = '<span class="spinner"></span>searching…'; }
  else if(st.status === 'error'){ el.textContent = ''; }
  else if(st.status === 'ok'){ el.textContent = `${st.results.length} result${st.results.length===1?'':'s'}`; if(st.telemetry) meta.textContent = `${st.telemetry.duration_s||''}s${st.telemetry.cache_hit?' · cached':''}`; }
  else el.textContent = '';
}

function savedKey(){ return 'ei.org.saved.' + ORG_CAT; }
function getSaved(){ try{ return JSON.parse(localStorage.getItem(savedKey())||'[]'); }catch(_){ return []; } }
function setSaved(arr){ localStorage.setItem(savedKey(), JSON.stringify(arr)); }
function isSaved(item){ return getSaved().some(s => s.name === item.name); }
function toggleSave(idx){
  const item = (SHOWING_SAVED ? getSaved() : ORG_STATE[ORG_CAT].results)[idx];
  if(!item) return;
  let saved = getSaved();
  if(saved.some(s => s.name === item.name)) saved = saved.filter(s => s.name !== item.name);
  else saved.push(item);
  setSaved(saved);
  renderOrgCards();
  // If user is on the budget tab, push the new shortlist
}
function toggleSaved(){
  SHOWING_SAVED = !SHOWING_SAVED;
  document.getElementById('btn-show-saved').textContent = SHOWING_SAVED ? 'Show search results' : 'Show saved';
  renderOrgCards(); refreshOrgStatus();
}
function renderOrgCards(){
  const root = document.getElementById('org-results');
  const st = ORG_STATE[ORG_CAT];
  if(SHOWING_SAVED){
    const list = getSaved();
    root.innerHTML = list.length
      ? list.map((it,i) => orgCardHtml(it,i)).join('')
      : emptyState('No saved items', 'Save items from search results to shortlist them here.', 'list');
    return;
  }
  if(st.status === 'loading'){ root.innerHTML = '<div class="empty" style="padding:32px"><span class="spinner"></span><span style="margin-left:8px">searching ' + ORG_CAT + '…</span></div>'; return; }
  if(st.status === 'error'){ root.innerHTML = `<div class="banner banner-error"><span>${escapeHtml(st.error||'search failed')}</span><button class="btn btn-secondary btn-sm" onclick="retryCategory('${ORG_CAT}')">Retry</button></div>`; return; }
  if(st.status === 'ok'){
    root.innerHTML = st.results.length
      ? st.results.map((it,i) => orgCardHtml(it,i)).join('')
      : emptyState('No results','Try broadening the query or removing filters.','list');
    return;
  }
  root.innerHTML = emptyState('Run a search', `Configure the form above and search for ${ORG_CAT}.`, 'list');
}
function orgCardHtml(it, i){
  const SVG_STAR = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m12 2 3 7 7 .8-5.3 4.7L18 22l-6-3.7L6 22l1.3-7.5L2 9.8 9 9z"/></svg>';
  const SVG_STAR_FILL = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m12 2 3 7 7 .8-5.3 4.7L18 22l-6-3.7L6 22l1.3-7.5L2 9.8 9 9z"/></svg>';
  const cost = costLine(it);
  const rating = it.rating ? `<div class="org-rating">★ ${(+it.rating).toFixed(1)}</div>` : '';
  const saved = isSaved(it);
  const meta = metaLine(it);
  const desc = it.description ? `<div class="desc">${escapeHtml(it.description)}</div>` : '';
  const details = detailsHtml(it);
  return `<div class="org-card">
    <div class="head">
      <div>
        <div class="org-card-name">${escapeHtml(it.name||'(no name)')}${saved ? ' <span class="chip">Saved</span>' : ''}</div>
        <div class="org-meta">${meta}</div>
      </div>
      <div class="right">
        <div class="right-stack">
          ${cost ? `<div class="org-cost">${escapeHtml(cost)}</div>` : ''}
          ${rating}
        </div>
        <button class="save-btn ${saved?'saved':''}" onclick="toggleSave(${i})" title="${saved?'Unsave':'Save'}">${saved?SVG_STAR_FILL:SVG_STAR}</button>
      </div>
    </div>
    ${desc}
    ${details}
    <div class="actions">
      ${it.contact_email ? `<a class="btn btn-secondary btn-sm" href="${mailtoOrg(it)}">Contact</a>` : ''}
      ${it.website ? `<a class="btn btn-tertiary btn-sm" href="${escapeHtml(it.website)}" target="_blank">Website</a>` : ''}
      ${it.source_url ? `<a class="btn btn-tertiary btn-sm" href="${escapeHtml(it.source_url)}" target="_blank">Source</a>` : ''}
    </div>
  </div>`;
}
function metaLine(it){
  if(ORG_CAT === 'venues'){ return [it.address||'', it.city||'', it.capacity?`cap. ${it.capacity}`:''].filter(Boolean).map(escapeHtml).join(' · '); }
  if(ORG_CAT === 'caterers'){ return [it.cuisine_type||'', it.location||'', it.minimum_order||''].filter(Boolean).map(escapeHtml).join(' · '); }
  return [it.industry||'', it.company_size||'', it.budget_range||''].filter(Boolean).map(escapeHtml).join(' · ');
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
    if(Array.isArray(it.amenities) && it.amenities.length) parts.push(it.amenities.map(a => `<span class="amenity">${escapeHtml(a)}</span>`).join(''));
    if(it.minimum_spend) parts.push(`<div class="muted">Min spend: ${escapeHtml(it.minimum_spend)}</div>`);
  }
  if(ORG_CAT === 'caterers'){
    if(Array.isArray(it.dietary_accommodations) && it.dietary_accommodations.length) parts.push(it.dietary_accommodations.map(d => `<span class="amenity">${escapeHtml(d)}</span>`).join(''));
    if(Array.isArray(it.pricing_tiers) && it.pricing_tiers.length) parts.push('<ul>' + it.pricing_tiers.map(t => `<li>${escapeHtml(t.name||'')}: ${escapeHtml(t.price||'')}</li>`).join('') + '</ul>');
  }
  if(ORG_CAT === 'sponsors'){
    if(Array.isArray(it.past_events_sponsored) && it.past_events_sponsored.length) parts.push('<div><b>Past events:</b> ' + it.past_events_sponsored.slice(0,5).map(escapeHtml).join(', ') + '</div>');
    if(it.contact_person) parts.push(`<div><b>Likely contact:</b> ${escapeHtml(it.contact_person)}</div>`);
  }
  if(!parts.length) return '';
  return `<details><summary>more details</summary><div>${parts.join('')}</div></details>`;
}
function mailtoOrg(it){
  const subject = `Inquiry — event ${ORG_CAT === 'venues' ? 'venue' : ORG_CAT === 'caterers' ? 'catering' : 'sponsorship'}`;
  const body = `Hi ${it.contact_person || 'there'},\n\nI'm planning an event and would love to talk about ${ORG_CAT === 'sponsors' ? 'a possible sponsorship partnership' : ORG_CAT === 'caterers' ? 'catering options' : 'availability and pricing for ' + (it.name||'your space')}.\n\nQuick details about the event:\n- ...\n\nHow does your team like to take inquiries?\n\nThanks!`;
  return `mailto:${encodeURIComponent(it.contact_email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

async function autoFireOrgSearches(){
  let summary = null;
  try{ const r = await fetch('/event/summary'); if(r.ok){ summary = await r.json(); } }catch(_){}
  if(!summary || !summary.ok) return;
  const queries = deriveOrgQueries(summary);
  if(!queries) return;
  const banner = document.getElementById('org-banner-meta');
  if(banner) banner.textContent = `${summary.target_size||'?'} ${summary.format||'event'} in ${summary.city||'?'}`;
  ['venues','caterers','sponsors'].forEach(cat => {
    orgSearch(cat,{query:queries[cat],sort:'relevance',autoSourced:true,suppressActiveSwitch:true});
  });
}
function deriveOrgQueries(s){
  const headcount = s.target_size || 100;
  const city = s.city || '';
  const fmt = s.format || 'event';
  return {
    venues: {location:city,capacity:headcount,availability:'',amenities:'',budget:''},
    caterers: {location:city,cuisine:'',headcount,dietary:'',budget:''},
    sponsors: {industry:fmt,size:'',budget:'',notes:''},
  };
}

// ---------- Budget tab ----------
const BUDGET_CATS = ["Venue","Food","A/V","Marketing","Other"];

async function loadBudget(){
  await pushShortlistToBudget();
  try{
    const r = await fetch('/budget'); if(!r.ok) return;
    BD_STATE = await r.json();
  }catch(_){return;}
  const totalInp = document.getElementById('bd-total');
  if(totalInp && document.activeElement !== totalInp) totalInp.value = BD_STATE.summary.total_budget || '';
  const sponsorInp = document.getElementById('bd-sponsor');
  if(sponsorInp && document.activeElement !== sponsorInp) sponsorInp.value = BD_STATE.summary.sponsor_income || '';
  renderBudgetBar();
  renderBudgetCategories();
  refreshAllStats();
}

function renderBudgetBar(){
  const s = BD_STATE.summary || {};
  const total = +s.total_budget || 0;
  const spent = +s.spent || 0;
  const pct = total > 0 ? (spent / total) * 100 : 0;
  const fill = document.getElementById('bd-bar-fill');
  fill.style.width = Math.min(100, Math.max(0, pct)).toFixed(1) + '%';
  const text = document.getElementById('bd-bar-text');
  const left = (total - spent);
  if(total === 0){
    text.innerHTML = '<span class="muted">Set a total budget to track spending.</span>';
  } else if(left < 0){
    text.innerHTML = `<span><b>$${fmtMoney(spent)}</b> of <b>$${fmtMoney(total)}</b> spent</span><span class="bd-over-label">↑ Over by $${fmtMoney(-left)}</span>`;
  } else {
    text.innerHTML = `<span><b>$${fmtMoney(spent)}</b> of <b>$${fmtMoney(total)}</b> spent</span><span class="muted">$${fmtMoney(left)} left</span>`;
  }
}

function renderBudgetCategories(){
  const root = document.getElementById('bd-categories');
  const itemsByCat = {};
  BUDGET_CATS.forEach(c => itemsByCat[c] = []);
  (BD_STATE.line_items||[]).forEach(it => { if(itemsByCat[it.category]) itemsByCat[it.category].push(it); });
  const total = +(BD_STATE.summary && BD_STATE.summary.total_budget) || 0;
  root.innerHTML = BUDGET_CATS.map(cat => {
    const items = itemsByCat[cat];
    const catTotal = items.reduce((a,b) => a + (+b.cost||0), 0);
    const pct = total > 0 ? Math.min(100, (catTotal/total)*100) : 0;
    const rows = items.map(it => budgetItemRow(it)).join('');
    const open = items.length > 0;
    return `<details class="bd-cat" ${open ? 'open' : ''}>
      <summary>
        <span class="cat-name">${cat}</span>
        <div class="cat-bar"><div class="cat-bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
        <div class="cat-amount">$${fmtMoney(catTotal)}<span class="cat-count">${items.length} item${items.length===1?'':'s'}</span></div>
      </summary>
      <div class="cat-body">
        ${rows || '<div class="muted" style="font-size:13px;padding:14px 0">No items.</div>'}
        <button class="bd-add-trigger" onclick="showBudgetAddForm('${cat}')" id="bd-add-trigger-${cat}">+ Add line item</button>
        <div class="bd-add-form hidden" id="bd-add-form-${cat}">
          <input id="bd-add-name-${cat}" placeholder="e.g. Catering deposit">
          <input id="bd-add-cost-${cat}" type="number" placeholder="Cost" min="0" step="50">
          <button class="btn btn-primary btn-sm" onclick="addBudgetItem('${cat}')">Add</button>
          <button class="btn btn-tertiary btn-sm" onclick="hideBudgetAddForm('${cat}')">Cancel</button>
        </div>
      </div>
    </details>`;
  }).join('');
}

function budgetItemRow(it){
  const src = it.source === 'org_shortlist'
    ? `<span class="src-tag">from Organization</span>`
    : '';
  const statusOpts = ['Planned','Booked','Paid'].map(s => `<option value="${s}" ${it.status===s?'selected':''}>${s}</option>`).join('');
  return `<div class="bd-li-row">
    <div class="bd-li-name"><span>${escapeHtml(it.name||'')}</span>${src}</div>
    <div><input class="input bd-li-cost-input input-sm" type="number" min="0" step="50" value="${it.cost||0}" onchange="updateBudgetCost('${it.id}', this.value)"></div>
    <div class="bd-li-status"><select class="input-sm" onchange="updateBudgetStatus('${it.id}', this.value)">${statusOpts}</select></div>
    <button class="bd-li-del" onclick="deleteBudgetItem('${it.id}')" title="Delete">×</button>
  </div>`;
}

function showBudgetAddForm(cat){
  document.getElementById('bd-add-trigger-'+cat).style.display = 'none';
  document.getElementById('bd-add-form-'+cat).classList.remove('hidden');
  document.getElementById('bd-add-name-'+cat).focus();
}
function hideBudgetAddForm(cat){
  document.getElementById('bd-add-trigger-'+cat).style.display = '';
  document.getElementById('bd-add-form-'+cat).classList.add('hidden');
  document.getElementById('bd-add-name-'+cat).value = '';
  document.getElementById('bd-add-cost-'+cat).value = '';
}

async function saveBudgetTotal(){
  const v = parseFloat(document.getElementById('bd-total').value || '0') || 0;
  const status = document.getElementById('bd-total-status');
  status.textContent = 'saving…';
  await fetch('/budget/total',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({total_budget:v})});
  await loadBudget();
  status.textContent = 'saved';
  setTimeout(() => { if(status.textContent === 'saved') status.textContent = ''; }, 1500);
}
async function saveSponsorIncome(){
  const v = parseFloat(document.getElementById('bd-sponsor').value || '0') || 0;
  await fetch('/budget/sponsor_income',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({sponsor_income:v})});
  await loadBudget();
}
async function addBudgetItem(cat){
  const name = (document.getElementById('bd-add-name-'+cat).value||'').trim();
  const cost = parseFloat(document.getElementById('bd-add-cost-'+cat).value||'0') || 0;
  if(!name){ alert('Give the line item a name first.'); return; }
  await fetch('/budget/line_item',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category:cat,name,cost})});
  hideBudgetAddForm(cat);
  await loadBudget();
}
async function updateBudgetCost(id, v){
  await fetch('/budget/line_item/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({cost:parseFloat(v||'0')||0})});
  await loadBudget();
}
async function updateBudgetStatus(id, status){
  await fetch('/budget/line_item/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  await loadBudget();
}
async function deleteBudgetItem(id){
  if(!confirm('Delete this line item?')) return;
  await fetch('/budget/line_item/'+encodeURIComponent(id),{method:'DELETE'});
  await loadBudget();
}
function parseCostText(s){
  if(!s) return 0;
  const m = String(s).match(/\$?\s*([0-9][0-9,]*)/);
  if(!m) return 0;
  return parseInt(m[1].replace(/,/g,''),10) || 0;
}
async function pushShortlistToBudget(){
  const vendors = [];
  ['venues','caterers'].forEach(cat => {
    let saved = [];
    try{ saved = JSON.parse(localStorage.getItem('ei.org.saved.'+cat)||'[]'); }catch(_){}
    saved.forEach(it => {
      const targetCat = cat === 'venues' ? 'Venue' : 'Food';
      const quote = cat === 'venues' ? (it.rental_fee||'') : (it.price_per_head||'');
      vendors.push({category:targetCat,name:it.name||'(unnamed)',cost:parseCostText(quote),cost_text:quote,source_ref:it.name||''});
    });
  });
  if(!vendors.length) return;
  try{ await fetch('/budget/autofill_from_shortlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({vendors})}); }catch(_){}
}

// ---------- Attendees tab ----------
async function loadAttendees(){
  try{
    const r = await fetch('/attendees'); if(!r.ok) return;
    ATT_STATE = await r.json();
  }catch(_){return;}
  renderAttSummary();
  renderAttendees();
  refreshAllStats();
}

function renderAttSummary(){
  const s = ATT_STATE.summary;
  document.getElementById('att-summary-text').innerHTML = `<b>${s.total||0}</b> invited · <b>${s.confirmed||0}</b> confirmed · <b>${s.declined||0}</b> declined`;
}

function setAttendeeFilter(f){
  ATT_FILTER = f;
  document.querySelectorAll('#att-filter-chips .filter-chip').forEach(b => b.classList.toggle('active', b.dataset.filter === f));
  renderAttendees();
}

function statusIcon(status){
  const ICONS = {
    Confirmed: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>',
    Attended: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>',
    Declined: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6l12 12M6 18L18 6"/></svg>',
    Invited: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="6"/></svg>',
  };
  return `<span class="att-status-icon" data-status="${status||'Invited'}">${ICONS[status||'Invited']}</span>`;
}

function renderAttendees(){
  const wrap = document.getElementById('att-list-wrap');
  const list = (ATT_STATE.attendees || []).filter(a => ATT_FILTER === 'all' ? true : (a.status||'Invited') === ATT_FILTER);
  if(!list.length){
    if(!ATT_STATE.attendees.length){
      wrap.innerHTML = emptyState('No attendees yet','Run an Event Intelligence prompt or click "Add attendee" above.','people');
    } else {
      wrap.innerHTML = emptyState('No attendees match this filter','Switch to "All" to see everyone.','list');
    }
    return;
  }
  wrap.innerHTML = `<table class="list">
    <thead><tr><th style="width:32px"></th><th>Name</th><th>Company</th><th style="width:160px">Status</th><th>Notes</th></tr></thead>
    <tbody>${list.map(a => attRow(a)).join('')}</tbody>
  </table>`;
}

function attRow(a){
  const opts = ['Invited','Confirmed','Declined','Attended'].map(s => `<option value="${s}" ${a.status===s?'selected':''}>${s}</option>`).join('');
  return `<tr class="att-row" data-id="${escapeHtml(a.id)}">
    <td>${avatar(a.name||'?')}</td>
    <td><div class="cell-name"><div><div class="name-main">${escapeHtml(a.name||'')}</div>${a.email?`<div class="name-sub">${escapeHtml(a.email)}</div>`:''}</div></div></td>
    <td class="muted">${escapeHtml(a.company||'')}</td>
    <td>
      <div class="att-status-cell">
        ${statusIcon(a.status)}
        <select class="input-sm" onchange="updateAttendeeStatus('${escapeHtml(a.id)}', this.value)">${opts}</select>
      </div>
    </td>
    <td><input class="att-notes-input" placeholder="add note…" value="${escapeHtml(a.notes||'')}" onchange="updateAttendeeNotes('${escapeHtml(a.id)}', this.value)"></td>
  </tr>`;
}

function toggleAddAttendee(){
  const f = document.getElementById('att-add-form');
  f.classList.toggle('hidden');
  if(!f.classList.contains('hidden')) document.getElementById('att-name').focus();
}

async function addAttendee(){
  const name = (document.getElementById('att-name').value||'').trim();
  if(!name){ alert('Name is required.'); return; }
  const company = (document.getElementById('att-company').value||'').trim();
  const email = (document.getElementById('att-email').value||'').trim();
  try{
    const r = await fetch('/attendees',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,company,email})});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail||'failed');
    document.getElementById('att-name').value = '';
    document.getElementById('att-company').value = '';
    document.getElementById('att-email').value = '';
    toggleAddAttendee();
    await loadAttendees();
  }catch(e){
    alert('Failed: ' + e.message);
  }
}

async function updateAttendeeStatus(id, status){
  await fetch('/attendees/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  await loadAttendees();
}
async function updateAttendeeNotes(id, notes){
  await fetch('/attendees/'+encodeURIComponent(id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({notes})});
}

function startAttendeePoll(){
  stopAttendeePoll();
  ATT_POLL_TIMER = setInterval(loadAttendees, 10000);
}
function stopAttendeePoll(){
  if(ATT_POLL_TIMER){ clearInterval(ATT_POLL_TIMER); ATT_POLL_TIMER = null; }
}

// ---------- Keyboard handlers ----------
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){
    closeMsg();
    closeDatePopover();
    closeInfoPopover();
  }
});
['att-name','att-company','att-email'].forEach(id => {
  const el = document.getElementById(id);
  if(el) el.addEventListener('keydown', (e) => { if(e.key === 'Enter') addAttendee(); });
});
BUDGET_CATS.forEach(cat => {
  // Wire after budget renders, since these inputs are rendered dynamically.
});

// ---------- Init ----------
loadEventMeta();
refreshAllStats();
// Render an empty EI state initially so the tab doesn't look broken before /run
document.getElementById('result').innerHTML = emptyState('No prospects yet','Run a brief above to source attendees.','people');
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
