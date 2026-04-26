import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from data.mock_data import FLIGHTS, HOTELS, ACTIVITIES

class ResearchAgent(Agent):

    class GatherOptions(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)

            if msg and msg.metadata.get("performative") == "request":
                preferences = json.loads(msg.body)
                print(f"\n[ResearchAgent] Received request for {preferences['destination']}.")

                destination = preferences["destination"]
                budget = preferences["budget"]
                interests = preferences["interests"]
                is_family = preferences.get("scenario") == "family"

                # AUTONOMOUS DECISION: filter based on scenario
                flights = [f for f in FLIGHTS
                           if f["to"] == destination and f["price"] < budget * 0.3]

                hotels = [h for h in HOTELS
                          if h["city"] == destination and
                          (not is_family or h["family_friendly"])]

                activities = [a for a in ACTIVITIES
                              if a["city"] == destination and
                              a["type"] in interests and
                              (not is_family or a["family_friendly"])]

                print(f"[ResearchAgent] Found: {len(flights)} flights, "
                      f"{len(hotels)} hotels, {len(activities)} activities.")

                results = {
                    "preferences": preferences,
                    "flights": flights,
                    "hotels": hotels,
                    "activities": activities
                }

                reply = Message(to="optimizer_agent@localhost")
                reply.set_metadata("performative", "inform")
                reply.body = json.dumps(results)
                await self.send(reply)
                print("[ResearchAgent] ✅ Results sent to Optimizer Agent.")

    async def setup(self):
        print("[ResearchAgent] Agent started.")
        self.add_behaviour(self.GatherOptions())