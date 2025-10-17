from datetime import datetime
from typing import Literal
import random
from dataclasses import dataclass

from constants import main_system_prompt

from agents.realtime import (
    RealtimeAgent,
    realtime_handoff
)

from agents import function_tool
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

reservation_agent = RealtimeAgent(
    name="Reservation Agent",
    instructions="You are a helpful voice assistant. Your job is to help the customer make a reservation for in-person dining, gather all required details, call tools as needed, and clearly report the outcome. After attempting a reservation, if it succeeds, confirm the details and provide the caller with the reservation time and party size. If it fails, kindly explain that it did not go through and suggest nearby alternative times that might work instead.",
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



