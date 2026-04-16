CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS sensor_readings (
  time        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  zone_id     TEXT NOT NULL,
  sensor_type TEXT NOT NULL,
  value       DOUBLE PRECISION NOT NULL,
  quality     TEXT NOT NULL CHECK (quality IN ('GOOD', 'SUSPECT', 'BAD')),
  stuck       BOOLEAN NOT NULL DEFAULT FALSE,
  raw_value   DOUBLE PRECISION,
  calibration_applied BOOLEAN NOT NULL DEFAULT FALSE,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('sensor_readings', 'time');

CREATE INDEX idx_sensor_readings_zone ON sensor_readings (zone_id, time DESC);
CREATE INDEX idx_sensor_readings_quality ON sensor_readings (quality, time DESC);

CREATE TABLE IF NOT EXISTS calibration_offsets (
  zone_id     TEXT NOT NULL,
  sensor_type TEXT NOT NULL,
  offset_value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  dry_value   DOUBLE PRECISION,
  wet_value   DOUBLE PRECISION,
  temp_coefficient DOUBLE PRECISION DEFAULT 0.0,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_calibration_date TIMESTAMPTZ,
  PRIMARY KEY (zone_id, sensor_type)
);

CREATE TABLE IF NOT EXISTS zone_config (
  zone_id       TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  plant_type    TEXT,
  soil_type     TEXT,
  target_vwc_min DOUBLE PRECISION,
  target_vwc_max DOUBLE PRECISION,
  target_ph_min  DOUBLE PRECISION,
  target_ph_max  DOUBLE PRECISION,
  irrigation_zone_id TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS node_heartbeats (
  node_id     TEXT NOT NULL,
  heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (node_id, heartbeat_at)
);

SELECT create_hypertable('node_heartbeats', 'heartbeat_at');

-- Phase 3: Flock management tables

CREATE TABLE IF NOT EXISTS flock_config (
  id                          SERIAL PRIMARY KEY,
  breed                       TEXT NOT NULL,
  lay_rate_override           DOUBLE PRECISION,
  hatch_date                  DATE NOT NULL,
  flock_size                  INTEGER NOT NULL,
  supplemental_lighting       BOOLEAN NOT NULL DEFAULT FALSE,
  hen_weight_threshold_grams  DOUBLE PRECISION NOT NULL DEFAULT 1500.0,
  egg_weight_grams            DOUBLE PRECISION NOT NULL DEFAULT 60.0,
  tare_weight_grams           DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  latitude                    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  longitude                   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS egg_counts (
  count_date        DATE PRIMARY KEY,
  estimated_count   INTEGER NOT NULL,
  raw_weight_grams  DOUBLE PRECISION,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feed_daily_consumption (
  consumption_date   DATE PRIMARY KEY,
  consumption_grams  DOUBLE PRECISION,
  refill_detected    BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Phase 5: Hourly rollup continuous aggregate for long-term data retention (D-11)
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    zone_id,
    sensor_type,
    AVG(value)   AS avg_value,
    MIN(value)   AS min_value,
    MAX(value)   AS max_value,
    COUNT(*)     AS reading_count
FROM sensor_readings
WHERE quality = 'GOOD'
GROUP BY bucket, zone_id, sensor_type
WITH NO DATA;

-- Cagg refresh policy: start_offset 7 days MUST be < raw retention 90 days (Pitfall 1)
SELECT add_continuous_aggregate_policy('sensor_readings_hourly',
    start_offset      => INTERVAL '7 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Raw data retention: 90 days (D-10)
SELECT add_retention_policy('sensor_readings', INTERVAL '90 days');

-- Rollup retention: 2 years / 730 days (D-11)
SELECT add_retention_policy('sensor_readings_hourly', INTERVAL '730 days');
