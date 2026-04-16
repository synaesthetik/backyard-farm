"""Tests for ntfy HTTP POST dispatch (D-08, NOTF-03)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeNtfySettings:
    def __init__(self, enabled=True, url="http://ntfy.home", topic="farm"):
        self._enabled = enabled
        self._url = url
        self._topic = topic

    def is_enabled(self):
        return self._enabled

    def get_all(self):
        return {"url": self._url, "topic": self._topic, "enabled": self._enabled}


def test_send_ntfy_noop_when_disabled():
    """No HTTP call when ntfy is disabled (D-09)."""
    import sys
    if "ntfy" in sys.modules:
        del sys.modules["ntfy"]

    import ntfy as ntfy_mod

    settings = _FakeNtfySettings(enabled=False)
    alert = {"severity": "P1", "message": "Low moisture — zone-01"}

    with patch("aiohttp.ClientSession") as mock_session:
        asyncio.get_event_loop().run_until_complete(
            ntfy_mod.send_ntfy_notification(settings, alert)
        )
        mock_session.assert_not_called()


def test_send_ntfy_posts_to_correct_url():
    """HTTP POST goes to {url}/{topic} (D-08)."""
    import sys
    if "ntfy" in sys.modules:
        del sys.modules["ntfy"]

    import ntfy as ntfy_mod

    settings = _FakeNtfySettings(enabled=True, url="http://ntfy.home", topic="farm-alerts")
    alert = {"severity": "P1", "message": "Low moisture — zone-01"}

    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.status = 200

    mock_session_instance = AsyncMock()
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=None)
    mock_session_instance.post = MagicMock(return_value=mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session_instance):
        asyncio.get_event_loop().run_until_complete(
            ntfy_mod.send_ntfy_notification(settings, alert)
        )

    mock_session_instance.post.assert_called_once()
    call_args = mock_session_instance.post.call_args
    assert call_args[0][0] == "http://ntfy.home/farm-alerts"


def test_send_ntfy_priority_p0_is_5():
    """P0 severity maps to Priority header '5' (urgent)."""
    import sys
    if "ntfy" in sys.modules:
        del sys.modules["ntfy"]

    import ntfy as ntfy_mod

    settings = _FakeNtfySettings(enabled=True)
    alert = {"severity": "P0", "message": "Coop door stuck"}

    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.status = 200

    mock_session_instance = AsyncMock()
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=None)
    mock_session_instance.post = MagicMock(return_value=mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session_instance):
        asyncio.get_event_loop().run_until_complete(
            ntfy_mod.send_ntfy_notification(settings, alert)
        )

    call_kwargs = mock_session_instance.post.call_args[1]
    assert call_kwargs["headers"]["Priority"] == "5"


def test_send_ntfy_priority_p1_is_3():
    """P1 severity maps to Priority header '3' (default)."""
    import sys
    if "ntfy" in sys.modules:
        del sys.modules["ntfy"]

    import ntfy as ntfy_mod

    settings = _FakeNtfySettings(enabled=True)
    alert = {"severity": "P1", "message": "Low moisture"}

    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.status = 200

    mock_session_instance = AsyncMock()
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=None)
    mock_session_instance.post = MagicMock(return_value=mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session_instance):
        asyncio.get_event_loop().run_until_complete(
            ntfy_mod.send_ntfy_notification(settings, alert)
        )

    call_kwargs = mock_session_instance.post.call_args[1]
    assert call_kwargs["headers"]["Priority"] == "3"
