-- Phase 5: Operational Hardening — calibration date tracking and data retention (D-03, D-10, D-11)
--
-- Run-once migration for existing deployments.
-- ADD COLUMN IF NOT EXISTS is idempotent.
-- Continuous aggregate and retention policy DDL use DO blocks with EXCEPTION handlers
-- for idempotency (TimescaleDB does NOT support IF NOT EXISTS on cagg creation).

-- Phase 5: pH calibration date tracking (D-03)
ALTER TABLE calibration_offsets
  ADD COLUMN IF NOT EXISTS last_calibration_date TIMESTAMPTZ;

-- Phase 5: Hourly rollup continuous aggregate (D-11)
-- Wrapped in DO block for idempotency (TimescaleDB has no CREATE MATERIALIZED VIEW IF NOT EXISTS for caggs).
DO $$
BEGIN
  CREATE MATERIALIZED VIEW sensor_readings_hourly
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
EXCEPTION
  WHEN duplicate_table THEN
    RAISE NOTICE 'sensor_readings_hourly already exists, skipping creation.';
END;
$$;

-- Cagg refresh policy: start_offset 7 days MUST be < raw retention 90 days (Pitfall 1).
-- Wrapped in DO block for idempotency.
DO $$
BEGIN
  PERFORM add_continuous_aggregate_policy('sensor_readings_hourly',
      start_offset      => INTERVAL '7 days',
      end_offset        => INTERVAL '1 hour',
      schedule_interval => INTERVAL '1 hour'
  );
EXCEPTION
  WHEN others THEN
    RAISE NOTICE 'Continuous aggregate policy for sensor_readings_hourly may already exist: %', SQLERRM;
END;
$$;

-- Raw data retention: 90 days (D-10).
-- Wrapped in DO block for idempotency.
DO $$
BEGIN
  PERFORM add_retention_policy('sensor_readings', INTERVAL '90 days');
EXCEPTION
  WHEN others THEN
    RAISE NOTICE 'Retention policy for sensor_readings may already exist: %', SQLERRM;
END;
$$;

-- Rollup retention: 2 years / 730 days (D-11).
-- Wrapped in DO block for idempotency.
DO $$
BEGIN
  PERFORM add_retention_policy('sensor_readings_hourly', INTERVAL '730 days');
EXCEPTION
  WHEN others THEN
    RAISE NOTICE 'Retention policy for sensor_readings_hourly may already exist: %', SQLERRM;
END;
$$;
