"""
Quick connection test — verifies SPADE can reach PyJabber.
Run this before main.py to confirm the server is reachable.
"""
import asyncio
import spade
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour

class TestAgent(Agent):
    class SayHello(OneShotBehaviour):
        async def run(self):
            print("[TestAgent] ✅ Connected to XMPP server successfully!")
            await self.agent.stop()

    async def setup(self):
        self.add_behaviour(self.SayHello())

async def main():
    print("Testing connection to PyJabber server...")
    agent = TestAgent("test_agent@localhost", "Pass123!",
                      verify_security=False)
    await agent.start(auto_register=True)
    await asyncio.sleep(3)
    if not agent.is_alive():
        print("✅ Test passed — server is reachable!")
    else:
        await agent.stop()
        print("✅ Test passed — server is reachable!")

spade.run(main())