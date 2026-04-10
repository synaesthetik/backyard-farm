"""Zone configuration store — reads thresholds and targets from zone_configs table.

Falls back to env var defaults if no database row exists for a zone.
"""
import os
import logging
from dataclasses import dataclass, field

import asyncpg

logger = logging.getLogger(__name__)

VWC_LOW_DEFAULT = float(os.getenv("VWC_LOW_THRESHOLD", "30.0"))
VWC_HIGH_DEFAULT = float(os.getenv("VWC_HIGH_THRESHOLD", "60.0"))
PH_LOW_DEFAULT = float(os.getenv("PH_LOW_THRESHOLD", "6.0"))
PH_HIGH_DEFAULT = float(os.getenv("PH_HIGH_THRESHOLD", "7.5"))
TEMP_LOW_DEFAULT = float(os.getenv("TEMP_LOW_THRESHOLD", "5.0"))
TEMP_HIGH_DEFAULT = float(os.getenv("TEMP_HIGH_THRESHOLD", "40.0"))
FEED_LOW_THRESHOLD_PCT = float(os.getenv("FEED_LOW_THRESHOLD_PCT", "20.0"))
WATER_LOW_THRESHOLD_PCT = float(os.getenv("WATER_LOW_THRESHOLD_PCT", "20.0"))
FEED_MAX_WEIGHT_GRAMS = float(os.getenv("FEED_MAX_WEIGHT_GRAMS", "5000.0"))
WATER_MAX_LEVEL = float(os.getenv("WATER_MAX_LEVEL", "100.0"))


@dataclass
class ZoneConfig:
    zone_id: str
    vwc_low_threshold: float = VWC_LOW_DEFAULT
    vwc_high_threshold: float = VWC_HIGH_DEFAULT
    ph_low_threshold: float = PH_LOW_DEFAULT
    ph_high_threshold: float = PH_HIGH_DEFAULT
    temp_low_threshold: float = TEMP_LOW_DEFAULT
    temp_high_threshold: float = TEMP_HIGH_DEFAULT


class ZoneConfigStore:
    def __init__(self):
        self._configs: dict[str, ZoneConfig] = {}

    async def load_from_db(self, pool: asyncpg.Pool):
        """Load zone configs from database. Creates table if not exists."""
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS zone_configs (
                zone_id TEXT PRIMARY KEY,
                vwc_low_threshold FLOAT DEFAULT %s,
                vwc_high_threshold FLOAT DEFAULT %s,
                ph_low_threshold FLOAT DEFAULT %s,
                ph_high_threshold FLOAT DEFAULT %s,
                temp_low_threshold FLOAT DEFAULT %s,
                temp_high_threshold FLOAT DEFAULT %s
            )
        """ % (VWC_LOW_DEFAULT, VWC_HIGH_DEFAULT, PH_LOW_DEFAULT,
               PH_HIGH_DEFAULT, TEMP_LOW_DEFAULT, TEMP_HIGH_DEFAULT))
        rows = await pool.fetch("SELECT * FROM zone_configs")
        for row in rows:
            self._configs[row["zone_id"]] = ZoneConfig(
                zone_id=row["zone_id"],
                vwc_low_threshold=row["vwc_low_threshold"],
                vwc_high_threshold=row["vwc_high_threshold"],
                ph_low_threshold=row["ph_low_threshold"],
                ph_high_threshold=row["ph_high_threshold"],
                temp_low_threshold=row["temp_low_threshold"],
                temp_high_threshold=row["temp_high_threshold"],
            )
        logger.info("Loaded %d zone configs from database", len(self._configs))

    def get(self, zone_id: str) -> ZoneConfig:
        """Get zone config, returning defaults if no DB row exists."""
        return self._configs.get(zone_id, ZoneConfig(zone_id=zone_id))
