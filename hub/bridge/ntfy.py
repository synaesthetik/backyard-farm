"""ntfy HTTP POST dispatch for push notifications (D-08, NOTF-03).

Sends alerts to farmer's self-hosted ntfy server.
Called via asyncio.create_task() — non-blocking (Pitfall 4).
Priority mapping: P0 -> 5 (urgent), P1 -> 3 (default).

ntfy is silently disabled when URL is empty or ntfy_settings.is_enabled() is
False (D-09). A 5-second timeout guards against slow/unresponsive ntfy servers
(T-05-06 — DoS mitigation).

Exports: send_ntfy_notification, send_ntfy_test
"""
import logging

import aiohttp

from ntfy_settings import NtfySettings

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=5)


async def send_ntfy_notification(ntfy_settings: NtfySettings, alert: dict) -> None:
    """Fire-and-forget ntfy push notification for a single alert (D-08).

    Args:
        ntfy_settings: NtfySettings instance — checked for is_enabled() first.
        alert: Alert dict with at least "severity" ("P0"|"P1") and "message" keys.

    Priority mapping (T-05-06 — non-blocking, 5s timeout):
        P0 -> "5" (urgent)
        P1 -> "3" (default)
    """
    if not ntfy_settings.is_enabled():
        return

    settings = ntfy_settings.get_all()
    url = settings.get("url", "").rstrip("/")
    topic = settings.get("topic", "")
    endpoint = f"{url}/{topic}"

    priority = "5" if alert.get("severity") == "P0" else "3"
    message = alert.get("message", "Farm alert")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                data=message,
                headers={
                    "Title": "Farm Alert",
                    "Priority": priority,
                    "Tags": "warning",
                },
                timeout=_TIMEOUT,
            ):
                pass
        logger.debug("ntfy notification sent to %s (priority=%s)", endpoint, priority)
    except Exception as exc:
        logger.warning(
            "ntfy notification failed (non-critical): %s — %s",
            endpoint,
            exc,
        )


async def send_ntfy_test(ntfy_settings: NtfySettings) -> tuple[bool, str]:
    """Send a test notification to verify ntfy configuration.

    Used by the POST /internal/ntfy-test endpoint.

    Returns:
        (True, "ok") on success.
        (False, error_message) on failure.
    """
    settings = ntfy_settings.get_all()
    url = settings.get("url", "").rstrip("/")
    topic = settings.get("topic", "")
    endpoint = f"{url}/{topic}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                data="Test notification from Backyard Farm",
                headers={
                    "Title": "Farm Alert — Test",
                    "Priority": "3",
                    "Tags": "white_check_mark",
                },
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    return False, f"ntfy returned {resp.status}: {body}"
        return True, "ok"
    except Exception as exc:
        logger.warning("ntfy test notification failed: %s — %s", endpoint, exc)
        return False, str(exc)
