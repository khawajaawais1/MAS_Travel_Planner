"""
ResearchAgent
─────────────
Responsibilities:
  • Listen for REQUEST messages (from PreferenceAgent or OptimizerAgent).
  • Filter FLIGHTS, HOTELS, and ACTIVITIES from mock data to match preferences.
  • Send an INFORM to OptimizerAgent with the filtered candidates.

Autonomous decisions:
  • Uses a budget ceiling of 25 % of total budget for flights.
  • Excludes non-family-friendly options when scenario == "family".
  • Matches activities whose type appears in the traveller's interests list.
  • On a re-search request from OptimizerAgent the new (relaxed) budget
    is used automatically — no further orchestration needed.
"""

import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

from data.mock_data import FLIGHTS, HOTELS, ACTIVITIES
from web.dashboard import (
    UI_STATE, ui_log, set_stage, set_agent_status, SERVER
)


class ResearchAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if msg is None:
                return
            if msg.get_metadata("performative") != "request":
                return

            prefs     = json.loads(msg.body)
            dest      = prefs["destination"]
            budget    = prefs["budget"]
            interests = prefs.get("interests", ["cultural"])
            is_family = prefs.get("scenario") == "family"
            sender    = msg.get_metadata("sender") or "unknown"

            set_stage("researching options")
            print(
                f"\n[ResearchAgent] REQUEST from {sender} → "
                f"{dest} | €{budget} | interests: {interests}"
            )

            # ── Autonomous filtering ──────────────────────────────────────
            flight_budget = budget * 0.25

            flights = [
                f for f in FLIGHTS
                if f["to"] == dest and f["price"] <= flight_budget
            ]

            hotels = [
                h for h in HOTELS
                if h["city"] == dest and
                (not is_family or h["family_friendly"])
            ]

            activities = [
                a for a in ACTIVITIES
                if a["city"] == dest
                and a["type"] in interests
                and (not is_family or a["family_friendly"])
            ]

            print(
                f"[ResearchAgent] Results: {len(flights)} flights | "
                f"{len(hotels)} hotels | {len(activities)} activities"
            )
            ui_log(
                "ResearchAgent",
                f"Found {len(flights)} flights, {len(hotels)} hotels, "
                f"{len(activities)} activities for {dest}"
            )

            UI_STATE["search_results"] = {
                "flights":    flights,
                "hotels":     hotels,
                "activities": activities,
            }

            reply = Message(to=f"optimizer_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "ResearchAgent")
            reply.body = json.dumps(
                {
                    "preferences": prefs,
                    "flights":     flights,
                    "hotels":      hotels,
                    "activities":  activities,
                }
            )
            await self.send(reply)
            print("[ResearchAgent] ✅ INFORM → OptimizerAgent")

    async def setup(self):
        print("[ResearchAgent] Agent started.")
        set_agent_status("ResearchAgent", "running")
        t = Template()
        t.set_metadata("performative", "request")
        self.add_behaviour(self.Listen(), t)