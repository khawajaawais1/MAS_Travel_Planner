"""
Smart Travel Planner - Multi Agent System
Uses SPADE 4.1.2 with embedded XMPP server (no external server needed).
Run:  python main.py          (solo scenario)
      python main.py family   (family scenario)
"""
import sys
import json
import asyncio
from datetime import datetime
from aiohttp import web
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template
from spade.container import run_container
from data.mock_data import FLIGHTS, HOTELS, ACTIVITIES

SERVER   = "localhost"
PASSWORD = "Pass123!"
AVAILABLE_DESTINATIONS = sorted({item["to"] for item in FLIGHTS})
AVAILABLE_INTERESTS = sorted({item["type"] for item in ACTIVITIES})

UI_STATE = {
    "scenario": None,
    "stage": "starting",
    "agents": {
        "PreferenceAgent": "stopped",
        "ResearchAgent": "stopped",
        "OptimizerAgent": "stopped",
        "ItineraryAgent": "stopped",
        "BookingAgent": "stopped",
    },
    "preferences": None,
    "preferences_answers": {},
    "current_question": None,
    "pending_user_answer": None,
    "preferences_sent": False,
    "search_results": {},
    "optimized_plan": {},
    "itinerary": [],
    "booking_summary": {},
    "total_cost": None,
    "chat_history": [],
    "logs": []
}

AGENTS = {}


def ui_log(agent: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    UI_STATE["logs"].append(f"[{now}] {agent}: {message}")
    if len(UI_STATE["logs"]) > 200:
        UI_STATE["logs"].pop(0)


def set_agent_status(agent: str, status: str) -> None:
    UI_STATE["agents"][agent] = status


def set_stage(stage: str) -> None:
    UI_STATE["stage"] = stage


def chat_log(sender: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    UI_STATE["chat_history"].append({
        "time": now,
        "sender": sender,
        "message": message,
    })
    if len(UI_STATE["chat_history"]) > 200:
        UI_STATE["chat_history"].pop(0)


def normalize_destination(destination: str) -> str:
    value = (destination or "").strip()
    for option in AVAILABLE_DESTINATIONS:
        if option.lower() == value.lower():
            return option
    return value.title()


def parse_interests(value) -> list:
    if isinstance(value, list):
        items = value
    else:
        items = str(value or "").replace(" and ", ",").split(",")
    normalized = []
    for item in items:
        interest = str(item).strip().lower()
        if interest and interest not in normalized:
            normalized.append(interest)
    return normalized or ["cultural"]


def assistant_answer(question: str) -> str:
    text = question.lower().strip()
    prefs = UI_STATE.get("preferences") or {}
    summary = UI_STATE.get("booking_summary") or {}
    results = UI_STATE.get("search_results") or {}
    optimized = UI_STATE.get("optimized_plan") or {}

    if "destination" in text and any(word in text for word in ["available", "search", "option", "can"]):
        return f"I can currently search these destinations: {', '.join(AVAILABLE_DESTINATIONS)}."

    if any(word in text for word in ["interest", "activity type", "activities type"]):
        return f"I can match interests like: {', '.join(AVAILABLE_INTERESTS)}."

    if any(word in text for word in ["destination", "where"]):
        destination = prefs.get("destination") or summary.get("destination")
        return f"The current destination is {destination}." if destination else (
            f"I do not have a destination yet. I can search: {', '.join(AVAILABLE_DESTINATIONS)}."
        )

    if any(word in text for word in ["budget", "cost", "price", "total"]):
        total = summary.get("total_cost") or optimized.get("total_cost") or UI_STATE.get("total_cost")
        budget = prefs.get("budget")
        if total and budget:
            return f"The selected plan costs EUR {total} against your EUR {budget} budget."
        if budget:
            return f"Your current budget is EUR {budget}. I am still building the total cost."
        return "I do not have a budget or total cost yet."

    if "flight" in text or "airline" in text:
        flight = summary.get("flight") or optimized.get("best_flight")
        if flight:
            return f"The recommended flight is {flight['airline']} for EUR {flight['price']} with a {flight['duration']} duration."
        return f"I found {len(results.get('flights', []))} matching flights so far."

    if "hotel" in text or "stay" in text:
        hotel = summary.get("hotel") or optimized.get("best_hotel")
        if hotel:
            return f"The recommended hotel is {hotel['name']}, rated {hotel['rating']}, at EUR {hotel['price_per_night']} per night."
        return f"I found {len(results.get('hotels', []))} matching hotels so far."

    if "activit" in text or "things" in text or "tour" in text:
        activities = summary.get("activities") or optimized.get("activities") or results.get("activities", [])
        if activities:
            names = ", ".join(item["name"] for item in activities)
            return f"The current activity picks are: {names}."
        return "I have not found activities yet. Cultural, food, and leisure are available interests."

    if "itinerary" in text or "plan" in text or "day" in text:
        itinerary = summary.get("itinerary") or UI_STATE.get("itinerary") or []
        if itinerary:
            return "Here is the current day plan: " + " | ".join(itinerary)
        return "The itinerary is not ready yet. I will show it as soon as the itinerary agent finishes."

    if "help" in text or "what can" in text:
        return "You can ask about the destination, budget, flight, hotel, activities, or day-by-day itinerary."

    return "I can answer basic questions about your destination, budget, flight, hotel, activities, and itinerary."


async def status(request: web.Request) -> web.Response:
    return web.json_response(UI_STATE)


async def send_preferences(request: web.Request) -> web.Response:
    data = await request.json()
    preferences = {
        "scenario": data.get("scenario", "solo"),
        "destination": normalize_destination(data.get("destination", "Rome")),
        "days": int(data.get("days", 5)),
        "budget": int(data.get("budget", 1500)),
        "interests": parse_interests(data.get("interests", ["cultural", "food"])),
        "travel_style": data.get("travel_style", "flexible")
    }

    UI_STATE["preferences"] = preferences
    UI_STATE["scenario"] = preferences["scenario"]
    UI_STATE["preferences_sent"] = True
    chat_log("User", json.dumps(preferences))
    ui_log("System", "Received full preferences from user")
    set_stage("user input received")

    preference_agent = AGENTS.get("PreferenceAgent")
    if preference_agent is None:
        ui_log("System", "Preference agent not available")
        return web.json_response({"status": "error", "message": "Preference agent not available."}, status=500)

    preference_agent.add_behaviour(preference_agent.SendPreferencesBehaviour(preferences))
    set_stage("waiting for research")
    ui_log("PreferenceAgent", "Sent preferences to ResearchAgent")

    return web.json_response({"status": "ok"})


async def ask_question(request: web.Request) -> web.Response:
    data = await request.json()
    question = data.get("message", "").strip()
    if not question:
        return web.json_response({"status": "error", "message": "Question cannot be empty."}, status=400)

    chat_log("User", question)
    answer = assistant_answer(question)
    chat_log("Travel Assistant", answer)
    ui_log("Travel Assistant", f"Answered question: {question}")
    return web.json_response({"status": "ok", "answer": answer})


async def submit_answer(request: web.Request) -> web.Response:
    data = await request.json()
    answer = data.get("answer", "").strip()
    if not answer:
        return web.json_response({"status": "error", "message": "Answer cannot be empty."}, status=400)

    if UI_STATE.get("current_question") is None:
        return web.json_response({"status": "error", "message": "No question is active."}, status=400)

    UI_STATE["pending_user_answer"] = answer
    chat_log("User", answer)
    ui_log("System", f"User answered: {answer}")
    set_stage("processing user answer")

    return web.json_response({"status": "ok"})


async def index(request: web.Request) -> web.Response:
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Smart Travel Planner</title>
      <style>
        :root { --bg:#f7f4ed; --ink:#1d2528; --muted:#687477; --panel:#fff; --soft:#eef6f3; --line:#d8e2dc; --accent:#087f6d; --dark:#102a2d; --good:#168a57; --wait:#b58900; --bad:#b54d48; }
        * { box-sizing: border-box; }
        body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; margin:0; background:var(--bg); color:var(--ink); }
        header { background:var(--dark); color:white; padding:22px 28px; }
        header h1 { margin:0 0 6px; font-size:28px; }
        header p { margin:0; color:#d4e8e1; }
        .container { padding:20px; display:grid; gap:16px; max-width:1280px; margin:0 auto; }
        .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; box-shadow:0 1px 10px rgba(16,42,45,.07); margin:0; }
        .grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
        pre { white-space:pre-wrap; word-break:break-word; max-height:280px; overflow-y:auto; background:#122326; color:#e9f7f1; padding:12px; border-radius:8px; font-size:12px; }
        input { border:1px solid var(--line); border-radius:8px; min-height:42px; font:inherit; }
        button { border:0; border-radius:8px; min-height:42px; padding:0 14px; font:inherit; font-weight:700; background:var(--accent); color:white; cursor:pointer; }
        button:hover { filter:brightness(.92); }
        .status-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; }
        .running { background:var(--good); }
        .waiting { background:var(--wait); }
        .stopped { background:var(--bad); }
        .hero { display:grid; grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr); gap:16px; align-items:stretch; }
        .stage-pill { display:inline-flex; align-items:center; gap:8px; padding:8px 10px; background:var(--soft); color:var(--accent); border-radius:8px; font-weight:800; }
        .question-box { border-left:4px solid var(--accent); background:#e8fff6; padding:10px 12px; border-radius:8px; line-height:1.45; font-size:14px; }
        .composer { display:grid; grid-template-columns:1fr auto; gap:8px; margin-top:12px; }
        .metric-row { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
        .metric { background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:14px; }
        .metric span { display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
        .metric b { display:block; margin-top:5px; font-size:22px; }
        .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
        .chips button { min-height:34px; background:#dff3ed; color:#075f55; }
        .timeline { list-style:none; padding:0; margin:0; display:grid; gap:10px; }
        .timeline li { background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:11px; }
        .timeline b { color:var(--accent); margin-right:8px; }
        .chat-lines { height:430px; overflow:auto; display:flex; flex-direction:column; gap:10px; padding:12px; background:#f8fbf9; border:1px solid var(--line); border-radius:8px; margin-top:14px; }
        .msg { max-width:78%; padding:10px 12px; border-radius:8px; background:var(--soft); line-height:1.42; align-self:flex-start; }
        .msg.user { background:#102a2d; color:white; align-self:flex-end; }
        .msg.system { background:#fff7e8; color:#49351f; align-self:center; max-width:92%; }
        .msg strong { display:block; font-size:12px; color:var(--muted); margin-bottom:4px; }
        .msg.user strong { color:#b9d9d0; }
        @media (max-width:800px) { .hero,.metric-row,.composer { grid-template-columns:1fr; } }
      </style>
    </head>
    <body>
      <header>
        <h1>Smart Travel Planner</h1>
        <p>Five agents collaborate live: preferences, research, optimization, itinerary, and booking.</p>
      </header>
      <div class="container">
        <div class="hero">
        <div class="card">
          <h2>Conversation</h2>
          <p class="stage-pill">Stage: <span id="stage">...</span></p>
          <div class="chat-lines" id="chat_history">Loading conversation...</div>
          <h3>Agent is waiting for</h3>
          <div class="question-box" id="current_question">Waiting for question...</div>
          <form class="composer" id="answer_form">
            <input type="text" id="answer_input" placeholder="Type your message..." autocomplete="off" />
            <button type="submit">Send</button>
          </form>
          <div class="chips">
            <button type="button" data-ask="What destinations can you search?">Destinations</button>
            <button type="button" data-ask="What is my total cost?">Total cost</button>
            <button type="button" data-ask="Which hotel did you choose?">Hotel</button>
            <button type="button" data-ask="Show my itinerary">Itinerary</button>
          </div>
          <p id="answer_status"></p>
        </div>
        <div class="card">
          <h2>Trip Snapshot</h2>
          <div class="metric-row">
            <div class="metric"><span>Scenario</span><b id="scenario">...</b></div>
            <div class="metric"><span>Destination</span><b id="destination">Pending</b></div>
            <div class="metric"><span>Total Cost</span><b id="total_cost">Pending</b></div>
          </div>
        </div>
        </div>

        <div class="card grid">
          <div>
            <h3>Preferences</h3>
            <pre id="preferences">...</pre>
          </div>
          <div>
            <h3>Search results</h3>
            <pre id="search_results">...</pre>
          </div>
        </div>

        <div class="card grid">
          <div>
            <h3>Itinerary</h3>
            <ul class="timeline" id="itinerary">...</ul>
          </div>
          <div>
            <h3>Optimized plan</h3>
            <pre id="optimized_plan">...</pre>
          </div>
        </div>

        <div class="card">
          <h3>Final booking summary</h3>
          <pre id="booking_summary">Waiting for booking to complete...</pre>
        </div>

        <div class="card grid">
          <div>
            <h3>Agent status</h3>
            <div id="agent_status"></div>
          </div>
          <div>
            <h3>Chat behavior</h3>
            <p>During setup, short replies answer the active preference question. Questions like "what can you search?" are answered by the assistant in this same chat.</p>
          </div>
        </div>

        <div class="card">
          <h3>Logs</h3>
          <pre id="logs">Loading...</pre>
        </div>
      </div>

      <script>
        let latestState = null;

        function money(value) {
          return value === null || value === undefined ? 'pending' : 'EUR ' + value;
        }

        function escapeHtml(value) {
          return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
          }[char]));
        }

        function renderChat(items) {
          const chat = document.getElementById('chat_history');
          chat.innerHTML = (items || []).map(item => {
            const cls = item.sender === 'User' ? 'msg user' : item.sender === 'System' ? 'msg system' : 'msg';
            return `<div class="${cls}"><strong>${escapeHtml(item.time)} ${escapeHtml(item.sender)}</strong>${escapeHtml(item.message)}</div>`;
          }).join('');
          chat.scrollTop = chat.scrollHeight;
        }

        function looksLikeQuestion(text) {
          const value = text.trim().toLowerCase();
          return value.endsWith('?') || /^(what|which|who|where|when|why|how|can|could|do|does|is|are|show|tell|explain)\\b/.test(value);
        }

        function renderItinerary(items) {
          const list = document.getElementById('itinerary');
          if (!items || !items.length) {
            list.innerHTML = '<li><b>Pending</b>The itinerary agent will fill this after optimization.</li>';
            return;
          }
          list.innerHTML = items.map((line, index) => {
            return `<li><b>Day ${index + 1}</b>${escapeHtml(line.replace(/^Day\\s*\\d+\\s*:?\\s*/i, ''))}</li>`;
          }).join('');
        }
        async function refresh() {
          const response = await fetch('/status');
          const data = await response.json();
          latestState = data;
          const prefs = data.preferences || {};
          document.getElementById('scenario').textContent = data.scenario || 'unknown';
          document.getElementById('destination').textContent = prefs.destination || data.booking_summary.destination || 'Pending';
          document.getElementById('stage').textContent = data.stage;
          document.getElementById('total_cost').textContent = money(data.total_cost || data.optimized_plan.total_cost);
          document.getElementById('preferences').textContent = JSON.stringify(data.preferences || {}, null, 2);
          document.getElementById('search_results').textContent = JSON.stringify(data.search_results || {}, null, 2);
          document.getElementById('optimized_plan').textContent = JSON.stringify(data.optimized_plan || {}, null, 2);
          renderItinerary(data.itinerary || []);
          document.getElementById('booking_summary').textContent = JSON.stringify(data.booking_summary || {}, null, 2);
          document.getElementById('current_question').textContent = data.current_question || 'Planning is complete. Switch to Ask mode for questions about the trip.';
          renderChat(data.chat_history);
          document.getElementById('logs').textContent = (data.logs || []).join('\\n');

          const statusHtml = Object.entries(data.agents).map(([agent, state]) => {
            const cls = state === 'running' ? 'running' : state === 'waiting' ? 'waiting' : 'stopped';
            return `<div><span class='status-dot ${cls}'></span>${agent}: ${state}</div>`;
          }).join('');
          document.getElementById('agent_status').innerHTML = statusHtml;
        }

        function updateStatusBar(message) {
          const status = document.getElementById('answer_status');
          if (status) status.textContent = message;
        }

        window.addEventListener('DOMContentLoaded', () => {
          refresh().catch(error => updateStatusBar('Refresh failed: ' + error.message));
          setInterval(() => {
            refresh().catch(error => updateStatusBar('Refresh failed: ' + error.message));
          }, 1000);

          const input = document.getElementById('answer_input');
          document.getElementById('answer_form').addEventListener('submit', async (event) => {
            event.preventDefault();
            updateStatusBar('Sending...');
            const answer = input.value.trim();
            input.value = '';
            if (!answer) {
              updateStatusBar('');
              return;
            }
            try {
              const shouldAsk = !latestState || !latestState.current_question || looksLikeQuestion(answer);
              const res = await fetch(window.location.origin + (shouldAsk ? '/chat' : '/answer'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(shouldAsk ? { message: answer } : { answer })
              });
              if (!res.ok) {
                const text = await res.text();
                updateStatusBar('Error: ' + text);
                return;
              }
              const result = await res.json();
              updateStatusBar(result.status === 'ok' ? 'Sent' : 'Error');
              refresh().catch(error => updateStatusBar('Refresh failed: ' + error.message));
            } catch (error) {
              console.error('Send failed', error);
              updateStatusBar('Send failed');
            }
          });

          document.querySelectorAll('[data-ask]').forEach(button => {
            button.addEventListener('click', async () => {
              updateStatusBar('Asking...');
              try {
                const res = await fetch(window.location.origin + '/chat', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ message: button.dataset.ask })
                });
                if (!res.ok) {
                  updateStatusBar('Question failed');
                  return;
                }
                updateStatusBar('Answered');
                refresh().catch(error => updateStatusBar('Refresh failed: ' + error.message));
              } catch (error) {
                console.error('Question failed', error);
                updateStatusBar('Question failed');
              }
            });
          });
        });
      </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


def create_web_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/status', status),
        web.post('/preferences', send_preferences),
        web.post('/answer', submit_answer),
        web.post('/chat', ask_question),
    ])
    return app

# ─────────────────────────────────────────────
# PREFERENCE AGENT
# ─────────────────────────────────────────────
class PreferenceAgent(Agent):

    class SendPreferencesBehaviour(OneShotBehaviour):
        def __init__(self, preferences):
            super().__init__()
            self.preferences = preferences

        async def run(self):
            preferences = self.preferences
            print(f"\n[PreferenceAgent] Building profile for: {preferences['scenario'].upper()}")
            print(f"[PreferenceAgent] Destination: {preferences['destination']} | "
                  f"Budget: €{preferences['budget']} | Days: {preferences['days']}")

            UI_STATE["preferences"] = preferences
            ui_log("PreferenceAgent", "Preferences collected")

            msg = Message(to=f"research_agent@{SERVER}")
            msg.set_metadata("performative", "request")
            msg.set_metadata("sender",       "PreferenceAgent")
            msg.body = json.dumps(preferences)
            await self.send(msg)
            print("[PreferenceAgent] ✅ REQUEST sent to ResearchAgent.\n")
            ui_log("PreferenceAgent", "Request sent to ResearchAgent")
            set_stage("waiting for research")

    class PromptForPreferences(OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(2)
            self.agent.questions = [
                {"field": "scenario", "text": "Which travel scenario do you want? (solo or family)"},
                {"field": "destination", "text": f"Where would you like to travel? Options: {', '.join(AVAILABLE_DESTINATIONS)}"},
                {"field": "days", "text": "How many days will the trip last?"},
                {"field": "budget", "text": "What is your total budget in euros?"},
                {"field": "interests", "text": f"What are your interests? Options: {', '.join(AVAILABLE_INTERESTS)}. List them separated by commas."},
                {"field": "travel_style", "text": "What travel style do you prefer? (e.g. flexible, relaxed)"},
            ]
            self.agent.question_index = 0
            UI_STATE["preferences_answers"] = {}
            UI_STATE["pending_user_answer"] = None
            UI_STATE["current_question"] = self.agent.questions[0]["text"]
            chat_log("PreferenceAgent", "Hello! I will ask you a few travel questions. Please answer them one by one.")
            chat_log("PreferenceAgent", UI_STATE["current_question"])
            set_stage("waiting for user input")

    class WaitForUserInput(CyclicBehaviour):
        async def run(self):
            answer = UI_STATE.get("pending_user_answer")
            if not answer:
                return
            UI_STATE["pending_user_answer"] = None
            index = getattr(self.agent, "question_index", 0)
            question = self.agent.questions[index]
            field = question["field"]
            value = answer
            if field == "days" or field == "budget":
                try:
                    value = int(answer)
                except ValueError:
                    UI_STATE["current_question"] = f"Please enter a valid number for {field}."
                    chat_log("PreferenceAgent", UI_STATE["current_question"])
                    set_stage("waiting for valid input")
                    return
                if value <= 0:
                    UI_STATE["current_question"] = f"Please enter a {field} value greater than zero."
                    chat_log("PreferenceAgent", UI_STATE["current_question"])
                    set_stage("waiting for valid input")
                    return
            elif field == "interests":
                value = parse_interests(answer)
            elif field == "destination":
                value = normalize_destination(answer)
                if value not in AVAILABLE_DESTINATIONS:
                    UI_STATE["current_question"] = (
                        "I can currently search Rome, Florence, Paris, or Barcelona. "
                        "Which one should I use?"
                    )
                    chat_log("PreferenceAgent", UI_STATE["current_question"])
                    set_stage("waiting for valid input")
                    return
            elif field == "scenario":
                normalized = answer.lower()
                if normalized not in ["solo", "family"]:
                    UI_STATE["current_question"] = "Please answer 'solo' or 'family'."
                    chat_log("PreferenceAgent", UI_STATE["current_question"])
                    set_stage("waiting for valid input")
                    return
                value = normalized

            UI_STATE["preferences_answers"][field] = value
            ui_log("PreferenceAgent", f"Received answer for {field}")
            self.agent.question_index = index + 1

            if self.agent.question_index >= len(self.agent.questions):
                preferences = UI_STATE["preferences_answers"].copy()
                UI_STATE["preferences"] = preferences
                UI_STATE["scenario"] = preferences.get("scenario", UI_STATE["scenario"])
                UI_STATE["preferences_sent"] = True
                UI_STATE["current_question"] = None
                chat_log("PreferenceAgent", "Thank you! Searching travel options now.")
                self.agent.add_behaviour(self.agent.SendPreferencesBehaviour(preferences))
            else:
                next_question = self.agent.questions[self.agent.question_index]["text"]
                UI_STATE["current_question"] = next_question
                chat_log("PreferenceAgent", next_question)
                set_stage("waiting for user input")

    async def setup(self):
        print("[PreferenceAgent] Agent started.")
        self.add_behaviour(self.PromptForPreferences())
        self.add_behaviour(self.WaitForUserInput())


# ─────────────────────────────────────────────
# RESEARCH AGENT
# ─────────────────────────────────────────────
class ResearchAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if not msg:
                return
            if msg.get_metadata("performative") != "request":
                return

            prefs     = json.loads(msg.body)
            dest      = prefs["destination"]
            budget    = prefs["budget"]
            interests = prefs["interests"]
            is_family = prefs["scenario"] == "family"
            sender    = msg.get_metadata("sender")
            set_stage("researching options")

            print(f"\n[ResearchAgent] REQUEST from {sender} → {dest} | €{budget}")

            # AUTONOMOUS DECISION: filter options based on scenario type
            flights = [f for f in FLIGHTS
                       if f["to"] == dest and f["price"] < budget * 0.25]

            hotels  = [h for h in HOTELS
                       if h["city"] == dest and
                       (not is_family or h["family_friendly"])]

            activities = [a for a in ACTIVITIES
                          if a["city"] == dest and
                          a["type"] in interests and
                          (not is_family or a["family_friendly"])]

            print(f"[ResearchAgent] Found: {len(flights)} flights | "
                  f"{len(hotels)} hotels | {len(activities)} activities")
            UI_STATE["search_results"] = {
                "flights": flights,
                "hotels": hotels,
                "activities": activities
            }
            ui_log("ResearchAgent", f"Search returned {len(flights)} flights, {len(hotels)} hotels, {len(activities)} activities")

            reply = Message(to=f"optimizer_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "ResearchAgent")
            reply.body = json.dumps({
                "preferences": prefs,
                "flights":     flights,
                "hotels":      hotels,
                "activities":  activities
            })
            await self.send(reply)
            print("[ResearchAgent] ✅ INFORM sent to OptimizerAgent.\n")

    async def setup(self):
        print("[ResearchAgent] Agent started.")
        t = Template()
        t.set_metadata("performative", "request")
        self.add_behaviour(self.Listen(), t)


# ─────────────────────────────────────────────
# OPTIMIZER AGENT
# ─────────────────────────────────────────────
class OptimizerAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if not msg:
                return
            if msg.get_metadata("performative") != "inform":
                return

            data       = json.loads(msg.body)
            prefs      = data["preferences"]
            flights    = data["flights"]
            hotels     = data["hotels"]
            activities = data["activities"]
            budget     = prefs["budget"]
            sender     = msg.get_metadata("sender")
            set_stage("optimizing plan")

            print(f"\n[OptimizerAgent] INFORM from {sender} | Budget: €{budget}")

            if not flights or not hotels:
                print("[OptimizerAgent] ❌ No valid options. Sending FAILURE.")
                ui_log("OptimizerAgent", "No valid flights or hotels available")
                fail = Message(to=f"booking_agent@{SERVER}")
                fail.set_metadata("performative", "failure")
                fail.set_metadata("sender",       "OptimizerAgent")
                fail.body = json.dumps({"reason": "No valid flights or hotels."})
                await self.send(fail)
                return

            # AUTONOMOUS DECISION: score and select best combination
            best_flight    = min(flights,    key=lambda f: f["price"])
            best_hotel     = max(hotels,     key=lambda h: h["rating"])
            top_activities = activities[:2]

            total = (best_flight["price"] +
                     best_hotel["price_per_night"] * prefs["days"] +
                     sum(a["price"] for a in top_activities))

            print(f"[OptimizerAgent] Best: {best_flight['airline']} + "
                  f"{best_hotel['name']} = €{total}")
            UI_STATE["optimized_plan"] = {
                "best_flight": best_flight,
                "best_hotel": best_hotel,
                "activities": top_activities,
                "total_cost": total
            }
            ui_log("OptimizerAgent", f"Selected plan total €{total}")

            if total > budget:
                # FEEDBACK LOOP: send REQUEST back to Research Agent
                print(f"[OptimizerAgent] ⚠️ €{total} exceeds €{budget}. "
                      f"Requesting broader search (+20% budget)...")
                ui_log("OptimizerAgent", "Over budget, requesting broader search")
                new_prefs = prefs.copy()
                new_prefs["budget"] = int(budget * 1.2)
                feedback = Message(to=f"research_agent@{SERVER}")
                feedback.set_metadata("performative", "request")
                feedback.set_metadata("sender",       "OptimizerAgent")
                feedback.body = json.dumps(new_prefs)
                await self.send(feedback)
                return

            print(f"[OptimizerAgent] ✅ Plan selected. Total: €{total}")

            reply = Message(to=f"itinerary_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "OptimizerAgent")
            reply.body = json.dumps({
                "preferences": prefs,
                "best_flight": best_flight,
                "best_hotel":  best_hotel,
                "activities":  top_activities,
                "total_cost":  total
            })
            await self.send(reply)
            print("[OptimizerAgent] ✅ INFORM sent to ItineraryAgent.\n")

    async def setup(self):
        print("[OptimizerAgent] Agent started.")
        t = Template()
        t.set_metadata("performative", "inform")
        self.add_behaviour(self.Listen(), t)


# ─────────────────────────────────────────────
# ITINERARY AGENT
# ─────────────────────────────────────────────
class ItineraryAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if not msg:
                return
            if msg.get_metadata("performative") != "inform":
                return

            data      = json.loads(msg.body)
            prefs     = data["preferences"]
            flight    = data["best_flight"]
            hotel     = data["best_hotel"]
            acts      = data["activities"]
            days      = prefs["days"]
            is_family = prefs["scenario"] == "family"
            sender    = msg.get_metadata("sender")

            set_stage("building itinerary")
            print(f"\n[ItineraryAgent] INFORM from {sender}.")
            print(f"[ItineraryAgent] Building {days}-day plan "
                  f"({'family pace' if is_family else 'flexible pace'})...")

            # AUTONOMOUS DECISION: adjust pacing based on scenario
            itinerary = [
                f"Day 1 : ✈ Fly {flight['airline']} ({flight['duration']}) "
                f"→ Check in at {hotel['name']}"
            ]
            for day in range(2, days):
                act  = acts[(day-2) % len(acts)]["name"] if acts else "Free time"
                rest = "  [Rest included]" if is_family else ""
                itinerary.append(f"Day {day} : 🎯 {act}{rest}")
            itinerary.append(f"Day {days} : 🏠 Checkout & Return flight")
            UI_STATE["itinerary"] = itinerary
            ui_log("ItineraryAgent", "Itinerary created")

            reply = Message(to=f"booking_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "ItineraryAgent")
            reply.body = json.dumps({
                "preferences": prefs,
                "flight":      flight,
                "hotel":       hotel,
                "activities":  acts,
                "itinerary":   itinerary,
                "total_cost":  data["total_cost"]
            })
            await self.send(reply)
            print("[ItineraryAgent] ✅ INFORM sent to BookingAgent.\n")

    async def setup(self):
        print("[ItineraryAgent] Agent started.")
        t = Template()
        t.set_metadata("performative", "inform")
        self.add_behaviour(self.Listen(), t)


# ─────────────────────────────────────────────
# BOOKING AGENT
# ─────────────────────────────────────────────
class BookingAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if not msg:
                return

            perf = msg.get_metadata("performative")

            if perf == "failure":
                reason = json.loads(msg.body)["reason"]
                print(f"\n[BookingAgent] ❌ FAILURE: {reason}")
                set_agent_status("BookingAgent", "stopped")
                set_stage("failed")
                ui_log("BookingAgent", reason)
                await self.agent.stop()
                return

            if perf == "inform":
                data  = json.loads(msg.body)
                prefs = data["preferences"]
                set_stage("preparing booking summary")

                print("\n" + "═"*57)
                print("   ✈️   SMART TRAVEL PLANNER — BOOKING SUMMARY")
                print("═"*57)
                print(f"  Scenario    : {prefs['scenario'].upper()}")
                print(f"  Destination : {prefs['destination']}")
                print(f"  Duration    : {prefs['days']} days")
                print(f"  Travel Style: {prefs['travel_style'].capitalize()}")
                print(f"  Total Cost  : €{data['total_cost']}")
                print("─"*57)
                print(f"  ✈  Flight : {data['flight']['airline']} "
                      f"({data['flight']['duration']}) "
                      f"— €{data['flight']['price']}")
                print(f"  🏨 Hotel  : {data['hotel']['name']} "
                      f"— €{data['hotel']['price_per_night']}/night "
                      f"⭐ {data['hotel']['rating']}")
                print("  🎯 Activities:")
                for a in data["activities"]:
                    print(f"       • {a['name']} (€{a['price']})")
                print("─"*57)
                print("  📅 Itinerary:")
                for line in data["itinerary"]:
                    print(f"       {line}")
                print("═"*57)
                print("  ✅ Booking recommendations ready for the user!")
                print("═"*57 + "\n")
                UI_STATE["total_cost"] = data["total_cost"]
                UI_STATE["booking_summary"] = {
                    "scenario": prefs["scenario"],
                    "destination": prefs["destination"],
                    "days": prefs["days"],
                    "travel_style": prefs["travel_style"],
                    "flight": data["flight"],
                    "hotel": data["hotel"],
                    "activities": data["activities"],
                    "itinerary": data["itinerary"],
                    "total_cost": data["total_cost"]
                }
                set_stage("completed")
                ui_log("BookingAgent", "Booking summary ready")
                chat_log("BookingAgent", "Your itinerary and booking recommendations are ready. You can ask me about the cost, hotel, flight, activities, or day-by-day plan.")
                set_agent_status("BookingAgent", "stopped")
                await self.agent.stop()

    async def setup(self):
        print("[BookingAgent] Agent started.")
        self.add_behaviour(self.Listen())


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def main():
    scenario = "solo"
    if len(sys.argv) > 1 and sys.argv[1] == "family":
        scenario = "family"

    UI_STATE["scenario"] = scenario
    set_stage("initializing")

    print("═"*57)
    print(f"   🌍 SMART TRAVEL PLANNER  (scenario: {scenario.upper()})")
    print("═"*57)

    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 10001)
    await site.start()
    ui_log("System", "Web dashboard started on http://localhost:10001")
    set_stage("starting agents")

    # Create all agents
    booking   = BookingAgent(  f"booking_agent@{SERVER}",   PASSWORD, verify_security=False)
    itinerary = ItineraryAgent(f"itinerary_agent@{SERVER}", PASSWORD, verify_security=False)
    optimizer = OptimizerAgent(f"optimizer_agent@{SERVER}", PASSWORD, verify_security=False)
    research  = ResearchAgent( f"research_agent@{SERVER}",  PASSWORD, verify_security=False)
    preference = PreferenceAgent(f"preference_agent@{SERVER}", PASSWORD, verify_security=False)
    preference.scenario = scenario

    AGENTS["PreferenceAgent"] = preference

    # Start listener agents first, then the trigger agent
    await booking.start(auto_register=True)
    ui_log("BookingAgent", "started")
    set_agent_status("BookingAgent", "running")

    await itinerary.start(auto_register=True)
    ui_log("ItineraryAgent", "started")
    set_agent_status("ItineraryAgent", "running")

    await optimizer.start(auto_register=True)
    ui_log("OptimizerAgent", "started")
    set_agent_status("OptimizerAgent", "running")

    await research.start(auto_register=True)
    ui_log("ResearchAgent", "started")
    set_agent_status("ResearchAgent", "running")

    await preference.start(auto_register=True)
    ui_log("PreferenceAgent", "started")
    set_agent_status("PreferenceAgent", "running")
    set_stage("waiting for user input")

    chat_log("PreferenceAgent", "I need your preferences before I can search the mock data.")
    print("\n[System] All 5 agents running. Waiting for user input.\n")

   # Wait for booking agent to finish
    while booking.is_alive():
        await asyncio.sleep(1)

    set_stage("completed")
    ui_log("System", "Booking complete. You can close the browser when ready.")
    print("\n🎉 Booking complete. Visit http://localhost:10001 to view the dashboard.")
    print("   Press Ctrl+C when done.\n")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    await preference.stop()
    await research.stop()
    await optimizer.stop()
    await itinerary.stop()
    await runner.cleanup()
    print("[System] All agents stopped. MAS complete.\n")


if __name__ == "__main__":
    run_container(main(), embedded_xmpp_server=True)
