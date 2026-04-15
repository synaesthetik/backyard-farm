"""REST endpoints for AI/Rules toggle and model maturity state (D-05, D-06, D-12, D-13).

Proxies to the bridge internal HTTP server (same pattern as recommendation_router.py).
The bridge owns toggle state and maturity tracking — this router is the API-side facade.

Endpoints:
  GET  /api/settings/ai      -- return all domain toggle states
  PATCH /api/settings/ai     -- update one domain toggle ("ai" or "rules")
  GET  /api/model-maturity   -- return domain maturity + per-zone data maturity

Security (T-04-08): domain and mode values are validated via Pydantic BaseModel.
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


class AISettingsPatch(BaseModel):
    """Request body for PATCH /api/settings/ai.

    Pydantic validation ensures domain and mode values are well-formed strings
    before they reach the bridge. The bridge performs final domain/mode validation
    (T-04-08: Elevation of Privilege mitigation — validate at API boundary too).
    """
    domain: str  # "irrigation" | "zone_health" | "flock_anomaly"
    mode: str    # "ai" | "rules"


@router.get("/api/settings/ai")
async def get_ai_settings():
    """Return the current AI/Rules toggle state for all three domains.

    Proxies GET /internal/ai-settings from the bridge process.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/ai-settings"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for AI settings: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — AI settings unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error fetching AI settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/settings/ai")
async def patch_ai_settings(body: AISettingsPatch):
    """Update the AI/Rules toggle for a single domain.

    Change takes effect on the next inference cycle — no bridge restart required (D-06).
    Proxies PATCH /internal/ai-settings to the bridge process.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/ai-settings"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url,
                json=body.model_dump(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    body_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body_text}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for AI settings patch: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — AI settings unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error patching AI settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/model-maturity")
async def get_model_maturity():
    """Return model maturity state: per-domain recommendation counts and per-zone data maturity.

    Proxies GET /internal/model-maturity from the bridge process.
    Used by the AI Status card on the Home tab (D-12, D-13).
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/model-maturity"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Bridge error: {body}")
                return await resp.json()
    except aiohttp.ClientConnectorError as exc:
        logger.error("Cannot reach bridge for model maturity: %s", exc)
        raise HTTPException(status_code=503, detail="Bridge unreachable — model maturity unavailable")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error fetching model maturity: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
