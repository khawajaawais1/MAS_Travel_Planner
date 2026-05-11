"""
ItineraryAgent
──────────────
Responsibilities:
  • Receive INFORM from OptimizerAgent.
  • Build a human-readable day-by-day itinerary.
  • Each interior day gets a UNIQUE activity — no repetition.
  • Family pacing adds a structured morning/afternoon split.
  • Send the finished plan to BookingAgent via INFORM.

Autonomous decisions:
  • Day 1  → arrival + check-in + evening neighbourhood walk.
  • Day N  → checkout + departure flight.
  • If more interior days than unique activities, fills extras with
    city-specific free suggestions (markets, parks, viewpoints) so
    the itinerary never shows the same item twice.
  • Family trips add "[rest break included]" and drop late-night items.
  • Solo trips add an optional evening recommendation per day.
"""

import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

from web.dashboard import (
    UI_STATE, ui_log, set_stage, set_agent_status, SERVER
)

# City-specific filler suggestions used when paid activities run out
CITY_FILLERS = {
    "Rome": [
        "Explore the Trastevere neighbourhood on foot",
        "Morning at Campo de' Fiori market",
        "Stroll along the Tiber riverside path",
        "People-watching at Piazza Navona",
        "Visit the Pantheon (free entry before 9 am)",
        "Afternoon in the Pigneto street-art quarter",
    ],
    "Florence": [
        "Cross Ponte Vecchio at sunrise",
        "Browse the San Lorenzo leather market",
        "Hike to Piazzale Michelangelo for panoramic views",
        "Afternoon in the Oltrarno antique quarter",
        "Visit the Mercato Centrale food hall",
        "Stroll through the Boboli Gardens",
    ],
    "Paris": [
        "Morning walk along the Canal Saint-Martin",
        "Explore Shakespeare & Company bookshop and the Latin Quarter",
        "Wander through Montmartre and see Sacré-Cœur",
        "Afternoon at the Palais Royal gardens",
        "Visit the covered passages (Galerie Vivienne, Passage Jouffroy)",
        "Evening at Place des Vosges in Le Marais",
        "Explore the Belleville neighbourhood and street art",
    ],
    "Barcelona": [
        "Morning walk along La Barceloneta beach",
        "Explore El Born neighbourhood and Mercat de Santa Caterina",
        "Stroll down La Rambla to the harbour",
        "Afternoon in the Eixample modernista buildings",
        "Visit Bunkers del Carmel for 360° city views",
        "Explore the Poblenou neighbourhood",
    ],
}

EVENING_SUGGESTIONS = {
    "Rome":      "End the evening with aperitivo at a Pigneto bar.",
    "Florence":  "Finish with a Negroni at an Oltrarno cocktail bar.",
    "Paris":     "Wrap up with a glass of natural wine in Le Marais.",
    "Barcelona": "Close the night with vermouth and pintxos in El Born.",
}


def _build_itinerary(
    flight: dict,
    hotel: dict,
    activities: list[dict],
    days: int,
    dest: str,
    is_family: bool,
) -> list[str]:
    """
    Returns a list of day strings, one per day, with no repeated activities.
    """
    itinerary: list[str] = []
    fillers = list(CITY_FILLERS.get(dest, ["Free exploration day"]))
    evening = EVENING_SUGGESTIONS.get(dest, "")

    # ── Day 1: Arrival ────────────────────────────────────────────────────
    itinerary.append(
        f"✈  Fly {flight['airline']} ({flight['flight_number']}, "
        f"{flight['duration']})  →  Check in at {hotel['name']} ({hotel['area']})  "
        f"→  Evening stroll to get your bearings."
    )

    # ── Interior days ─────────────────────────────────────────────────────
    used_acts: list[str] = []            # track used activity names

    for day_num in range(2, days):
        day_activities: list[str] = []

        # Morning activity (paid, if available)
        available = [a for a in activities if a["name"] not in used_acts]
        if available:
            act = available[0]
            used_acts.append(act["name"])
            duration = act.get("duration", "")
            cost_str = f"€{act['price']}" if act["price"] > 0 else "free"
            morning  = f"{act['name']} ({duration}, {cost_str})"
            if act.get("description"):
                morning += f" — {act['description']}"
            if is_family:
                morning += "  [rest break after]"
            day_activities.append(f"🎯 Morning: {morning}")
        else:
            # Fall back to a filler
            if fillers:
                suggestion = fillers.pop(0)
            else:
                suggestion = "Free exploration"
            day_activities.append(f"🗺  Morning: {suggestion}")

        # Afternoon free suggestion (always a filler)
        if fillers:
            afternoon = fillers.pop(0)
            day_activities.append(f"🌆 Afternoon: {afternoon}")

        # Evening (solo only)
        if not is_family and evening:
            day_activities.append(f"🍷 Evening: {evening}")

        itinerary.append("  |  ".join(day_activities))

    # ── Final day: Checkout ───────────────────────────────────────────────
    if days >= 2:
        itinerary.append(
            f"🏠 Checkout from {hotel['name']}  →  "
            f"Return flight home  →  Safe travels!"
        )

    return itinerary


class ItineraryAgent(Agent):

    class Listen(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=60)
            if msg is None:
                return
            if msg.get_metadata("performative") != "inform":
                return

            data      = json.loads(msg.body)
            prefs     = data["preferences"]
            flight    = data["best_flight"]
            hotel     = data["best_hotel"]
            acts      = data["activities"]
            days      = prefs["days"]
            dest      = prefs["destination"]
            is_family = prefs.get("scenario") == "family"
            sender    = msg.get_metadata("sender") or "unknown"

            set_stage("building itinerary")
            print(
                f"\n[ItineraryAgent] INFORM from {sender} → "
                f"building {days}-day plan for {dest} "
                f"({'family' if is_family else 'solo'})"
            )

            itinerary = _build_itinerary(
                flight=flight,
                hotel=hotel,
                activities=acts,
                days=days,
                dest=dest,
                is_family=is_family,
            )

            UI_STATE["itinerary"] = itinerary
            ui_log("ItineraryAgent", f"Built {len(itinerary)}-day itinerary for {dest}")
            print(f"[ItineraryAgent] ✅ {len(itinerary)}-day itinerary created")

            reply = Message(to=f"booking_agent@{SERVER}")
            reply.set_metadata("performative", "inform")
            reply.set_metadata("sender",       "ItineraryAgent")
            reply.body = json.dumps(
                {
                    "preferences": prefs,
                    "flight":      flight,
                    "hotel":       hotel,
                    "activities":  acts,
                    "itinerary":   itinerary,
                    "total_cost":  data["total_cost"],
                }
            )
            await self.send(reply)
            print("[ItineraryAgent] ✅ INFORM → BookingAgent")

    async def setup(self):
        print("[ItineraryAgent] Agent started.")
        set_agent_status("ItineraryAgent", "running")
        t = Template()
        t.set_metadata("performative", "inform")
        self.add_behaviour(self.Listen(), t)