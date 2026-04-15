---
phase: 04-onnx-ai-layer-and-recommendation-engine
plan: "01"
subsystem: hub-bridge-inference
tags:
  - onnx
  - feature-aggregation
  - data-maturity
  - synthetic-data
  - ai-06

dependency_graph:
  requires:
    - hub/bridge/main.py (asyncpg pool pattern, INSERT_READING_SQL)
    - hub/bridge/models.py (QualityFlag, SensorPayload)
    - TimescaleDB sensor_readings hypertable
    - TimescaleDB egg_counts table
  provides:
    - hub/bridge/inference/feature_aggregator.py (FeatureAggregator)
    - hub/bridge/inference/maturity_tracker.py (MaturityTracker)
    - hub/bridge/inference/synthetic/generate_synthetic_data.py (CLI generator)
    - scripts/generate_synthetic_data.py (CLI entry point)
    - model_maturity table DDL (CREATE TABLE IF NOT EXISTS)
  affects:
    - Phase 4 plans 02-05 (all ONNX inference depends on FeatureAggregator)
    - hub/bridge/main.py (will integrate MaturityTracker in 04-03)

tech_stack:
  added:
    - onnxruntime==1.23.2 (hub/bridge/requirements.txt)
    - numpy==2.2.6 (hub/bridge/requirements.txt)
    - APScheduler==3.11.2 (hub/bridge/requirements.txt)
    - watchdog==6.0.0 (hub/bridge/requirements.txt)
    - scikit-learn==1.7.2 (scripts/requirements-training.txt)
    - skl2onnx==1.20.0 (scripts/requirements-training.txt)
    - onnx==1.17.0 (scripts/requirements-training.txt)
  patterns:
    - asyncpg pool with AsyncMock for unit testing (no running DB required)
    - Structural SQL filter (quality = 'GOOD' hardcoded in WHERE clause, not parameterized)
    - Fixed-length feature vectors with NaN sentinels for missing sensor types
    - In-memory domain state with DB persistence via upsert

key_files:
  created:
    - hub/bridge/inference/__init__.py
    - hub/bridge/inference/feature_aggregator.py
    - hub/bridge/inference/maturity_tracker.py
    - hub/bridge/inference/synthetic/__init__.py
    - hub/bridge/inference/synthetic/generate_synthetic_data.py
    - hub/bridge/tests/inference/__init__.py
    - hub/bridge/tests/inference/test_feature_aggregator.py
    - hub/bridge/tests/inference/test_maturity_tracker.py
    - scripts/generate_synthetic_data.py
    - scripts/requirements-training.txt
  modified:
    - hub/bridge/requirements.txt (appended onnxruntime, numpy, APScheduler, watchdog)

decisions:
  - "quality = 'GOOD' is a structural WHERE clause filter, never a query parameter (AI-06, D-10)"
  - "build_feature_vector uses NaN sentinels for missing sensors to guarantee fixed ONNX input shape"
  - "MaturityTracker DOMAINS are irrigation, zone_health, flock_anomaly (matching bridge rec types)"
  - "Synthetic generator uses ON CONFLICT DO NOTHING to allow safe re-runs on the same DB"
  - "Synthetic data inserts egg_counts rows alongside coop sensor readings for full flock maturity coverage"

metrics:
  duration_seconds: 270
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 1
  tests_added: 15
---

# Phase 4 Plan 01: Data Foundation and Feature Aggregation Summary

**One-liner:** asyncpg-backed FeatureAggregator with structural GOOD-flag SQL filtering, MaturityTracker persisting per-domain approval counts to TimescaleDB, and a CLI synthetic data generator producing 6+ weeks of realistic multi-zone sensor data (90/7/3% GOOD/SUSPECT/BAD distribution).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Package dependencies, feature aggregator with GOOD-flag filter | 997132f | hub/bridge/inference/feature_aggregator.py, tests/inference/test_feature_aggregator.py, requirements.txt, scripts/requirements-training.txt |
| 2 | Maturity tracker, synthetic data generator, CLI entry point | fe401f6 | hub/bridge/inference/maturity_tracker.py, inference/synthetic/generate_synthetic_data.py, tests/inference/test_maturity_tracker.py, scripts/generate_synthetic_data.py |

## What Was Built

### FeatureAggregator (hub/bridge/inference/feature_aggregator.py)

Queries TimescaleDB for sensor window aggregates with mandatory `quality = 'GOOD'` filtering enforced in the SQL WHERE clause — never as a parameter. This is the single entry point for all ONNX model inputs.

Key methods:
- `aggregate_zone_features(zone_id, sensor_types, window_hours)` — returns per-sensor stats dict or None if below MIN_READINGS threshold (default 10). Enforces the data sufficiency gate.
- `build_feature_vector(aggregated, sensor_types)` — converts stats into a flat `list[float]` of fixed length `len(sensor_types) * 4`. Missing sensors get `[NaN, NaN, NaN, NaN]` sentinels so ONNX always sees consistent input shape.
- `check_data_maturity(zone_id)` — runs the 4-week maturity gate query: `gate_passed = good_ratio >= 0.8 AND data_span_days >= 28`.

### MaturityTracker (hub/bridge/inference/maturity_tracker.py)

Tracks recommendation counts, approval counts, and rejection counts per domain (irrigation, zone_health, flock_anomaly). State is held in memory and persisted to the `model_maturity` TimescaleDB table.

Key methods:
- `ensure_table()` — creates the table on startup
- `load_from_db()` / `persist_to_db()` — DB round-trip for restart safety
- `record_recommendation(domain, rec_id)` / `record_approval(domain)` / `record_rejection(domain)` — in-memory increments
- `get_maturity_state(domain)` / `get_all_maturity_states()` — approval_rate with division-by-zero guard

### Synthetic Data Generator (hub/bridge/inference/synthetic/generate_synthetic_data.py)

CLI tool that generates 6+ weeks of realistic sensor data seeded into TimescaleDB (D-02, D-03):
- Garden zones: moisture (VWC seasonal curve + diurnal + noise), pH (slow drift + noise), temperature (diurnal + seasonal + noise)
- Coop: feed_weight (daily step-down with auto-refill), water_level (daily step-down with auto-refill), nesting_box_weight (laying window pattern by flock size)
- Quality distribution: 90% GOOD, 7% SUSPECT, 3% BAD
- Also inserts egg_counts rows for flock maturity coverage
- CLI args: `--weeks`, `--zones`, `--db-url`, `--flock-size`, `--seed`

Entry point: `scripts/generate_synthetic_data.py` (thin wrapper).

## Tests

15 tests total across 2 test files. All pass with `python -m pytest tests/inference/ -x -q`.

- `test_feature_aggregator.py` (8 tests): GOOD-flag SQL verification, insufficient readings returns None, fixed-length vectors with NaN sentinels, maturity gate true/false conditions
- `test_maturity_tracker.py` (7 tests): increment counts, approval_rate calculation, zero-division guard, DB load/persist round-trip via AsyncMock

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

T-04-01 (Tampering): Synthetic data shares the sensor_readings table with real data. The generator uses `ON CONFLICT DO NOTHING` and is documented as a dev-only tool. Production systems have no path to invoke this script automatically.

T-04-02 (DoS): MIN_READINGS threshold and check_data_maturity gate are implemented and tested. Both prevent inference on insufficient data.

T-04-03 (Information Disclosure): Feature vectors contain only sensor aggregates — no PII, LAN-only system. Accepted as planned.

No new threat surface found beyond the plan's threat model.

## Self-Check: PASSED

- hub/bridge/inference/feature_aggregator.py: FOUND
- hub/bridge/inference/maturity_tracker.py: FOUND
- hub/bridge/inference/synthetic/generate_synthetic_data.py: FOUND
- hub/bridge/tests/inference/test_feature_aggregator.py: FOUND
- hub/bridge/tests/inference/test_maturity_tracker.py: FOUND
- scripts/generate_synthetic_data.py: FOUND
- scripts/requirements-training.txt: FOUND
- hub/bridge/requirements.txt (onnxruntime line): FOUND
- Commit 997132f: FOUND
- Commit fe401f6: FOUND
- All 15 tests: PASSED
