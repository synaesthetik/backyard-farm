"""REST endpoints for sensor calibration management (ZONE-07, D-02, D-05).

Proxies to the bridge internal HTTP server (same pattern as inference_settings_router.py).
The bridge owns CalibrationStore — this router is the API-side facade.

Endpoints:
  GET   /api/calibrations                              — list all calibration entries
  POST  /api/calibrations/{zone_id}/{sensor_type}/record — record a new calibration
  PATCH /api/calibrations/{zone_id}/{sensor_type}      — update calibration fields

Security (T-05-01): Pydantic BaseModel validates all fields at API boundary.
Exports: router
"""
import logging
import os
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

BRIDGE_INTERNAL_URL = os.getenv("BRIDGE_INTERNAL_URL", "http://bridge:8001")


class CalibrationRecordBody(BaseModel):
    """Request body for POST /api/calibrations/{zone_id}/{sensor_type}/record.

    Pydantic validation ensures field types are correct at the API boundary
    before proxying to the bridge (T-05-01: Tampering mitigation).
    """
    offset: float
    dry_value: Optional[float] = None
    wet_value: Optional[float] = None
    temp_coefficient: float = 0.0


class CalibrationPatch(BaseModel):
    """Request body for PATCH /api/calibrations/{zone_id}/{sensor_type}.

    All fields optional — only provided fields are updated.
    """
    offset_value: Optional[float] = None
    dry_value: Optional[float] = None
    wet_value: Optional[float] = None
    temp_coefficient: Optional[float] = None


@router.get("/api/calibrations")
async def get_calibrations():
    """Return all calibration entries from the bridge CalibrationStore.

    Proxies GET /internal/calibrations from the bridge process.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/calibrations"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for calibrations: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — calibrations unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error fetching calibrations: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/calibrations/{zone_id}/{sensor_type}/record")
async def record_calibration(zone_id: str, sensor_type: str, body: CalibrationRecordBody):
    """Record a new calibration event for a sensor.

    Sets last_calibration_date to NOW() and clears any ph_calibration_overdue alert.
    Proxies POST /internal/calibrations/{zone_id}/{sensor_type}/record to bridge.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/calibrations/{zone_id}/{sensor_type}/record"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body.model_dump(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    body_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body_text}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge to record calibration for %s/%s: %s", zone_id, sensor_type, exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — calibration record unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error recording calibration for %s/%s: %s", zone_id, sensor_type, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/calibrations/{zone_id}/{sensor_type}")
async def patch_calibration(zone_id: str, sensor_type: str, body: CalibrationPatch):
    """Update specific calibration fields for a sensor (does not set last_calibration_date).

    Proxies PATCH /internal/calibrations/{zone_id}/{sensor_type} to bridge.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/calibrations/{zone_id}/{sensor_type}"
    # Only send non-None fields to the bridge
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    body_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body_text}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge to patch calibration for %s/%s: %s", zone_id, sensor_type, exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — calibration patch unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error patching calibration for %s/%s: %s", zone_id, sensor_type, exc)
        raise HTTPException(status_code=500, detail=str(exc))
