"""LiveKit Agent using livekit-agents framework."""

import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import WorkerOptions, JobContext

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Note: We assume 'livekit-agents' is installed as per plan.
# This is a reference implementation based on typical patterns.


async def entrypoint(ctx: JobContext):
    """Entry point for the LiveKit Agent Job."""
    logger.info(f"Starting job for room: {ctx.room.name}")

    await ctx.connect()

    # Wait for the first participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    try:
        from livekit.plugins import google
        from livekit.agents import AgentSession
    except ImportError:
        logger.error("Required LiveKit plugins not installed")
        return

    # Initialize the Gemini Realtime Model (Multimodal Live API)
    # Note: Adjust model name as per availability in your environment
    model = google.realtime.RealtimeModel(
        model="gemini-3.1-flash-live-preview",
        voice="Puck",
        api_version="v1beta"
    )

    # Create the agent with instructions and model
    my_agent = agents.Agent(
        instructions="You are a helpful assistant that can search the web.",
        llm=model
    )

    session = AgentSession(llm=model)
    
    await session.start(my_agent, room=ctx.room)
    
    logger.info("LiveKit Agent session started")
    
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    # This file can be run directly to start the worker
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("agent.log"),
            logging.StreamHandler()
        ]
    )
    options = WorkerOptions(
        entrypoint_fnc=entrypoint,
    )
    agents.cli.run_app(options)
