"""Synthetic sensor data generator for bootstrapping the data maturity gate (D-02, D-03).

Generates 6+ weeks of realistic multi-sensor data and inserts it into TimescaleDB.
This is a development/testing tool only. Production systems use real sensor data.

Quality distribution: ~90% GOOD, ~7% SUSPECT, ~3% BAD (realistic noise, D-03).
All synthetic rows have stuck=False.

Usage:
    python generate_synthetic_data.py [--weeks 6] [--zones zone-01,zone-02] [--db-url ...]

The coop zone is always included for flock sensor types.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
from datetime import datetime, timedelta, timezone

import asyncpg

# ---------------------------------------------------------------------------
# DB connection defaults (mirror hub/bridge/main.py)
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "farm")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "farm_local_dev")
DB_NAME = os.getenv("POSTGRES_DB", "farmdb")

INSERT_READING_SQL = """
INSERT INTO sensor_readings
    (time, zone_id, sensor_type, value, quality, stuck, raw_value, calibration_applied, received_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT DO NOTHING
"""

INSERT_EGG_COUNTS_SQL = """
INSERT INTO egg_counts (count_date, estimated_count, raw_weight_grams, updated_at)
VALUES ($1, $2, $3, $4)
ON CONFLICT (count_date) DO UPDATE
  SET estimated_count = EXCLUDED.estimated_count,
      raw_weight_grams = EXCLUDED.raw_weight_grams,
      updated_at = EXCLUDED.updated_at
"""

# ---------------------------------------------------------------------------
# Quality flag distribution (D-03)
# ---------------------------------------------------------------------------
QUALITY_WEIGHTS = [("GOOD", 0.90), ("SUSPECT", 0.07), ("BAD", 0.03)]
_QUALITY_THRESHOLDS = [w for _, w in QUALITY_WEIGHTS]
_QUALITY_LABELS = [q for q, _ in QUALITY_WEIGHTS]


def _pick_quality(rng: random.Random) -> str:
    """Return a quality flag according to the realistic noise distribution."""
    r = rng.random()
    cumulative = 0.0
    for label, weight in zip(_QUALITY_LABELS, _QUALITY_THRESHOLDS):
        cumulative += weight
        if r < cumulative:
            return label
    return "GOOD"


# ---------------------------------------------------------------------------
# Sensor value generators
# ---------------------------------------------------------------------------

def _day_fraction(ts: datetime) -> float:
    """Fraction of the day elapsed [0, 1)."""
    return (ts.hour + ts.minute / 60.0 + ts.second / 3600.0) / 24.0


def _day_of_year(ts: datetime) -> int:
    return ts.timetuple().tm_yday


def _seasonal_swing(ts: datetime) -> float:
    """Seasonal factor in [-1, 1] for northern hemisphere (peak in summer ~day 172)."""
    doy = _day_of_year(ts)
    return math.sin(2 * math.pi * (doy - 80) / 365.0)


def generate_moisture(ts: datetime, rng: random.Random) -> float:
    """VWC (%): base 40% +/- 15% seasonal swing, 5% diurnal cycle, sigma=2.0 noise."""
    seasonal = 40.0 + 15.0 * _seasonal_swing(ts)
    diurnal = 5.0 * math.sin(2 * math.pi * _day_fraction(ts) - math.pi / 2)
    noise = rng.gauss(0.0, 2.0)
    return max(0.0, min(100.0, seasonal + diurnal + noise))


def generate_ph(ts: datetime, rng: random.Random, day_index: int) -> float:
    """pH: base 6.5, slow drift rate 0.01/day, noise sigma=0.1."""
    drift = 0.01 * day_index
    noise = rng.gauss(0.0, 0.1)
    return max(4.0, min(9.0, 6.5 + drift + noise))


def generate_temperature(ts: datetime, rng: random.Random) -> float:
    """Temperature (C): base 22C, 8C diurnal amplitude, 5C seasonal swing, sigma=0.5 noise."""
    seasonal = 5.0 * _seasonal_swing(ts)
    diurnal = 8.0 * math.sin(2 * math.pi * _day_fraction(ts) - math.pi / 2)
    noise = rng.gauss(0.0, 0.5)
    return max(-10.0, min(50.0, 22.0 + seasonal + diurnal + noise))


def generate_feed_weight(
    ts: datetime,
    rng: random.Random,
    current_weight: float,
) -> tuple[float, float]:
    """Feed weight (g): daily step-down ~200g/day, refill when < 1000g.

    Returns (new_weight, value_for_this_hour).
    """
    consume_per_hour = 200.0 / 24.0
    new_weight = max(0.0, current_weight - consume_per_hour)
    if new_weight < 1000.0:
        new_weight = 5000.0  # refill
    noise = rng.gauss(0.0, 20.0)
    return new_weight, max(0.0, new_weight + noise)


def generate_water_level(
    ts: datetime,
    rng: random.Random,
    current_level: float,
) -> tuple[float, float]:
    """Water level (%): daily step-down ~8%/day, refill when < 20%.

    Returns (new_level, value_for_this_hour).
    """
    consume_per_hour = 8.0 / 24.0
    new_level = max(0.0, current_level - consume_per_hour)
    if new_level < 20.0:
        new_level = 100.0  # refill
    noise = rng.gauss(0.0, 0.5)
    return new_level, max(0.0, min(100.0, new_level + noise))


def generate_nesting_box_weight(
    ts: datetime,
    rng: random.Random,
    flock_size: int = 5,
) -> float:
    """Nesting box weight (g): tare 0g, +60g per egg.

    1-5 eggs/day based on flock size. Weight peaks mid-morning and drops after collection.
    """
    day_frac = _day_fraction(ts)
    # Eggs laid between 6am (0.25) and 2pm (0.583)
    eggs_today = max(1, min(flock_size, int(rng.gauss(flock_size * 0.7, 1.0))))
    if 0.25 <= day_frac <= 0.583:
        # Gradual accumulation during laying window
        fraction_through_window = (day_frac - 0.25) / (0.583 - 0.25)
        eggs_present = int(eggs_today * fraction_through_window)
    elif day_frac > 0.583:
        eggs_present = 0  # collected
    else:
        eggs_present = 0  # before laying starts
    noise = rng.gauss(0.0, 5.0)
    return max(0.0, eggs_present * 60.0 + noise)


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

async def generate_zone_readings(
    pool: asyncpg.Pool,
    zone_id: str,
    weeks: int,
    rng: random.Random,
) -> int:
    """Generate garden zone sensor readings (moisture, ph, temperature) and insert."""
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(weeks=weeks)

    readings: list[tuple] = []
    ts = start_ts
    day_index = 0
    last_date = ts.date()

    while ts <= end_ts:
        current_date = ts.date()
        if current_date != last_date:
            day_index += 1
            last_date = current_date

        for sensor_type, value in [
            ("moisture", generate_moisture(ts, rng)),
            ("ph", generate_ph(ts, rng, day_index)),
            ("temperature", generate_temperature(ts, rng)),
        ]:
            quality = _pick_quality(rng)
            readings.append((
                ts,          # time
                zone_id,     # zone_id
                sensor_type, # sensor_type
                round(value, 4),  # value
                quality,     # quality
                False,       # stuck
                round(value, 4),  # raw_value (no calibration applied)
                False,       # calibration_applied
                ts,          # received_at
            ))

        ts += timedelta(hours=1)

    # Batch insert
    async with pool.acquire() as conn:
        await conn.executemany(INSERT_READING_SQL, readings)

    print(f"Generated {len(readings)} readings for zone {zone_id} ({weeks} weeks)")
    return len(readings)


async def generate_coop_readings(
    pool: asyncpg.Pool,
    weeks: int,
    rng: random.Random,
    flock_size: int = 5,
) -> int:
    """Generate coop sensor readings (feed_weight, water_level, nesting_box_weight) and insert."""
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(weeks=weeks)

    readings: list[tuple] = []
    egg_count_rows: list[tuple] = []

    ts = start_ts
    current_feed_weight = 5000.0
    current_water_level = 100.0
    last_egg_date = None
    daily_eggs = 0

    while ts <= end_ts:
        current_date = ts.date()

        # Feed weight
        current_feed_weight, feed_value = generate_feed_weight(ts, rng, current_feed_weight)
        quality = _pick_quality(rng)
        readings.append((ts, "coop", "feed_weight", round(feed_value, 2), quality, False, round(feed_value, 2), False, ts))

        # Water level
        current_water_level, water_value = generate_water_level(ts, rng, current_water_level)
        quality = _pick_quality(rng)
        readings.append((ts, "coop", "water_level", round(water_value, 2), quality, False, round(water_value, 2), False, ts))

        # Nesting box weight
        nesting_weight = generate_nesting_box_weight(ts, rng, flock_size)
        quality = _pick_quality(rng)
        readings.append((ts, "coop", "nesting_box_weight", round(nesting_weight, 2), quality, False, round(nesting_weight, 2), False, ts))

        # Track daily eggs from nesting box (estimate from peak weight)
        if last_egg_date != current_date:
            if last_egg_date is not None:
                # Insert egg count for the previous day
                raw_grams = daily_eggs * 60.0
                egg_count_rows.append((
                    last_egg_date,
                    daily_eggs,
                    round(raw_grams, 1),
                    ts,
                ))
            last_egg_date = current_date
            daily_eggs = max(1, min(flock_size, int(rng.gauss(flock_size * 0.7, 1.0))))

        ts += timedelta(hours=1)

    # Insert final egg count day
    if last_egg_date is not None:
        raw_grams = daily_eggs * 60.0
        egg_count_rows.append((last_egg_date, daily_eggs, round(raw_grams, 1), ts))

    async with pool.acquire() as conn:
        await conn.executemany(INSERT_READING_SQL, readings)
        await conn.executemany(INSERT_EGG_COUNTS_SQL, egg_count_rows)

    print(f"Generated {len(readings)} readings for zone coop ({weeks} weeks)")
    print(f"Inserted {len(egg_count_rows)} egg_counts rows")
    return len(readings)


async def main() -> None:
    """CLI entry point. Parses args, connects to DB, generates synthetic data."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic farm sensor data for development (D-02, D-03)."
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=6,
        help="Number of weeks of data to generate (default: 6)",
    )
    parser.add_argument(
        "--zones",
        type=str,
        default="zone-01,zone-02",
        help="Comma-separated zone IDs for garden zones (default: zone-01,zone-02)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="asyncpg DSN (e.g. postgresql://user:pass@host/db). Defaults to env vars.",
    )
    parser.add_argument(
        "--flock-size",
        type=int,
        default=5,
        help="Number of hens (affects nesting box weight and egg counts, default: 5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()
    rng = random.Random(args.seed)

    zone_list: list[str] = [z.strip() for z in args.zones.split(",") if z.strip()]

    if args.db_url:
        pool = await asyncpg.create_pool(args.db_url, min_size=2, max_size=5)
    else:
        pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            min_size=2,
            max_size=5,
        )

    try:
        total_readings = 0
        for zone_id in zone_list:
            total_readings += await generate_zone_readings(pool, zone_id, args.weeks, rng)

        total_readings += await generate_coop_readings(pool, args.weeks, rng, args.flock_size)

        print(f"\nDone. Total readings inserted: {total_readings}")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
