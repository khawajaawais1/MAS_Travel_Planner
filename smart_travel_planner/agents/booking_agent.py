import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class BookingAgent(Agent):

    class PresentBooking(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)

            if msg and msg.metadata.get("performative") == "inform":
                data = json.loads(msg.body)
                prefs = data["preferences"]

                print("\n" + "=" * 55)
                print("   ✈️  SMART TRAVEL PLANNER — FINAL BOOKING SUMMARY")
                print("=" * 55)
                print(f"  Scenario    : {prefs['scenario'].upper()}")
                print(f"  Destination : {prefs['destination']}")
                print(f"  Duration    : {prefs['days']} days")
                print(f"  Total Cost  : €{data['total_cost']}")
                print("-" * 55)
                print(f"  ✈  Flight   : {data['flight']['airline']} "
                      f"({data['flight']['duration']}) — €{data['flight']['price']}")
                print(f"  🏨 Hotel    : {data['hotel']['name']} "
                      f"— €{data['hotel']['price_per_night']}/night "
                      f"(Rating: {data['hotel']['rating']})")
                print(f"  🎯 Activities:")
                for a in data["activities"]:
                    print(f"       - {a['name']} (€{a['price']})")
                print("-" * 55)
                print("  📅 Day-by-Day Itinerary:")
                for line in data["itinerary"]:
                    print(f"       {line}")
                print("=" * 55)
                print("  ✅ Booking recommendations ready for user!")
                print("=" * 55 + "\n")

    async def setup(self):
        print("[BookingAgent] Agent started.")
        self.add_behaviour(self.PresentBooking())