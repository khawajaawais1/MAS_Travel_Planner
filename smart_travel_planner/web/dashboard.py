"""
web/dashboard.py
────────────────
Provides:
  • UI_STATE          – single shared dict read by all agents and HTTP handlers
  • Helper functions  – ui_log, chat_log, set_stage, set_agent_status
  • create_web_app()  – returns configured aiohttp Application
  • SERVER constant   – XMPP server hostname used by agents

The HTML dashboard is self-contained: one HTML file, all CSS/JS inline.
Design aesthetic: refined editorial travel magazine — warm cream palette,
Playfair Display headlines, clean data cards, animated status indicators.
"""

import json
from datetime import datetime
from aiohttp import web

# ── Constants ────────────────────────────────────────────────────────────────
SERVER   = "localhost"
PASSWORD = "Pass123!"

# ── Shared state ─────────────────────────────────────────────────────────────
UI_STATE: dict = {
    "scenario":           None,
    "stage":              "starting",
    "agents": {
        "PreferenceAgent": "stopped",
        "ResearchAgent":   "stopped",
        "OptimizerAgent":  "stopped",
        "ItineraryAgent":  "stopped",
        "BookingAgent":    "stopped",
    },
    "preferences":        None,
    "preferences_answers": {},
    "current_question":   None,
    "pending_user_answer": None,
    "preferences_sent":   False,
    "search_results":     {},
    "optimized_plan":     {},
    "itinerary":          [],
    "booking_summary":    {},
    "total_cost":         None,
    "chat_history":       [],
    "logs":               [],
}

# Will be set by main.py so HTTP handlers can trigger agent behaviours
AGENTS: dict = {}


# ── Helper functions ──────────────────────────────────────────────────────────
def ui_log(agent: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    UI_STATE["logs"].append(f"[{now}] {agent}: {message}")
    if len(UI_STATE["logs"]) > 300:
        UI_STATE["logs"].pop(0)


def chat_log(sender: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    UI_STATE["chat_history"].append({"time": now, "sender": sender, "message": message})
    if len(UI_STATE["chat_history"]) > 300:
        UI_STATE["chat_history"].pop(0)


def set_stage(stage: str) -> None:
    UI_STATE["stage"] = stage


def set_agent_status(agent: str, status: str) -> None:
    UI_STATE["agents"][agent] = status


# ── Simple Q&A assistant ──────────────────────────────────────────────────────
def _assistant_answer(question: str) -> str:
    text    = question.lower().strip()
    prefs   = UI_STATE.get("preferences") or {}
    summary = UI_STATE.get("booking_summary") or {}
    results = UI_STATE.get("search_results") or {}
    opt     = UI_STATE.get("optimized_plan") or {}

    from data.mock_data import FLIGHTS, ACTIVITIES
    dests     = sorted({f["to"] for f in FLIGHTS})
    interests = sorted({a["type"] for a in ACTIVITIES})

    if any(w in text for w in ["destination", "where can", "available dest"]):
        return f"I can search these destinations: {', '.join(dests)}."

    if any(w in text for w in ["interest", "activit"]):
        dest = prefs.get("destination") or summary.get("destination")
        acts = summary.get("activities") or opt.get("activities") or results.get("activities", [])
        if acts:
            names = ", ".join(a["name"] for a in acts)
            return f"Planned activities: {names}."
        return f"Available interest categories: {', '.join(interests)}."

    if any(w in text for w in ["budget", "cost", "price", "total", "how much"]):
        total  = UI_STATE.get("total_cost") or opt.get("total_cost") or summary.get("total_cost")
        budget = prefs.get("budget") or summary.get("budget")
        if total and budget:
            diff = int(total) - int(budget)
            note = "within budget ✅" if diff <= 0 else f"€{diff} over budget ⚠️"
            return f"Total cost: €{total} against your €{budget} budget — {note}."
        if budget:
            return f"Your budget is €{budget}. Total cost will appear after optimisation."
        return "I don't have a budget set yet."

    if any(w in text for w in ["flight", "airline", "fly"]):
        flight = summary.get("flight") or opt.get("best_flight")
        if flight:
            return (f"Flight: {flight['airline']} {flight.get('flight_number','')} "
                    f"({flight['duration']}) — €{flight['price']}.")
        return f"{len(results.get('flights', []))} flights found so far."

    if any(w in text for w in ["hotel", "stay", "accommodation"]):
        hotel = summary.get("hotel") or opt.get("best_hotel")
        if hotel:
            return (f"Hotel: {hotel['name']} in {hotel.get('area','')} "
                    f"— €{hotel['price_per_night']}/night, rated {hotel['rating']}.")
        return f"{len(results.get('hotels', []))} hotels found so far."

    if any(w in text for w in ["itinerary", "plan", "day", "schedule"]):
        itin = summary.get("itinerary") or UI_STATE.get("itinerary") or []
        if itin:
            return "Day-by-day plan: " + " | ".join(
                f"Day {i+1}: {line[:80]}…" if len(line) > 80 else f"Day {i+1}: {line}"
                for i, line in enumerate(itin)
            )
        return "The itinerary will appear here once the ItineraryAgent finishes."

    if any(w in text for w in ["where", "destination"]):
        d = prefs.get("destination") or summary.get("destination")
        return f"Destination: {d}." if d else f"No destination set yet. Options: {', '.join(dests)}."

    if any(w in text for w in ["help", "what can", "commands"]):
        return ("You can ask about: destination, budget/cost, flight, hotel, "
                "activities/interests, itinerary/plan, or just chat.")

    return ("I can answer questions about your destination, budget, flight, hotel, "
            "activities, and day-by-day itinerary. What would you like to know?")


# ── HTTP handlers ─────────────────────────────────────────────────────────────
async def handle_status(request: web.Request) -> web.Response:
    return web.json_response(UI_STATE)


async def handle_send_preferences(request: web.Request) -> web.Response:
    from data.mock_data import FLIGHTS, ACTIVITIES

    dests     = sorted({f["to"] for f in FLIGHTS})
    interests = sorted({a["type"] for a in ACTIVITIES})

    data = await request.json()

    def _norm_dest(v):
        v = (v or "").strip()
        for d in dests:
            if d.lower() == v.lower():
                return d
        return v.title()

    def _parse_interests(v):
        if isinstance(v, list):
            items = v
        else:
            items = str(v or "").replace(" and ", ",").split(",")
        out = []
        for i in items:
            t = i.strip().lower()
            if t and t not in out:
                out.append(t)
        return out or ["cultural"]

    prefs = {
        "scenario":     data.get("scenario", "solo"),
        "destination":  _norm_dest(data.get("destination", "Rome")),
        "days":         max(2, int(data.get("days", 5))),
        "budget":       max(200, int(data.get("budget", 1500))),
        "interests":    _parse_interests(data.get("interests", ["cultural", "food"])),
        "travel_style": data.get("travel_style", "flexible"),
    }

    UI_STATE["preferences"]      = prefs
    UI_STATE["scenario"]         = prefs["scenario"]
    UI_STATE["preferences_sent"] = True
    chat_log("User", json.dumps(prefs, ensure_ascii=False))
    ui_log("System", "Preferences received via form")
    set_stage("user input received")

    pref_agent = AGENTS.get("PreferenceAgent")
    if pref_agent is None:
        return web.json_response(
            {"status": "error", "message": "PreferenceAgent not available."}, status=500
        )

    from agents.preference_agent import PreferenceAgent
    pref_agent.add_behaviour(PreferenceAgent.SendPreferencesBehaviour(prefs))
    return web.json_response({"status": "ok"})


async def handle_ask_question(request: web.Request) -> web.Response:
    data     = await request.json()
    question = data.get("message", "").strip()
    if not question:
        return web.json_response({"status": "error", "message": "Empty message."}, status=400)
    chat_log("User", question)
    answer = _assistant_answer(question)
    chat_log("Travel Assistant", answer)
    ui_log("Assistant", f"Q: {question[:60]} → A: {answer[:60]}")
    return web.json_response({"status": "ok", "answer": answer})


async def handle_submit_answer(request: web.Request) -> web.Response:
    data   = await request.json()
    answer = data.get("answer", "").strip()
    if not answer:
        return web.json_response({"status": "error", "message": "Empty answer."}, status=400)
    if UI_STATE.get("current_question") is None:
        return web.json_response({"status": "error", "message": "No active question."}, status=400)
    UI_STATE["pending_user_answer"] = answer
    chat_log("User", answer)
    ui_log("System", f"User answered: {answer[:60]}")
    set_stage("processing user answer")
    return web.json_response({"status": "ok"})


# ── HTML Frontend ─────────────────────────────────────────────────────────────
_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Smart Travel Planner</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;1,600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{
  --cream:#faf6ef;--ink:#1a1a1a;--muted:#6b6356;--warm-white:#fff9f2;
  --line:#e8e0d4;--accent:#c17f3a;--accent2:#2d6a4f;--dark:#1d2b1e;
  --good:#2d6a4f;--wait:#c17f3a;--bad:#8b3a3a;--panel:#ffffff;
  --radius:12px;--shadow:0 2px 20px rgba(26,26,26,.08);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:var(--cream);color:var(--ink);min-height:100vh}

/* ── Header ─────────────────────────────────────────────────────── */
header{background:var(--dark);color:#fff;padding:28px 36px;display:flex;align-items:flex-end;gap:24px}
header .wordmark{display:flex;flex-direction:column;gap:4px}
header h1{font-family:'Playfair Display',serif;font-size:34px;font-weight:700;letter-spacing:-.5px;color:#f5ede0}
header p{font-size:13px;color:#a8c5b5;font-weight:300;letter-spacing:.04em}
.stage-badge{margin-left:auto;padding:8px 18px;background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.15);border-radius:99px;font-size:12px;
  color:#c8ddd5;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}

/* ── Layout ──────────────────────────────────────────────────────── */
.layout{display:grid;grid-template-columns:380px 1fr;gap:0;min-height:calc(100vh - 96px)}

/* ── Left sidebar ────────────────────────────────────────────────── */
.sidebar{background:var(--warm-white);border-right:1px solid var(--line);
  display:flex;flex-direction:column;overflow:hidden}
.sidebar-section{padding:22px 24px;border-bottom:1px solid var(--line)}
.sidebar-section h3{font-family:'Playfair Display',serif;font-size:16px;
  font-weight:600;color:var(--ink);margin-bottom:14px}

/* Chat */
.chat-scroll{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;
  min-height:320px;max-height:420px}
.msg{max-width:86%;padding:10px 14px;border-radius:12px;font-size:13.5px;
  line-height:1.5;word-break:break-word}
.msg strong{display:block;font-size:11px;font-weight:600;margin-bottom:3px;opacity:.65}
.msg.agent{background:#fff;border:1px solid var(--line);align-self:flex-start;border-radius:4px 12px 12px 12px}
.msg.user{background:var(--dark);color:#e8f5ef;align-self:flex-end;border-radius:12px 4px 12px 12px}
.msg.user strong{color:#8fbfad}
.msg.assistant{background:#f0f9f4;border:1px solid #c8e8d8;align-self:flex-start;border-radius:4px 12px 12px 12px}

/* Composer */
.composer{padding:14px 16px;border-top:1px solid var(--line);display:flex;gap:10px}
.composer input{flex:1;padding:10px 14px;border:1px solid var(--line);border-radius:8px;
  font:inherit;font-size:13.5px;background:#fff;color:var(--ink);outline:none}
.composer input:focus{border-color:var(--accent)}
.composer button{padding:10px 18px;background:var(--accent);color:#fff;
  border:none;border-radius:8px;font:inherit;font-weight:600;cursor:pointer;white-space:nowrap}
.composer button:hover{filter:brightness(.9)}

/* Quick chips */
.chips{padding:10px 16px 14px;display:flex;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--line)}
.chip{padding:6px 12px;background:#f0f9f4;border:1px solid #c8e8d8;color:var(--accent2);
  border-radius:99px;font-size:12px;font-weight:500;cursor:pointer;transition:background .15s}
.chip:hover{background:#d8f0e4}

/* Question box */
.q-box{padding:12px 14px;background:#fffbf2;border-left:3px solid var(--accent);
  border-radius:0 8px 8px 0;font-size:13px;line-height:1.55;color:#4a3f30}

/* Preference form */
.pref-form{display:grid;gap:10px}
.pref-form label{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:4px}
.pref-form input,.pref-form select{width:100%;padding:9px 12px;border:1px solid var(--line);
  border-radius:8px;font:inherit;font-size:13.5px;background:#fff;color:var(--ink);outline:none}
.pref-form input:focus,.pref-form select:focus{border-color:var(--accent)}
.pref-form .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.btn-submit{width:100%;padding:11px;background:var(--accent2);color:#fff;
  border:none;border-radius:8px;font:inherit;font-weight:600;font-size:14px;
  cursor:pointer;margin-top:4px;letter-spacing:.02em}
.btn-submit:hover{filter:brightness(.9)}
#form-status{font-size:12px;color:var(--accent2);margin-top:6px;min-height:16px}

/* ── Main area ───────────────────────────────────────────────────── */
.main{padding:28px;display:flex;flex-direction:column;gap:20px;overflow-y:auto}

/* Metrics row */
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.metric{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px;box-shadow:var(--shadow)}
.metric .label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.07em;margin-bottom:8px}
.metric .value{font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:var(--ink);line-height:1.2}
.metric .sub{font-size:12px;color:var(--muted);margin-top:4px}

/* Cards */
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px;box-shadow:var(--shadow)}
.card h3{font-family:'Playfair Display',serif;font-size:17px;font-weight:600;
  margin-bottom:14px;color:var(--ink)}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}

/* Code blocks */
pre{white-space:pre-wrap;word-break:break-word;background:#1a1a1a;color:#d4e8dc;
  padding:14px;border-radius:8px;font-size:12px;max-height:260px;overflow-y:auto;line-height:1.6}

/* Itinerary timeline */
.timeline{display:flex;flex-direction:column;gap:10px}
.day-item{display:flex;gap:14px;align-items:flex-start}
.day-num{flex-shrink:0;width:36px;height:36px;background:var(--accent2);color:#fff;
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:700;letter-spacing:-.3px}
.day-content{flex:1;padding:10px 14px;background:#f8f9f8;border:1px solid var(--line);
  border-radius:8px;font-size:13px;line-height:1.6;color:#2a2a2a}

/* Agent status */
.agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}
.agent-card{padding:12px 14px;border:1px solid var(--line);border-radius:10px;
  display:flex;align-items:center;gap:10px;background:#fafafa}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.dot.running{background:var(--good);box-shadow:0 0 0 3px rgba(45,106,79,.2)}
.dot.waiting{background:var(--wait);box-shadow:0 0 0 3px rgba(193,127,58,.2)}
.dot.stopped{background:#ccc}
.agent-name{font-size:13px;font-weight:500}
.agent-state{font-size:11px;color:var(--muted);text-transform:capitalize}

/* Logs */
#logs{max-height:200px;font-size:11.5px;color:#b0d4c0;line-height:1.7}

/* Tabs */
.tabs{display:flex;gap:0;border-bottom:1px solid var(--line);margin-bottom:16px}
.tab{padding:9px 16px;font:inherit;font-size:13px;font-weight:500;color:var(--muted);
  background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;
  margin-bottom:-1px;transition:color .15s}
.tab.active{color:var(--accent2);border-bottom-color:var(--accent2)}
.tab-panel{display:none}.tab-panel.active{display:block}

/* Status message */
#status-msg{font-size:12px;color:var(--muted);padding:0 16px 8px;min-height:20px}

@media(max-width:960px){
  .layout{grid-template-columns:1fr}
  .sidebar{border-right:none;border-bottom:1px solid var(--line)}
  .metrics{grid-template-columns:repeat(2,1fr)}
  .two-col{grid-template-columns:1fr}
}
</style>
</head>
<body>
<header>
  <div class="wordmark">
    <h1>Smart Travel Planner</h1>
    <p>Five agents · preferences → research → optimise → itinerary → booking</p>
  </div>
  <div class="stage-badge" id="stage-badge">initialising</div>
</header>

<div class="layout">
  <!-- ── LEFT SIDEBAR ────────────────────────────────────────────── -->
  <aside class="sidebar">

    <!-- Agent is waiting for -->
    <div class="sidebar-section">
      <h3>Active question</h3>
      <div class="q-box" id="current_question">Waiting for agent to start…</div>
    </div>

    <!-- Chat -->
    <div class="sidebar-section" style="padding-bottom:0;border-bottom:none;flex:1;display:flex;flex-direction:column">
      <h3 style="padding-bottom:0">Conversation</h3>
    </div>
    <div class="chat-scroll" id="chat_history"></div>
    <div id="status-msg"></div>
    <div class="chips" id="quick-chips">
      <span class="chip" data-ask="What destinations can you search?">Destinations</span>
      <span class="chip" data-ask="What is the total cost?">Total cost</span>
      <span class="chip" data-ask="Which hotel did you choose?">Hotel</span>
      <span class="chip" data-ask="Show my day-by-day itinerary">Itinerary</span>
      <span class="chip" data-ask="Which flight did you choose?">Flight</span>
    </div>
    <div class="composer">
      <input type="text" id="chat_input" placeholder="Answer or ask a question…" autocomplete="off"/>
      <button id="send_btn">Send</button>
    </div>

    <!-- Preference form -->
    <div class="sidebar-section">
      <h3>Submit preferences</h3>
      <div class="pref-form" id="pref_form">
        <div class="row">
          <div>
            <label>Scenario</label>
            <select id="pf_scenario"><option value="solo">Solo</option><option value="family">Family</option></select>
          </div>
          <div>
            <label>Travel style</label>
            <input id="pf_style" type="text" value="flexible" placeholder="e.g. relaxed"/>
          </div>
        </div>
        <div>
          <label>Destination</label>
          <select id="pf_dest">
            <option>Rome</option><option>Florence</option>
            <option selected>Paris</option><option>Barcelona</option>
          </select>
        </div>
        <div class="row">
          <div>
            <label>Days</label>
            <input id="pf_days" type="number" value="5" min="2" max="14"/>
          </div>
          <div>
            <label>Budget (€)</label>
            <input id="pf_budget" type="number" value="1500" min="200"/>
          </div>
        </div>
        <div>
          <label>Interests (comma-separated)</label>
          <input id="pf_interests" type="text" value="cultural, food"/>
        </div>
        <button class="btn-submit" id="pref_submit">Plan my trip ✈</button>
        <p id="form-status"></p>
      </div>
    </div>

  </aside>

  <!-- ── MAIN AREA ──────────────────────────────────────────────── -->
  <main class="main">

    <!-- Metrics -->
    <div class="metrics">
      <div class="metric">
        <div class="label">Scenario</div>
        <div class="value" id="m_scenario">—</div>
      </div>
      <div class="metric">
        <div class="label">Destination</div>
        <div class="value" id="m_destination">—</div>
      </div>
      <div class="metric">
        <div class="label">Duration</div>
        <div class="value" id="m_days">—</div>
        <div class="sub">days</div>
      </div>
      <div class="metric">
        <div class="label">Total cost</div>
        <div class="value" id="m_cost">pending</div>
        <div class="sub" id="m_budget_note"></div>
      </div>
    </div>

    <!-- Itinerary -->
    <div class="card">
      <h3>📅 Day-by-Day Itinerary</h3>
      <div class="timeline" id="itinerary_list">
        <p style="color:var(--muted);font-size:13px">Itinerary will appear here after optimisation completes.</p>
      </div>
    </div>

    <!-- Data tabs: results / optimised / booking -->
    <div class="card">
      <div class="tabs">
        <button class="tab active" data-tab="search">Search results</button>
        <button class="tab" data-tab="optimized">Optimised plan</button>
        <button class="tab" data-tab="booking">Booking summary</button>
      </div>
      <div class="tab-panel active" id="tab_search"><pre id="search_results">{}</pre></div>
      <div class="tab-panel" id="tab_optimized"><pre id="optimized_plan">{}</pre></div>
      <div class="tab-panel" id="tab_booking"><pre id="booking_summary">Waiting for booking to complete…</pre></div>
    </div>

    <!-- Agent status -->
    <div class="card">
      <h3>Agent status</h3>
      <div class="agent-grid" id="agent_status"></div>
    </div>

    <!-- Logs -->
    <div class="card">
      <h3>System logs</h3>
      <pre id="logs">Loading…</pre>
    </div>

  </main>
</div>

<script>
let latestState = null;

// ── Utilities ────────────────────────────────────────────────────────
function esc(v){ return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
function money(v){ return v==null||v===undefined ? 'pending' : '€'+v; }
function setStatus(msg){ document.getElementById('status-msg').textContent = msg; }
function looksLikeQuestion(t){
  const v=t.trim().toLowerCase();
  return v.endsWith('?')||/^(what|which|who|where|when|why|how|can|could|do|does|is|are|show|tell|explain)\b/.test(v);
}

// ── Chat rendering ───────────────────────────────────────────────────
function renderChat(items){
  const el=document.getElementById('chat_history');
  if(!items||!items.length){ el.innerHTML='<p style="color:var(--muted);font-size:13px;padding:8px">Conversation will appear here…</p>'; return; }
  el.innerHTML=items.map(item=>{
    const cls=item.sender==='User'?'msg user':item.sender==='Travel Assistant'?'msg assistant':'msg agent';
    return `<div class="${cls}"><strong>${esc(item.sender)} · ${esc(item.time)}</strong>${esc(item.message)}</div>`;
  }).join('');
  el.scrollTop=el.scrollHeight;
}

// ── Itinerary rendering ──────────────────────────────────────────────
function renderItinerary(items){
  const el=document.getElementById('itinerary_list');
  if(!items||!items.length){
    el.innerHTML='<p style="color:var(--muted);font-size:13px">Itinerary will appear here after optimisation completes.</p>';
    return;
  }
  el.innerHTML=items.map((line,i)=>`
    <div class="day-item">
      <div class="day-num">${i+1}</div>
      <div class="day-content">${esc(line.replace(/^Day\s*\d+\s*:?\s*/i,''))}</div>
    </div>`).join('');
}

// ── Agent status ─────────────────────────────────────────────────────
function renderAgents(agents){
  const el=document.getElementById('agent_status');
  el.innerHTML=Object.entries(agents).map(([name,state])=>`
    <div class="agent-card">
      <div class="dot ${state}"></div>
      <div><div class="agent-name">${esc(name)}</div><div class="agent-state">${esc(state)}</div></div>
    </div>`).join('');
}

// ── Main refresh ─────────────────────────────────────────────────────
async function refresh(){
  const res=await fetch('/status');
  const d=await res.json();
  latestState=d;
  const prefs=d.preferences||{};
  const summary=d.booking_summary||{};
  const opt=d.optimized_plan||{};

  document.getElementById('stage-badge').textContent=d.stage;
  document.getElementById('current_question').textContent=d.current_question||'Planning complete — ask me anything about your trip.';

  document.getElementById('m_scenario').textContent=d.scenario||'—';
  document.getElementById('m_destination').textContent=prefs.destination||summary.destination||'—';
  document.getElementById('m_days').textContent=prefs.days||summary.days||'—';

  const total=d.total_cost||opt.total_cost||summary.total_cost;
  document.getElementById('m_cost').textContent=money(total);
  const budget=prefs.budget||summary.budget;
  if(total&&budget){
    const diff=total-budget;
    document.getElementById('m_budget_note').textContent=diff<=0?'within budget ✅':`€${diff} over budget`;
  }

  document.getElementById('search_results').textContent=JSON.stringify(d.search_results||{},null,2);
  document.getElementById('optimized_plan').textContent=JSON.stringify(d.optimized_plan||{},null,2);
  document.getElementById('booking_summary').textContent=
    Object.keys(summary).length?JSON.stringify(summary,null,2):'Waiting for booking to complete…';

  renderItinerary(d.itinerary||[]);
  renderChat(d.chat_history||[]);
  renderAgents(d.agents||{});
  document.getElementById('logs').textContent=(d.logs||[]).join('\n');
}

// ── Tabs ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab_'+btn.dataset.tab).classList.add('active');
  });
});

// ── Send message ─────────────────────────────────────────────────────
async function sendMessage(text){
  if(!text) return;
  setStatus('Sending…');
  try{
    const isQ=!latestState||!latestState.current_question||looksLikeQuestion(text);
    const res=await fetch(isQ?'/chat':'/answer',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(isQ?{message:text}:{answer:text})
    });
    setStatus(res.ok?'':'Error '+res.status);
    await refresh();
    setStatus('');
  }catch(e){ setStatus('Send failed'); }
}

// ── Event listeners ──────────────────────────────────────────────────
document.getElementById('send_btn').addEventListener('click',()=>{
  const inp=document.getElementById('chat_input');
  const val=inp.value.trim(); inp.value='';
  sendMessage(val);
});
document.getElementById('chat_input').addEventListener('keydown',e=>{
  if(e.key==='Enter'){ e.preventDefault(); document.getElementById('send_btn').click(); }
});
document.querySelectorAll('.chip').forEach(c=>{
  c.addEventListener('click',()=>sendMessage(c.dataset.ask));
});

// ── Preference form ───────────────────────────────────────────────────
document.getElementById('pref_submit').addEventListener('click',async()=>{
  const payload={
    scenario: document.getElementById('pf_scenario').value,
    destination: document.getElementById('pf_dest').value,
    days: parseInt(document.getElementById('pf_days').value)||5,
    budget: parseInt(document.getElementById('pf_budget').value)||1500,
    interests: document.getElementById('pf_interests').value,
    travel_style: document.getElementById('pf_style').value||'flexible'
  };
  document.getElementById('form-status').textContent='Submitting…';
  try{
    const res=await fetch('/preferences',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await res.json();
    document.getElementById('form-status').textContent=data.status==='ok'?'✅ Preferences sent!':'❌ '+data.message;
    await refresh();
  }catch(e){ document.getElementById('form-status').textContent='❌ Error: '+e.message; }
});

// ── Boot ─────────────────────────────────────────────────────────────
refresh().catch(e=>setStatus('Load error: '+e.message));
setInterval(()=>refresh().catch(e=>setStatus('Refresh error: '+e.message)),1200);
</script>
</body>
</html>"""


async def handle_index(request: web.Request) -> web.Response:
    return web.Response(text=_HTML, content_type="text/html")


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/",           handle_index)
    app.router.add_get("/status",     handle_status)
    app.router.add_post("/preferences", handle_send_preferences)
    app.router.add_post("/answer",    handle_submit_answer)
    app.router.add_post("/chat",      handle_ask_question)
    return app