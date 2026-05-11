"""
BookingAgent
────────────
Responsibilities:
  • Listen for INFORM (success) or FAILURE messages from ItineraryAgent /
    OptimizerAgent.
  • On INFORM: assemble and persist the full booking summary, print the
    console report, and mark the pipeline as complete.
  • On FAILURE: log the reason and mark the pipeline as failed.

Autonomous decisions:
  • Determines whether the trip is within budget and adds a budget status
    note to the summary.
  • Formats the console summary differently for solo vs family scenarios.
"""

import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from web.dashboard import (
    UI_STATE, ui_log, chat_log, set_stage, set_agent_status
)


def _console_report(data: dict, prefs: dict) -> None:
    """Print a nicely formatted booking summary to stdout."""
    is_family = prefs["scenario"] == "family"
    sep = "═" * 60

    print(f"\n{sep}")
    print("   ✈️   SMART TRAVEL PLANNER — BOOKING SUMMARY")
    print(sep)
    print(f"  Scenario     : {prefs['scenario'].upper()}")
    print(f"  Destination  : {prefs['destination']}")
    print(f"  Duration     : {prefs['days']} days")
    print(f"  Travel Style : {prefs.get('travel_style', 'flexible').capitalize()}")
    print(f"  Budget       : €{prefs['budget']}")
    print(f"  Total Cost   : €{data['total_cost']}")
    budget_note = (
        "✅ Within budget"
        if data["total_cost"] <= prefs["budget"]
        else f"⚠️  €{data['total_cost'] - prefs['budget']} over budget (best available)"
    )
    print(f"  Budget status: {budget_note}")
    print("─" * 60)

    f = data["flight"]
    print(f"  ✈  Flight  : {f['airline']} {f.get('flight_number','')} "
          f"({f['duration']}) — €{f['price']}")

    h = data["hotel"]
    print(f"  🏨 Hotel   : {h['name']} ({h.get('area','')}) "
          f"— €{h['price_per_night']}/night ⭐ {h['rating']} "
          f"{'👨‍👩‍👧 family-friendly' if is_family else ''}")

    print("  🎯 Activities:")
    for a in data["activities"]:
        fam = "  👨‍👩‍👧" if is_family and a.get("family_friendly") else ""
        print(f"       • {a['name']} (€{a['price']}){fam}")

    print("─" * 60)
    print("  📅 Day-by-Day Itinerary:")
    for i, line in enumerate(data["itinerary"], 1):
        print(f"     Day {i:>2}: {line}")

    print(sep)
    print("  ✅ Booking recommendations ready!")
    print(sep + "\n")


class BookingAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if msg is None:
                return

            perf = msg.get_metadata("performative")

            # ── FAILURE path ───────────────────────────────────────────
            if perf == "failure":
                reason = json.loads(msg.body).get("reason", "Unknown error")
                print(f"\n[BookingAgent] ❌ FAILURE: {reason}")
                ui_log("BookingAgent", f"Planning failed: {reason}")
                chat_log("BookingAgent",
                         f"Sorry, I could not build a plan: {reason} "
                         "Please try adjusting your budget or destination.")
                set_stage("failed")
                set_agent_status("BookingAgent", "stopped")
                await self.agent.stop()
                return

            # ── SUCCESS path ───────────────────────────────────────────
            if perf == "inform":
                data  = json.loads(msg.body)
                prefs = data["preferences"]

                set_stage("finalising booking")
                _console_report(data, prefs)

                budget_ok = data["total_cost"] <= prefs["budget"]
                UI_STATE["total_cost"] = data["total_cost"]
                UI_STATE["booking_summary"] = {
                    "scenario":     prefs["scenario"],
                    "destination":  prefs["destination"],
                    "days":         prefs["days"],
                    "travel_style": prefs.get("travel_style", "flexible"),
                    "budget":       prefs["budget"],
                    "budget_ok":    budget_ok,
                    "flight":       data["flight"],
                    "hotel":        data["hotel"],
                    "activities":   data["activities"],
                    "itinerary":    data["itinerary"],
                    "total_cost":   data["total_cost"],
                }

                set_stage("completed")
                ui_log("BookingAgent", "Booking summary ready — pipeline complete")
                chat_log(
                    "BookingAgent",
                    "🎉 Your personalised itinerary is ready! "
                    "You can ask me about the cost, hotel, flight, activities, "
                    "or any day of the plan."
                )
                set_agent_status("BookingAgent", "stopped")
                await self.agent.stop()

    async def setup(self):
        print("[BookingAgent] Agent started.")
        set_agent_status("BookingAgent", "running")
        self.add_behaviour(self.Listen())