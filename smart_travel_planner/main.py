"""
main.py — Smart Travel Planner entry point
──────────────────────────────────────────
Usage:
    python main.py            # solo scenario (default)
    python main.py family     # family scenario

The embedded XMPP server means no external Ejabberd/Openfire needed.
Five agents start in dependency order (listeners first, trigger last).
The web dashboard runs at http://localhost:10001
"""

import sys
import asyncio
from aiohttp import web
from spade.container import run_container

from web.dashboard import (
    UI_STATE, AGENTS, ui_log, chat_log, set_stage,
    set_agent_status, create_web_app, SERVER, PASSWORD
)

# Agent imports
from agents.booking_agent    import BookingAgent
from agents.itinerary_agent  import ItineraryAgent
from agents.optimizer_agent  import OptimizerAgent
from agents.research_agent   import ResearchAgent
from agents.preference_agent import PreferenceAgent

PORT = 10001


async def main() -> None:
    scenario = "family" if len(sys.argv) > 1 and sys.argv[1] == "family" else "solo"
    UI_STATE["scenario"] = scenario
    set_stage("initialising")

    print("═" * 60)
    print(f"   🌍 SMART TRAVEL PLANNER  [scenario: {scenario.upper()}]")
    print("═" * 60)

    # ── Web server ────────────────────────────────────────────────────
    web_app = create_web_app()
    runner  = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", PORT)
    await site.start()
    ui_log("System", f"Dashboard → http://localhost:{PORT}")
    set_stage("starting agents")

    # ── Instantiate agents ────────────────────────────────────────────
    # Start listeners FIRST so no messages are lost, then the trigger.
    booking   = BookingAgent(  f"booking_agent@{SERVER}",   PASSWORD, verify_security=False)
    itinerary = ItineraryAgent(f"itinerary_agent@{SERVER}", PASSWORD, verify_security=False)
    optimizer = OptimizerAgent(f"optimizer_agent@{SERVER}", PASSWORD, verify_security=False)
    research  = ResearchAgent( f"research_agent@{SERVER}",  PASSWORD, verify_security=False)
    preference = PreferenceAgent(f"preference_agent@{SERVER}", PASSWORD, verify_security=False)

    # Make the PreferenceAgent accessible to HTTP handlers
    AGENTS["PreferenceAgent"] = preference

    for agent, name in [
        (booking,   "BookingAgent"),
        (itinerary, "ItineraryAgent"),
        (optimizer, "OptimizerAgent"),
        (research,  "ResearchAgent"),
        (preference,"PreferenceAgent"),
    ]:
        await agent.start(auto_register=True)
        ui_log(name, "started")
        set_agent_status(name, "running")
        print(f"[System] {name} started.")

    set_stage("waiting for user input")
    chat_log("System",
             "All five agents are running. Use the preference form on the left "
             "or answer the questions in the chat to get started.")
    print(f"\n[System] All 5 agents running.")
    print(f"[System] Dashboard → http://localhost:{PORT}\n")

    # ── Wait for booking to finish ────────────────────────────────────
    while booking.is_alive():
        await asyncio.sleep(1)

    set_stage("completed")
    ui_log("System", "Pipeline complete. Dashboard stays open — press Ctrl+C to exit.")
    print("\n🎉 Booking complete.")
    print(f"   Dashboard → http://localhost:{PORT}")
    print("   Press Ctrl+C when done.\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    # ── Graceful shutdown ─────────────────────────────────────────────
    for agent in [preference, research, optimizer, itinerary]:
        if agent.is_alive():
            await agent.stop()
    await runner.cleanup()
    print("[System] Shutdown complete.\n")


if __name__ == "__main__":
    run_container(main(), embedded_xmpp_server=True)