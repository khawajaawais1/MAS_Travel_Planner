import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class ItineraryAgent(Agent):

    class BuildItinerary(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)

            if msg and msg.metadata.get("performative") == "inform":
                data = json.loads(msg.body)
                preferences = data["preferences"]
                flight = data["best_flight"]
                hotel = data["best_hotel"]
                activities = data["activities"]
                days = preferences["days"]
                is_family = preferences.get("scenario") == "family"

                print(f"\n[ItineraryAgent] Building {days}-day itinerary...")

                # AUTONOMOUS DECISION: pace the trip based on scenario
                itinerary = []
                itinerary.append(
                    f"Day 1: Arrive via {flight['airline']} | Check in at {hotel['name']}"
                )

                for day in range(2, days):
                    act = activities[(day - 2) % len(activities)]["name"] if activities else "Free time"
                    rest = " | Rest time included" if is_family else ""
                    itinerary.append(f"Day {day}: {act}{rest}")

                itinerary.append(f"Day {days}: Checkout & Departure")

                print("[ItineraryAgent] Itinerary built:")
                for line in itinerary:
                    print(f"   {line}")

                result = {
                    "preferences": preferences,
                    "flight": flight,
                    "hotel": hotel,
                    "activities": activities,
                    "itinerary": itinerary,
                    "total_cost": data["total_cost"]
                }

                reply = Message(to="booking_agent@localhost")
                reply.set_metadata("performative", "inform")
                reply.body = json.dumps(result)
                await self.send(reply)
                print("[ItineraryAgent] ✅ Itinerary sent to Booking Agent.")

    async def setup(self):
        print("[ItineraryAgent] Agent started.")
        self.add_behaviour(self.BuildItinerary())