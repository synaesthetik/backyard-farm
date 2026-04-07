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
