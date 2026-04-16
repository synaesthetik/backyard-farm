"""Tests for NtfySettings sidecar persistence (D-06, D-07, D-09)."""
import json
import os
import pytest


def test_ntfy_disabled_when_url_empty(tmp_path, monkeypatch):
    """NtfySettings with no env vars and no file: is_enabled() is False."""
    monkeypatch.delenv("NTFY_URL", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    settings_file = str(tmp_path / "ntfy_settings.json")

    import importlib
    import sys
    # Import fresh to avoid cached module state
    if "ntfy_settings" in sys.modules:
        del sys.modules["ntfy_settings"]

    import ntfy_settings as ns_mod
    settings = ns_mod.NtfySettings(settings_file=settings_file)
    assert settings.is_enabled() is False


def test_ntfy_enabled_when_url_set(tmp_path, monkeypatch):
    """When NTFY_URL and NTFY_TOPIC are set, is_enabled() is True (D-07)."""
    monkeypatch.setenv("NTFY_URL", "http://ntfy.example.com")
    monkeypatch.setenv("NTFY_TOPIC", "farm-alerts")
    settings_file = str(tmp_path / "ntfy_settings.json")

    import sys
    if "ntfy_settings" in sys.modules:
        del sys.modules["ntfy_settings"]

    import ntfy_settings as ns_mod
    settings = ns_mod.NtfySettings(settings_file=settings_file)
    assert settings.is_enabled() is True


def test_ntfy_update_persists(tmp_path, monkeypatch):
    """update() writes to JSON file; reload reads updated values (D-06)."""
    monkeypatch.delenv("NTFY_URL", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    settings_file = str(tmp_path / "ntfy_settings.json")

    import sys
    if "ntfy_settings" in sys.modules:
        del sys.modules["ntfy_settings"]

    import ntfy_settings as ns_mod
    settings = ns_mod.NtfySettings(settings_file=settings_file)
    settings.update(url="http://ntfy.home", topic="farm", enabled=True)

    # Reload from file
    settings2 = ns_mod.NtfySettings(settings_file=settings_file)
    assert settings2.is_enabled() is True
    all_settings = settings2.get_all()
    assert all_settings["url"] == "http://ntfy.home"
    assert all_settings["topic"] == "farm"
    assert all_settings["enabled"] is True


def test_ntfy_get_all_returns_dict(tmp_path, monkeypatch):
    """get_all() returns dict with url, topic, enabled keys."""
    monkeypatch.delenv("NTFY_URL", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    settings_file = str(tmp_path / "ntfy_settings.json")

    import sys
    if "ntfy_settings" in sys.modules:
        del sys.modules["ntfy_settings"]

    import ntfy_settings as ns_mod
    settings = ns_mod.NtfySettings(settings_file=settings_file)
    result = settings.get_all()
    assert isinstance(result, dict)
    assert "url" in result
    assert "topic" in result
    assert "enabled" in result


def test_ntfy_disabled_when_enabled_false(tmp_path, monkeypatch):
    """Setting URL but enabled=False means is_enabled() returns False (D-09)."""
    monkeypatch.delenv("NTFY_URL", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    settings_file = str(tmp_path / "ntfy_settings.json")

    import sys
    if "ntfy_settings" in sys.modules:
        del sys.modules["ntfy_settings"]

    import ntfy_settings as ns_mod
    settings = ns_mod.NtfySettings(settings_file=settings_file)
    settings.update(url="http://ntfy.home", topic="farm", enabled=False)
    assert settings.is_enabled() is False
