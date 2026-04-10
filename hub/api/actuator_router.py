"""Actuator command endpoints — irrigation and coop door.

Command flow: REST POST -> MQTT publish -> edge executes -> edge acks via MQTT ->
bridge forwards ack as actuator_ack delta -> pending_acks event resolved ->
REST response returned to client.

Per D-14: button spinner + disabled state while in flight.
Per D-15: no optimistic update — status only changes on confirmed ack.
Per D-17: single-zone-at-a-time invariant enforced here.
"""
import asyncio
import json
import logging
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_BRIDGE_USER", "hub-bridge")
MQTT_PASS = os.getenv("MQTT_BRIDGE_PASS", "")
ACK_TIMEOUT_SECONDS = 10.0

router = APIRouter()

# Shared state — in-memory, single-process (see Research "Don't Hand-Roll")
pending_acks: dict[str, asyncio.Event] = {}
active_irrigation_zone: str | None = None  # IRRIG-02 invariant


class IrrigateRequest(BaseModel):
    zone_id: str
    action: str  # "open" | "close"

class CoopDoorRequest(BaseModel):
    action: str  # "open" | "close"

class CommandResponse(BaseModel):
    status: str
    command_id: str


def resolve_ack(command_id: str):
    """Called by bridge when ack is received. Sets the asyncio.Event."""
    event = pending_acks.get(command_id)
    if event:
        event.set()


async def _send_irrigation_command(zone_id: str, action: str) -> str:
    """Publish an irrigation MQTT command and wait for ack. Returns command_id.

    Raises HTTPException on MQTT failure (502) or ack timeout (504).
    Used by both the irrigate() endpoint and recommendation_router.approve_recommendation().
    Updates active_irrigation_zone state when action is open or close.
    """
    global active_irrigation_zone

    command_id = str(uuid.uuid4())
    ack_event = asyncio.Event()
    pending_acks[command_id] = ack_event

    import aiomqtt
    try:
        async with aiomqtt.Client(
            MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS
        ) as client:
            payload = json.dumps({
                "command_id": command_id,
                "action": action,
                "zone_id": zone_id,
            })
            await client.publish(
                f"farm/{zone_id}/commands/irrigate", payload, qos=1
            )
    except Exception as e:
        pending_acks.pop(command_id, None)
        logger.error("MQTT publish failed: %s", e)
        raise HTTPException(status_code=502, detail="Failed to send command to edge node")

    try:
        await asyncio.wait_for(ack_event.wait(), timeout=ACK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        pending_acks.pop(command_id, None)
        raise HTTPException(status_code=504, detail="Command timeout - edge node did not ack")
    finally:
        pending_acks.pop(command_id, None)

    if action == "open":
        active_irrigation_zone = zone_id
    elif action == "close" and active_irrigation_zone == zone_id:
        active_irrigation_zone = None

    return command_id


@router.post("/api/actuators/irrigate", response_model=CommandResponse)
async def irrigate(request: IrrigateRequest):
    global active_irrigation_zone

    # IRRIG-02: single-zone-at-a-time invariant
    if request.action == "open" and active_irrigation_zone is not None:
        raise HTTPException(
            status_code=409,
            detail="Another zone is already irrigating."
        )

    command_id = await _send_irrigation_command(request.zone_id, request.action)
    return CommandResponse(status="confirmed", command_id=command_id)


@router.post("/api/actuators/coop-door", response_model=CommandResponse)
async def coop_door(request: CoopDoorRequest):
    command_id = str(uuid.uuid4())
    ack_event = asyncio.Event()
    pending_acks[command_id] = ack_event

    import aiomqtt
    try:
        async with aiomqtt.Client(
            MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS
        ) as client:
            payload = json.dumps({
                "command_id": command_id,
                "action": request.action,
                "zone_id": "coop",
            })
            await client.publish(
                "farm/coop/commands/coop_door", payload, qos=1
            )
    except Exception as e:
        pending_acks.pop(command_id, None)
        logger.error("MQTT publish failed: %s", e)
        raise HTTPException(status_code=502, detail="Failed to send command to edge node")

    try:
        await asyncio.wait_for(ack_event.wait(), timeout=ACK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        pending_acks.pop(command_id, None)
        raise HTTPException(status_code=504, detail="Command timeout - edge node did not ack")
    finally:
        pending_acks.pop(command_id, None)

    return CommandResponse(status="confirmed", command_id=command_id)
