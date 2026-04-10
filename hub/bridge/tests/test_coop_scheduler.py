"""Tests for coop_scheduler.py — astronomical clock scheduler and stuck-door watchdog."""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestGetTodaySchedule:
    def test_get_today_schedule_returns_sunrise_sunset(self):
        """get_today_schedule() returns dict with open_at and close_at as datetime objects."""
        fake_sunrise = datetime(2026, 4, 10, 13, 30, 0, tzinfo=timezone.utc)
        fake_sunset = datetime(2026, 4, 10, 2, 15, 0, tzinfo=timezone.utc)  # before hard close

        fake_sun_result = {
            "sunrise": fake_sunrise,
            "sunset": fake_sunset,
        }

        with patch("astral.sun.sun", return_value=fake_sun_result):
            from coop_scheduler import get_today_schedule
            schedule = get_today_schedule()

        assert "open_at" in schedule
        assert "close_at" in schedule
        assert isinstance(schedule["open_at"], datetime)
        assert isinstance(schedule["close_at"], datetime)
        # With no offset, open_at == sunrise
        assert schedule["open_at"] == fake_sunrise

    def test_schedule_respects_offset(self, monkeypatch):
        """With COOP_OPEN_OFFSET_MINUTES=30, open_at is 30 minutes after sunrise."""
        fake_sunrise = datetime(2026, 4, 10, 13, 30, 0, tzinfo=timezone.utc)
        fake_sunset = datetime(2026, 4, 10, 2, 15, 0, tzinfo=timezone.utc)

        fake_sun_result = {
            "sunrise": fake_sunrise,
            "sunset": fake_sunset,
        }

        monkeypatch.setenv("COOP_OPEN_OFFSET_MINUTES", "30")

        import importlib
        import coop_scheduler
        importlib.reload(coop_scheduler)

        with patch("astral.sun.sun", return_value=fake_sun_result):
            schedule = coop_scheduler.get_today_schedule()

        expected_open = fake_sunrise + timedelta(minutes=30)
        assert schedule["open_at"] == expected_open

    def test_hard_close_backstop(self, monkeypatch):
        """Sunset at 22:00 UTC, COOP_HARD_CLOSE_HOUR=21 -> close_at is 21:00 UTC."""
        today = datetime.now(timezone.utc).date()
        fake_sunrise = datetime(today.year, today.month, today.day, 13, 30, 0, tzinfo=timezone.utc)
        # Sunset at 22:00 UTC — after hard close hour of 21
        fake_sunset = datetime(today.year, today.month, today.day, 22, 0, 0, tzinfo=timezone.utc)

        fake_sun_result = {
            "sunrise": fake_sunrise,
            "sunset": fake_sunset,
        }

        monkeypatch.setenv("COOP_HARD_CLOSE_HOUR", "21")
        monkeypatch.setenv("COOP_OPEN_OFFSET_MINUTES", "0")
        monkeypatch.setenv("COOP_CLOSE_OFFSET_MINUTES", "0")

        import importlib
        import coop_scheduler
        importlib.reload(coop_scheduler)

        with patch("astral.sun.sun", return_value=fake_sun_result):
            schedule = coop_scheduler.get_today_schedule()

        expected_hard_close = datetime(today.year, today.month, today.day, 21, 0, 0, tzinfo=timezone.utc)
        assert schedule["close_at"] == expected_hard_close


class TestStuckDoorWatchdog:
    @pytest.mark.asyncio
    async def test_stuck_door_watchdog_fires_alert(self, monkeypatch):
        """When no ack arrives within timeout, notify_callback is called with P0 stuck_door alert."""
        monkeypatch.setenv("STUCK_DOOR_TIMEOUT_SECONDS", "0")

        import importlib
        import coop_scheduler
        importlib.reload(coop_scheduler)

        notify_callback = AsyncMock()

        # Ensure the ack event is NOT set (simulating no ack received)
        coop_scheduler._coop_ack_received.clear()

        # Set timeout to 0.1 seconds for fast test execution
        original_timeout = coop_scheduler.STUCK_DOOR_TIMEOUT_SECONDS
        coop_scheduler.STUCK_DOOR_TIMEOUT_SECONDS = 0.1

        try:
            await coop_scheduler._stuck_door_watchdog(notify_callback)
        finally:
            coop_scheduler.STUCK_DOOR_TIMEOUT_SECONDS = original_timeout

        # Verify notify_callback was called with the alert_state delta
        notify_callback.assert_awaited_once()
        call_args = notify_callback.call_args[0][0]

        assert call_args["type"] == "alert_state"
        assert "alerts" in call_args
        assert len(call_args["alerts"]) >= 1

        alert = call_args["alerts"][0]
        assert alert["key"] == "stuck_door:coop"
        assert alert["severity"] == "P0"
