"""AI/Rules engine toggle persistence (D-05, D-06, D-11).

Per-domain toggle state is persisted in a JSON sidecar file so the bridge
can read it on startup and after in-place updates. Reads and writes are
protected by a threading.Lock because watchdog and the aiohttp request
handler run in different threads.

Default state: all domains use "rules" (D-11 — rule engine during cold start).
Toggle changes take effect on the next inference cycle (D-06 — no restart needed).

Exports: AISettings
"""
import json
import logging
import os
import threading
from typing import Literal

logger = logging.getLogger(__name__)

# Path to the JSON sidecar file. Override with AI_SETTINGS_FILE env var.
SETTINGS_FILE = os.getenv(
    "AI_SETTINGS_FILE",
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "ai_settings.json"),
)

VALID_DOMAINS = frozenset(["irrigation", "zone_health", "flock_anomaly"])
VALID_MODES = frozenset(["ai", "rules"])

_DEFAULT_SETTINGS: dict[str, str] = {
    "irrigation": "rules",
    "zone_health": "rules",
    "flock_anomaly": "rules",
}


class AISettings:
    """Thread-safe AI/Rules toggle state for all three inference domains.

    Usage::

        settings = AISettings()
        mode = settings.get_mode("irrigation")   # "ai" or "rules"
        settings.set_mode("irrigation", "ai")    # takes effect on next cycle (D-06)
        all_settings = settings.get_all()
    """

    def __init__(self, settings_file: str = SETTINGS_FILE) -> None:
        self._settings_file = settings_file
        self._lock = threading.Lock()
        self._settings: dict[str, str] = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Read toggle state from the JSON sidecar file.

        If the file does not exist, initialises with defaults and writes the
        file so subsequent reads do not recreate it.
        """
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
                if os.path.exists(self._settings_file):
                    with open(self._settings_file, "r") as f:
                        loaded = json.load(f)
                    # Merge with defaults to handle new domains added after first write
                    merged = dict(_DEFAULT_SETTINGS)
                    for domain, mode in loaded.items():
                        if domain in VALID_DOMAINS and mode in VALID_MODES:
                            merged[domain] = mode
                    self._settings = merged
                    logger.info("Loaded AI settings from %s: %s", self._settings_file, self._settings)
                else:
                    self._settings = dict(_DEFAULT_SETTINGS)
                    self._save_locked()
                    logger.info(
                        "AI settings file not found — created with defaults at %s",
                        self._settings_file,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to load AI settings from %s: %s — using defaults",
                    self._settings_file, exc,
                )
                self._settings = dict(_DEFAULT_SETTINGS)

    def save(self) -> None:
        """Write current toggle state to the JSON sidecar file (thread-safe)."""
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        """Write state to file. Caller must hold self._lock."""
        try:
            os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
            with open(self._settings_file, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save AI settings to %s: %s", self._settings_file, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_mode(self, domain: str) -> str:
        """Return the current mode for *domain* — either "ai" or "rules".

        Unknown domains always return "rules" (safe fallback, D-11).
        """
        with self._lock:
            return self._settings.get(domain, "rules")

    def set_mode(self, domain: str, mode: str) -> None:
        """Update the toggle for *domain* to *mode*.

        The change is written to the JSON file immediately and takes effect on
        the next inference cycle (D-06 — no bridge restart required).

        Args:
            domain: One of "irrigation", "zone_health", "flock_anomaly".
            mode: "ai" or "rules".

        Raises:
            ValueError: If domain or mode is not a recognised value.
        """
        if domain not in VALID_DOMAINS:
            raise ValueError(f"Unknown AI domain: {domain!r}. Must be one of {sorted(VALID_DOMAINS)}")
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown AI mode: {mode!r}. Must be one of {sorted(VALID_MODES)}")

        with self._lock:
            self._settings[domain] = mode
            self._save_locked()

        logger.info("AI settings updated: %s -> %s (takes effect on next inference cycle)", domain, mode)

    def get_all(self) -> dict[str, str]:
        """Return a copy of the full toggle state dict."""
        with self._lock:
            return dict(self._settings)
