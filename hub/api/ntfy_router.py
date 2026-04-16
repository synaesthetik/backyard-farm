"""REST endpoints for ntfy push notification settings (NOTF-03, D-07).

Proxies to the bridge internal HTTP server.
The bridge owns NtfySettings — this router is the API-side facade.

Endpoints:
  GET   /api/settings/notifications       — return current ntfy settings
  PATCH /api/settings/notifications       — update ntfy settings (url, topic, enabled)
  POST  /api/settings/notifications/test  — send test notification via bridge

Security (T-05-04): Pydantic BaseModel validates fields at API boundary.
Exports: router
"""
import logging
import os

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

BRIDGE_INTERNAL_URL = os.getenv("BRIDGE_INTERNAL_URL", "http://bridge:8001")


class NtfySettingsPatch(BaseModel):
    """Request body for PATCH /api/settings/notifications.

    Pydantic validation ensures url, topic, and enabled values are
    well-formed before they reach the bridge (T-05-04: Tampering mitigation).
    """
    url: str | None = None
    topic: str | None = None
    enabled: bool | None = None


@router.get("/api/settings/notifications")
async def get_ntfy_settings():
    """Return the current ntfy push notification settings.

    Proxies GET /internal/ntfy-settings from the bridge process.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/ntfy-settings"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for ntfy settings: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — ntfy settings unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error fetching ntfy settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/settings/notifications")
async def patch_ntfy_settings(body: NtfySettingsPatch):
    """Update ntfy push notification settings.

    Changes take effect immediately — no bridge restart required (D-07).
    Proxies PATCH /internal/ntfy-settings to the bridge process.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/ntfy-settings"
    payload = body.model_dump(exclude_none=True)
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
        logger.error("Cannot reach bridge for ntfy settings patch: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — ntfy settings unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error patching ntfy settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/settings/notifications/test")
async def test_ntfy_notification():
    """Send a test push notification via the bridge.

    Proxies POST /internal/ntfy-test to the bridge process.
    Returns {"status": "ok"} on success, raises HTTPException(502) on failure.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/ntfy-test"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                result = await resp.json()
                if resp.status != 200 or result.get("status") != "ok":
                    raise HTTPException(
                        status_code=502,
                        detail=result.get("message", "ntfy test failed"),
                    )
                return {"status": "ok"}
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for ntfy test: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — ntfy test unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error testing ntfy: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
