import json
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message

class PreferenceAgent(Agent):

    class CollectAndSendPreferences(OneShotBehaviour):
        async def run(self):
            print("\n[PreferenceAgent] Collecting user preferences...")

            preferences = {
                "scenario": "solo",
                "destination": "Rome",
                "days": 5,
                "budget": 1500,
                "interests": ["cultural", "food"],
                "travel_style": "flexible"
            }

            print(f"[PreferenceAgent] Profile built for {preferences['scenario']} trip to {preferences['destination']}.")

            msg = Message(to="research_agent@localhost")
            msg.set_metadata("performative", "request")
            msg.body = json.dumps(preferences)

            await self.send(msg)
            print("[PreferenceAgent] ✅ Preferences sent to Research Agent.")

    async def setup(self):
        print("[PreferenceAgent] Agent started.")
        self.add_behaviour(self.CollectAndSendPreferences())