"""Flock configuration store — reads flock settings from flock_config table.

Falls back to sensible defaults if no database row exists.
Mirrors the zone_config.py pattern exactly.
"""
import logging
from dataclasses import dataclass
from datetime import date

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class FlockConfig:
    breed: str = "Rhode Island Red"
    lay_rate_override: float | None = None
    hatch_date: date = None  # type: ignore[assignment]
    flock_size: int = 6
    supplemental_lighting: bool = False
    hen_weight_threshold_grams: float = 1500.0
    egg_weight_grams: float = 60.0
    tare_weight_grams: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0

    def __post_init__(self):
        if self.hatch_date is None:
            self.hatch_date = date.today()


class FlockConfigStore:
    def __init__(self):
        self._config: FlockConfig = FlockConfig()

    async def load_from_db(self, pool: asyncpg.Pool):
        """Load flock config from database. Uses defaults if no row exists."""
        try:
            row = await pool.fetchrow(
                "SELECT breed, lay_rate_override, hatch_date, flock_size, "
                "supplemental_lighting, hen_weight_threshold_grams, egg_weight_grams, "
                "tare_weight_grams, latitude, longitude "
                "FROM flock_config ORDER BY id DESC LIMIT 1"
            )
            if row:
                self._config = FlockConfig(
                    breed=row["breed"],
                    lay_rate_override=row["lay_rate_override"],
                    hatch_date=row["hatch_date"],
                    flock_size=row["flock_size"],
                    supplemental_lighting=row["supplemental_lighting"],
                    hen_weight_threshold_grams=row["hen_weight_threshold_grams"],
                    egg_weight_grams=row["egg_weight_grams"],
                    tare_weight_grams=row["tare_weight_grams"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                )
                logger.info("Loaded flock config from database (breed=%s, flock_size=%d)",
                            self._config.breed, self._config.flock_size)
            else:
                logger.info("No flock config row found — using defaults")
        except Exception as e:
            logger.warning("Failed to load flock config from database: %s — using defaults", e)

    def get(self) -> FlockConfig:
        """Return current flock config (defaults if not loaded from DB)."""
        return self._config
