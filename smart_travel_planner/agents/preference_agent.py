"""
PreferenceAgent
───────────────
Responsibilities:
  • Ask the user a structured sequence of travel-preference questions via chat.
  • Validate every answer (type checks, allowed-value checks, range checks).
  • Assemble the validated preferences dict and send a REQUEST to ResearchAgent.
  • Accept pre-filled preferences from the /preferences HTTP endpoint (skips Q&A).

Autonomous decisions:
  • Rejects out-of-range budgets / days and re-prompts.
  • Normalises free-text destinations to the canonical form in AVAILABLE_DESTINATIONS.
  • Normalises interest tags to lowercase and deduplicates them.
"""

import json
import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message

from data.mock_data import FLIGHTS, ACTIVITIES
from web.dashboard import (
    UI_STATE, ui_log, chat_log, set_stage,
    set_agent_status, SERVER
)

AVAILABLE_DESTINATIONS = sorted({item["to"] for item in FLIGHTS})
AVAILABLE_INTERESTS    = sorted({item["type"] for item in ACTIVITIES})

QUESTIONS = [
    {
        "field": "scenario",
        "text": "Which travel scenario do you want? (solo or family)",
        "allowed": ["solo", "family"],
        "error": "Please answer 'solo' or 'family'.",
    },
    {
        "field": "destination",
        "text": f"Where would you like to travel? Available: {', '.join(AVAILABLE_DESTINATIONS)}",
        "allowed": AVAILABLE_DESTINATIONS,
        "error": f"I can search {', '.join(AVAILABLE_DESTINATIONS)}. Which one?",
    },
    {
        "field": "days",
        "text": "How many days will the trip last? (2–14)",
        "type": "int",
        "min": 2,
        "max": 14,
        "error": "Please enter a whole number between 2 and 14.",
    },
    {
        "field": "budget",
        "text": "What is your total budget in euros? (e.g. 1500)",
        "type": "int",
        "min": 200,
        "max": 50000,
        "error": "Please enter a budget between €200 and €50 000.",
    },
    {
        "field": "interests",
        "text": f"What are your interests? Options: {', '.join(AVAILABLE_INTERESTS)}. Separate with commas.",
        "type": "list",
        "allowed": AVAILABLE_INTERESTS,
    },
    {
        "field": "travel_style",
        "text": "What travel style do you prefer? (e.g. flexible, relaxed, adventure)",
    },
]


def _normalize_destination(value: str) -> str:
    v = (value or "").strip()
    for opt in AVAILABLE_DESTINATIONS:
        if opt.lower() == v.lower():
            return opt
    return v.title()


def _parse_interests(value) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = str(value or "").replace(" and ", ",").split(",")
    seen = []
    for item in items:
        tag = item.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen or ["cultural"]


def _validate(q: dict, raw: str):
    """
    Validate a raw string answer against question spec.
    Returns (parsed_value, error_message_or_None).
    """
    field = q["field"]
    typ   = q.get("type")

    if typ == "int":
        try:
            val = int(raw.strip())
        except ValueError:
            return None, q["error"]
        lo, hi = q.get("min", 1), q.get("max", 10**9)
        if not (lo <= val <= hi):
            return None, q["error"]
        return val, None

    if typ == "list":
        tags = _parse_interests(raw)
        allowed = q.get("allowed", [])
        valid   = [t for t in tags if t in allowed]
        if not valid:
            valid = ["cultural"]          # graceful fallback
        return valid, None

    if field == "destination":
        norm = _normalize_destination(raw)
        if norm not in AVAILABLE_DESTINATIONS:
            return None, q["error"]
        return norm, None

    if field == "scenario":
        v = raw.strip().lower()
        if v not in q["allowed"]:
            return None, q["error"]
        return v, None

    return raw.strip(), None


class PreferenceAgent(Agent):

    # ── Public shortcut: called by the /preferences HTTP handler ────────────
    class SendPreferencesBehaviour(OneShotBehaviour):
        def __init__(self, preferences: dict):
            super().__init__()
            self.preferences = preferences

        async def run(self):
            prefs = self.preferences
            print(
                f"\n[PreferenceAgent] Profile → {prefs['scenario'].upper()} | "
                f"{prefs['destination']} | €{prefs['budget']} | {prefs['days']} days"
            )
            UI_STATE["preferences"] = prefs
            ui_log("PreferenceAgent", "Preferences collected and dispatched")

            msg = Message(to=f"research_agent@{SERVER}")
            msg.set_metadata("performative", "request")
            msg.set_metadata("sender",       "PreferenceAgent")
            msg.body = json.dumps(prefs)
            await self.send(msg)

            print("[PreferenceAgent] ✅ REQUEST → ResearchAgent")
            ui_log("PreferenceAgent", "REQUEST sent to ResearchAgent")
            set_stage("waiting for research")

    # ── Interactive Q&A ─────────────────────────────────────────────────────
    class PromptForPreferences(OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(1.5)
            self.agent.q_index = 0
            self.agent.answers  = {}
            q_text = QUESTIONS[0]["text"]
            UI_STATE["current_question"] = q_text
            chat_log("PreferenceAgent",
                     "Hello! I'll ask you a few questions to plan your perfect trip. "
                     "You can also use the form on the right to submit all preferences at once.")
            chat_log("PreferenceAgent", q_text)
            set_stage("waiting for user input")

    class WaitForUserInput(CyclicBehaviour):
        async def run(self):
            raw = UI_STATE.get("pending_user_answer")
            if not raw:
                await asyncio.sleep(0.3)
                return

            UI_STATE["pending_user_answer"] = None
            idx = getattr(self.agent, "q_index", 0)
            if idx >= len(QUESTIONS):
                return                      # already done

            q = QUESTIONS[idx]
            value, err = _validate(q, raw)

            if err:
                UI_STATE["current_question"] = err
                chat_log("PreferenceAgent", err)
                set_stage("waiting for valid input")
                return

            self.agent.answers[q["field"]] = value
            ui_log("PreferenceAgent", f"Accepted {q['field']} = {value!r}")
            self.agent.q_index += 1

            if self.agent.q_index >= len(QUESTIONS):
                prefs = dict(self.agent.answers)
                UI_STATE["preferences"]      = prefs
                UI_STATE["scenario"]         = prefs.get("scenario", UI_STATE["scenario"])
                UI_STATE["preferences_sent"] = True
                UI_STATE["current_question"] = None
                chat_log("PreferenceAgent",
                         "Thank you! I now have everything I need — searching options now…")
                self.agent.add_behaviour(
                    PreferenceAgent.SendPreferencesBehaviour(prefs)
                )
            else:
                nxt = QUESTIONS[self.agent.q_index]["text"]
                UI_STATE["current_question"] = nxt
                chat_log("PreferenceAgent", nxt)
                set_stage("waiting for user input")

    async def setup(self):
        print("[PreferenceAgent] Agent started.")
        set_agent_status("PreferenceAgent", "running")
        self.add_behaviour(self.PromptForPreferences())
        self.add_behaviour(self.WaitForUserInput())