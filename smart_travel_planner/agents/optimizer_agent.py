"""
OptimizerAgent
──────────────
Responsibilities:
  • Receive INFORM from ResearchAgent with candidate flights/hotels/activities.
  • Score and select the best combination within the traveller's budget.
  • If over budget, send a REQUEST back to ResearchAgent with a relaxed budget
    (feedback loop, up to MAX_RETRIES times).
  • Send INFORM to ItineraryAgent with the chosen plan.
  • Send FAILURE to BookingAgent when no valid options are found after retries.

Autonomous decisions:
  • Best flight  = cheapest (minimises cost headroom for hotel + activities).
  • Best hotel   = highest rating within budget constraint.
  • Activities   = scored by (price efficiency = value/price); top N selected
                   where N = min(days-1, len(available)) so every day is unique.
  • Budget check = if total > budget → relax budget by +20 % and re-search
                   (up to MAX_RETRIES = 2 times before giving up).
"""

import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

from web.dashboard import (
    UI_STATE, ui_log, set_stage, set_agent_status, SERVER
)

MAX_RETRIES = 2


def _score_activity(a: dict) -> float:
    """Higher is better — cheap + rated activities first."""
    price = max(a.get("price", 1), 1)
    # Use a simple value-for-money heuristic (flat rating proxy since we
    # don't store per-activity ratings; shorter duration = more flexible)
    duration_hours = float(str(a.get("duration", "2h")).replace("h", "").split()[0])
    return duration_hours / price          # more hours per euro = higher rank


class OptimizerAgent(Agent):

    class Listen(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self._retry_count = 0

        async def run(self):
            msg = await self.receive(timeout=60)
            if msg is None:
                return
            if msg.get_metadata("performative") != "inform":
                return

            data       = json.loads(msg.body)
            prefs      = data["preferences"]
            flights    = data["flights"]
            hotels     = data["hotels"]
            activities = data["activities"]
            budget     = prefs["budget"]
            days       = prefs["days"]
            sender     = msg.get_metadata("sender") or "unknown"

            set_stage("optimizing plan")
            print(
                f"\n[OptimizerAgent] INFORM from {sender} | "
                f"Budget €{budget} | {len(flights)}f {len(hotels)}h {len(activities)}a"
            )

            # ── Guard: nothing to work with ────────────────────────────
            if not flights or not hotels:
                reason = (
                    "No flights found within budget." if not flights
                    else "No suitable hotels found."
                )
                print(f"[OptimizerAgent] ❌ {reason}")
                ui_log("OptimizerAgent", reason)
                await self._send_failure(reason)
                return

            # ── Autonomous selection ───────────────────────────────────
            best_flight = min(flights, key=lambda f: f["price"])
            best_hotel  = max(hotels,  key=lambda h: h["rating"])

            # How many activity slots do we need?
            # Day 1 = arrival, Day N = departure → interior days need activities.
            # We want enough unique activities to cover every interior day.
            # If interests return fewer activities than needed, we pad with
            # any remaining activities for that city (already pre-filtered).
            interior_days  = max(days - 2, 1)
            sorted_acts    = sorted(activities, key=_score_activity, reverse=True)

            # Deduplicate by name just in case
            seen_names, unique_acts = set(), []
            for a in sorted_acts:
                if a["name"] not in seen_names:
                    seen_names.add(a["name"])
                    unique_acts.append(a)

            top_activities = unique_acts[:interior_days]

            hotel_total    = best_hotel["price_per_night"] * days
            activity_total = sum(a["price"] for a in top_activities)
            total          = best_flight["price"] + hotel_total + activity_total

            print(
                f"[OptimizerAgent] Candidate: {best_flight['airline']} + "
                f"{best_hotel['name']} + {len(top_activities)} activities = €{total}"
            )

            # ── Budget check / feedback loop ───────────────────────────
            if total > budget:
                if self._retry_count < MAX_RETRIES:
                    self._retry_count += 1
                    new_budget = int(budget * 1.2)
                    print(
                        f"[OptimizerAgent] ⚠️  Over budget by €{total - budget}. "
                        f"Retry {self._retry_count}/{MAX_RETRIES} with €{new_budget}"
                    )
                    ui_log(
                        "OptimizerAgent",
                        f"Over budget (€{total} > €{budget}), "
                        f"requesting re-search with €{new_budget}"
                    )
                    new_prefs = {**prefs, "budget": new_budget}
                    feedback  = Message(to=f"research_agent@{SERVER}")
                    feedback.set_metadata("performative", "request")
                    feedback.set_metadata("sender",       "OptimizerAgent")
                    feedback.body = json.dumps(new_prefs)
                    await self.send(feedback)
                    return
                else:
                    # Accept the cheapest plan even if slightly over
                    print(
                        f"[OptimizerAgent] ⚠️  Still €{total - budget} over budget "
                        f"after {MAX_RETRIES} retries — accepting best available."
                    )
                    ui_log(
                        "OptimizerAgent",
                        f"Accepted over-budget plan €{total} (best available)"
                    )

            self._retry_count = 0          # reset for any future re-use

            UI_STATE["optimized_plan"] = {
                "best_flight": best_flight,
                "best_hotel":  best_hotel,
                "activities":  top_activities,
                "total_cost":  total,
            }
            ui_log("OptimizerAgent", f"Plan selected — total €{total}")
            print(f"[OptimizerAgent] ✅ Plan ready (€{total}). → ItineraryAgent")

            reply = Message(to=f"itinerary_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "OptimizerAgent")
            reply.body = json.dumps(
                {
                    "preferences": prefs,
                    "best_flight": best_flight,
                    "best_hotel":  best_hotel,
                    "activities":  top_activities,
                    "total_cost":  total,
                }
            )
            await self.send(reply)
            print("[OptimizerAgent] ✅ INFORM → ItineraryAgent")

        async def _send_failure(self, reason: str):
            fail = Message(to=f"booking_agent@{SERVER}")
            fail.set_metadata("performative", "failure")
            fail.set_metadata("sender",       "OptimizerAgent")
            fail.body = json.dumps({"reason": reason})
            await self.send(fail)

    async def setup(self):
        print("[OptimizerAgent] Agent started.")
        set_agent_status("OptimizerAgent", "running")
        t = Template()
        t.set_metadata("performative", "inform")
        self.add_behaviour(self.Listen(), t)