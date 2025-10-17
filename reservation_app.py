import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv

from agents.realtime import RealtimeAgent, RealtimeRunner, realtime_handoff
from agents import function_tool
from constants import main_system_prompt


@dataclass
class ReservationAttempt:
    """Record of an attempt to create a reservation."""

    reservation_at: datetime
    party_size: int
    status: Literal["success", "error"]

@function_tool  
async def make_reservation(reservation_at: datetime, party_size: int) -> ReservationAttempt:
    """Attempt to create a reservation and return the result."""
    success = random.randint(0, 1) == 1
    status: Literal["success", "error"] = "success" if success else "error"
    print(status)
    return ReservationAttempt(
        reservation_at=reservation_at,
        party_size=party_size,
        status=status,
    )

async def main():
    # Create the agent
    reservation_agent = RealtimeAgent(
    name="Reservation Agent",
    instructions=(
        
    ),
    tools=[make_reservation],
    handoff_description="An agent responsible for helping the customer to make a reservation for in person dining."
    )

    order_agent = RealtimeAgent(
        name="Order agent",
        instructions="You are a helpful voice assistant.  Your job is to help the customer place an online order",
        handoff_description="An agent responsible for helping the customer to place an online oder"
    )

    triage_agent = RealtimeAgent(
        name="Triage agent",
        instructions=main_system_prompt,
        handoffs=[realtime_handoff(reservation_agent), 
                  realtime_handoff(order_agent)],
    )
    # Set up the runner with configuration
    runner = RealtimeRunner(
        starting_agent=triage_agent,
        config={
            "model_settings": {
                "model_name": "gpt-realtime",
                "voice": "ash",
                "modalities": ["audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {"type": "semantic_vad", "interrupt_response": True},
            }
        },
    )
    # Start the session
    session = await runner.run()

    async with session:
        print("Session started! The agent will stream audio responses in real-time.")
        # Process events
        async for event in session:
            try:
                if event.type == "agent_start":
                    print(f"Agent started: {event.agent.name}")
                elif event.type == "agent_end":
                    print(f"Agent ended: {event.agent.name}")
                elif event.type == "handoff":
                    print(f"Handoff from {event.from_agent.name} to {event.to_agent.name}")
                elif event.type == "tool_start":
                    print(f"Tool started: {event.tool.name}")
                elif event.type == "tool_end":
                    print(f"Tool ended: {event.tool.name}; output: {event.output}")
                elif event.type == "audio_end":
                    print("Audio ended")
                elif event.type == "audio":
                    # Enqueue audio for callback-based playback with metadata
                    # Non-blocking put; queue is unbounded, so drops won’t occur.
                    pass
                elif event.type == "audio_interrupted":
                    print("Audio interrupted")
                    # Begin graceful fade + flush in the audio callback and rebuild jitter buffer.
                elif event.type == "error":
                    print(f"Error: {event.error}")
                elif event.type == "history_updated":
                    pass  # Skip these frequent events
                elif event.type == "history_added":
                    pass  # Skip these frequent events
                elif event.type == "raw_model_event":
                    print(f"Raw model event: {_truncate_str(str(event.data), 200)}")
                else:
                    print(f"Unknown event type: {event.type}")
            except Exception as e:
                print(f"Error processing event: {_truncate_str(str(e), 200)}")

def _truncate_str(s: str, max_length: int) -> str:
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s

if __name__ == "__main__":
    load_dotenv()
    # Run the session
    asyncio.run(main())
