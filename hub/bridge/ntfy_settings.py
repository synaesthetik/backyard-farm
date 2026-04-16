"""ntfy push notification settings persistence (D-06, D-07, D-09).

Settings (URL, topic, enabled) persisted in JSON sidecar file.
Thread-safe read/write (threading.Lock).
Env vars NTFY_URL and NTFY_TOPIC seed defaults when file missing.
If NTFY_URL is empty/unset, ntfy is silently disabled (D-09).

Exports: NtfySettings
"""
import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

# Path to the JSON sidecar file. Override with NTFY_SETTINGS_FILE env var.
NTFY_SETTINGS_FILE = os.getenv(
    "NTFY_SETTINGS_FILE",
    os.path.join(os.path.dirname(__file__), "..", "models", "ntfy_settings.json"),
)

_DEFAULT_NTFY: dict = {"url": "", "topic": "", "enabled": False}


class NtfySettings:
    """Thread-safe ntfy push notification settings.

    Persists URL, topic, and enabled flag in a JSON sidecar file.
    Env vars NTFY_URL and NTFY_TOPIC seed defaults when file is absent (D-07).
    ntfy is silently disabled when URL is empty or enabled is False (D-09).

    Usage::

        settings = NtfySettings()
        if settings.is_enabled():
            # ntfy is configured and active
            pass
        settings.update(url="http://ntfy.home", topic="farm", enabled=True)
        all_settings = settings.get_all()
    """

    def __init__(self, settings_file: str = NTFY_SETTINGS_FILE) -> None:
        self._settings_file = settings_file
        self._lock = threading.Lock()
        self._settings: dict = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Read ntfy settings from the JSON sidecar file.

        If the file does not exist, seeds from NTFY_URL and NTFY_TOPIC env vars.
        If NTFY_URL is non-empty, enabled is set to True automatically (D-07).
        """
        with self._lock:
            try:
                if os.path.exists(self._settings_file):
                    with open(self._settings_file, "r") as f:
                        loaded = json.load(f)
                    merged = dict(_DEFAULT_NTFY)
                    merged.update({k: v for k, v in loaded.items() if k in _DEFAULT_NTFY})
                    self._settings = merged
                    logger.info(
                        "Loaded ntfy settings from %s: url=%s enabled=%s",
                        self._settings_file,
                        self._settings.get("url", ""),
                        self._settings.get("enabled", False),
                    )
                else:
                    # Seed from env vars (D-07)
                    ntfy_url = os.getenv("NTFY_URL", "")
                    ntfy_topic = os.getenv("NTFY_TOPIC", "")
                    self._settings = dict(_DEFAULT_NTFY)
                    self._settings["url"] = ntfy_url
                    self._settings["topic"] = ntfy_topic
                    if ntfy_url:
                        self._settings["enabled"] = True
                    self._save_locked()
                    logger.info(
                        "ntfy settings file not found — seeded from env vars at %s",
                        self._settings_file,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to load ntfy settings from %s: %s — using defaults",
                    self._settings_file,
                    exc,
                )
                self._settings = dict(_DEFAULT_NTFY)

    def save(self) -> None:
        """Write current ntfy settings to the JSON sidecar file (thread-safe)."""
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        """Write settings to file. Caller must hold self._lock."""
        try:
            os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
            with open(self._settings_file, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save ntfy settings to %s: %s", self._settings_file, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return True only when ntfy is configured and active (D-09).

        Returns False when URL is empty/unset or enabled flag is False.
        """
        with self._lock:
            return bool(self._settings.get("enabled")) and bool(self._settings.get("url"))

    def get_all(self) -> dict:
        """Return a copy of the full ntfy settings dict."""
        with self._lock:
            return dict(self._settings)

    def update(self, **kwargs) -> None:
        """Update one or more ntfy settings fields and persist to file.

        Accepted keys: url, topic, enabled.
        Changes take effect immediately — no bridge restart required.
        """
        with self._lock:
            for key, value in kwargs.items():
                if key in _DEFAULT_NTFY:
                    self._settings[key] = value
            self._save_locked()
        logger.info("ntfy settings updated: %s", {k: v for k, v in kwargs.items() if k in _DEFAULT_NTFY})
