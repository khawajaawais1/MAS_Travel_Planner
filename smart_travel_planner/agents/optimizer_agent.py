import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class OptimizerAgent(Agent):

    class OptimizeOptions(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)

            if msg and msg.metadata.get("performative") == "inform":
                data = json.loads(msg.body)
                preferences = data["preferences"]
                flights = data["flights"]
                hotels = data["hotels"]
                activities = data["activities"]
                budget = preferences["budget"]

                print(f"\n[OptimizerAgent] Evaluating options against budget €{budget}...")

                if not flights or not hotels:
                    print("[OptimizerAgent] ❌ Not enough options found. Cannot optimize.")
                    return

                # AUTONOMOUS DECISION: pick best flight and hotel, score by rating and price
                best_flight = min(flights, key=lambda f: f["price"])
                best_hotel = max(hotels, key=lambda h: h["rating"])
                top_activities = activities[:2]

                hotel_total = best_hotel["price_per_night"] * preferences["days"]
                activity_total = sum(a["price"] for a in top_activities)
                total_cost = best_flight["price"] + hotel_total + activity_total

                print(f"[OptimizerAgent] Estimated total: €{total_cost} (budget: €{budget})")

                if total_cost > budget:
                    # FEEDBACK LOOP back to Research Agent
                    print(f"[OptimizerAgent] ⚠️ Over budget! Requesting broader search...")
                    new_prefs = preferences.copy()
                    new_prefs["budget"] = int(budget * 1.2)
                    feedback = Message(to="research_agent@localhost")
                    feedback.set_metadata("performative", "request")
                    feedback.body = json.dumps(new_prefs)
                    await self.send(feedback)
                    return

                optimized = {
                    "preferences": preferences,
                    "best_flight": best_flight,
                    "best_hotel": best_hotel,
                    "activities": top_activities,
                    "total_cost": total_cost
                }

                print(f"[OptimizerAgent] ✅ Best plan selected. Total: €{total_cost}")

                reply = Message(to="itinerary_agent@localhost")
                reply.set_metadata("performative", "inform")
                reply.body = json.dumps(optimized)
                await self.send(reply)

    async def setup(self):
        print("[OptimizerAgent] Agent started.")
        self.add_behaviour(self.OptimizeOptions())