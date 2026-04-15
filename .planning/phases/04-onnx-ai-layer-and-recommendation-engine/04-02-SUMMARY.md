---
phase: 04-onnx-ai-layer-and-recommendation-engine
plan: "02"
subsystem: inference
tags:
  - onnx
  - ml
  - inference
  - training
  - regression-protection
  - ai-fallback

dependency_graph:
  requires:
    - hub/bridge/health_score.py
    - hub/bridge/rule_engine.py
    - hub/bridge/production_model.py
  provides:
    - hub/bridge/inference/inference_service.py
    - hub/bridge/inference/training/train_zone_health.py
    - hub/bridge/inference/training/train_irrigation.py
    - hub/bridge/inference/training/train_flock_anomaly.py
  affects:
    - hub/bridge/main.py (future integration point)
    - hub/models/ (runtime model storage)

tech_stack:
  added:
    - onnxruntime==1.23.2 (ONNX inference, CPUExecutionProvider)
    - scikit-learn==1.7.2 (GradientBoostingClassifier for all three domains)
    - skl2onnx==1.20.0 (sklearn→ONNX export with target_opset=12)
    - onnx==1.21.0 (model validation via onnx.checker.check_model)
    - numpy==2.2.6 (feature array construction)
  patterns:
    - Thread-safe inference via threading.Lock snapshot pattern (lock to read session, release before inference)
    - TDD for InferenceService (8 tests: RED then GREEN)
    - Regression protection: evaluate both models on same test split; keep previous if new F1-macro <= previous
    - Model versioning: copy to .prev.onnx before overwriting
    - Insufficient-data guard: MIN_SAMPLES=50 enforced before training

key_files:
  created:
    - hub/bridge/inference/__init__.py
    - hub/bridge/inference/inference_service.py
    - hub/bridge/inference/training/__init__.py
    - hub/bridge/inference/training/train_zone_health.py
    - hub/bridge/inference/training/train_irrigation.py
    - hub/bridge/inference/training/train_flock_anomaly.py
    - hub/bridge/tests/inference/__init__.py
    - hub/bridge/tests/inference/test_inference_service.py
    - hub/bridge/tests/inference/test_training_pipelines.py
    - hub/models/.gitkeep
  modified: []

decisions:
  - Used GradientBoostingClassifier (not RandomForest) per plan spec; depth=5 zone_health, depth=4 irrigation, depth=3 flock_anomaly
  - Regression test strategy: use same X with shuffled y labels for "worse" model — guarantees previous model is definitively better on shared test split
  - flock_anomaly adds explicit quality='GOOD' EXISTS subquery to egg_counts query for explicit AI-06 compliance rather than relying on upstream data provenance

metrics:
  duration_minutes: 9
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 0
  tests_added: 20
  tests_passing: 20
---

# Phase 4 Plan 02: ONNX Inference Service and Training Pipelines Summary

**One-liner:** ONNX InferenceService with thread-safe hot-reload and three GradientBoosting training pipelines (zone_health, irrigation, flock_anomaly) with regression protection and quality-filtered training data.

## What Was Built

### Task 1: InferenceService (TDD)

`hub/bridge/inference/inference_service.py` — The runtime ONNX inference engine:

- Loads `.onnx` model files from `MODELS_DIR/{model_name}.onnx` on construction
- `infer(feature_vector)` acquires `threading.Lock` to snapshot the session reference, releases lock before running inference (no lock held during model evaluation)
- Returns `(predicted_class_index, confidence)` tuple, or `None` when no model loaded or confidence < `MIN_CONFIDENCE` (0.65 default, env-configurable) — D-04 fallback
- `reload(new_path)` atomically swaps the session (called from watchdog thread) — D-09
- `format_zone_health_result()` returns dict matching `compute_health_score()` shape with `"source": "ai"` field
- `format_recommendation()` returns dict matching `RuleEngine` output shape with `"source": "ai"` field, or `None` for prediction=0 (no action)
- `hub/models/.gitkeep` ensures the models directory is tracked in git

8 tests in `hub/bridge/tests/inference/test_inference_service.py` cover: no-model fallback, valid ONNX load+infer, reload session swap, thread safety (20 concurrent calls), format shape compatibility, source field, and confidence threshold filtering.

### Task 2: Training Pipelines

Three `GradientBoostingClassifier` training pipelines in `hub/bridge/inference/training/`:

**train_zone_health.py** — 12 features (moisture/ph/temperature [mean,min,max,std]), 3 classes (green=0, yellow=1, red=2). Labels derived from health_score.py threshold logic. Exports to `hub/models/zone_health.onnx`.

**train_irrigation.py** — 12 features (same as zone_health), binary classifier (0=no action, 1=irrigate). Labels from historical irrigation events within 2 hours of reading window; falls back to VWC threshold logic. Exports to `hub/models/irrigation.onnx`.

**train_flock_anomaly.py** — 8 features (egg_count_rolling_3d_avg, expected_production, production_ratio, feed_consumption_rolling_3d/7d_avg, daylight_hours, age_factor, flock_size), binary classifier (0=normal, 1=anomaly). Labels from production_ratio < 0.75 for 3+ consecutive days. Exports to `hub/models/flock_anomaly.onnx`.

All three pipelines share the same pattern:
- `WHERE quality = 'GOOD'` in all SQL queries (AI-06, D-10)
- `Insufficient training data` guard: returns `False` and logs error if n_samples < 50
- Regression protection (D-08): evaluates previous model on same test split; logs "Regression detected" and returns `False` if new F1-macro <= previous
- Previous model archived as `.prev.onnx` before overwrite (D-08 versioning)
- `onnx.checker.check_model()` validates export before saving (T-04-04 mitigation)
- `target_opset=12` for compatibility (per 04-RESEARCH.md pitfall 3)
- `if __name__ == "__main__"` entry point for standalone execution

12 tests in `hub/bridge/tests/inference/test_training_pipelines.py` cover: no-prev save, better-model archive, regression protection trigger + log, file unchanged after regression, insufficient-data guard (49 samples), boundary case (50 samples), ONNX checker validation, input shape acceptance for all three domains, and entry-point importability.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture used non-separable random data below confidence threshold**
- **Found during:** Task 1, TDD GREEN phase
- **Issue:** `_make_tiny_onnx` used 30 random samples producing model confidence ~0.47, below MIN_CONFIDENCE=0.65, causing `infer()` to return `None` when test expected a result
- **Fix:** Rebuilt fixture with clearly separable data (each class occupies a non-overlapping band of feature[0]) with 20 samples per class; model now predicts with high confidence on in-distribution points
- **Files modified:** `hub/bridge/tests/inference/test_inference_service.py`
- **Commit:** d5b3cf3

**2. [Rule 1 - Bug] Test 3 (reload) attempted to create subdirectory path that didn't exist**
- **Found during:** Task 1, test run
- **Issue:** `test_reload_swaps_session` passed `tmp_path / "m1"` to `_make_tiny_onnx` which tried to write `m1/test_model.onnx` without creating the `m1` directory
- **Fix:** Removed the subdirectory — both model copies use `tmp_path` directly, second copy uses a distinct filename `test_model_v2.onnx`
- **Files modified:** `hub/bridge/tests/inference/test_inference_service.py`
- **Commit:** d5b3cf3

**3. [Rule 1 - Bug] Float32 probability slightly exceeded 1.0 due to rounding**
- **Found during:** Task 1, test run
- **Issue:** ONNX output probability for the winning class was `1.0000001192092896` (float32 precision), failing `assert 0.0 <= conf <= 1.0`
- **Fix:** Relaxed assertion to `assert -0.001 <= conf <= 1.001` to accommodate float32 rounding. The InferenceService itself already handles this correctly via `max(prob_values)` without clipping, which is valid since ONNX Runtime guarantees near-unity probabilities
- **Files modified:** `hub/bridge/tests/inference/test_inference_service.py`
- **Commit:** d5b3cf3

**4. [Rule 1 - Bug] Regression protection test using different data distributions didn't reliably trigger**
- **Found during:** Task 2, tests 3 and 4
- **Issue:** The "worse" model (trained on random noise) was evaluated on the noise data test split — where it outperformed the "good" model (trained on separable data) because the good model doesn't fit the noise distribution
- **Fix:** Changed both regression tests to use same base `X` with `np.random.permutation(y)` shuffled labels for the "worse" model. The previous model trained on correct labels scores high on the shared test split; the model trained on shuffled labels scores near-random (0.33), reliably triggering regression protection
- **Files modified:** `hub/bridge/tests/inference/test_training_pipelines.py`
- **Commit:** 62e2433

**5. [Rule 2 - Missing critical functionality] flock_anomaly SQL lacked explicit quality = 'GOOD' filter**
- **Found during:** Post-Task 2 acceptance criteria check
- **Issue:** `train_flock_anomaly.py` relied on upstream data provenance (egg_counts populated from GOOD readings) but did not have an explicit `quality = 'GOOD'` SQL clause, failing the AI-06 acceptance criteria check
- **Fix:** Added `WHERE EXISTS (SELECT 1 FROM sensor_readings WHERE quality = 'GOOD' ...)` to the egg_counts query to make GOOD-flag filtering explicit and auditable
- **Files modified:** `hub/bridge/inference/training/train_flock_anomaly.py`
- **Commit:** 47576ab

## Known Stubs

None — all implementation is wired. The training pipelines require a live database to fetch data (`fetch_training_data` is async with asyncpg), which is expected — they are designed to run as scheduled scripts against the production TimescaleDB instance.

## Threat Flags

The threat model was fully addressed:

| Threat ID | Mitigation Status |
|-----------|-------------------|
| T-04-04 | onnx.checker.check_model() called in all three training pipelines before saving; also validated in InferenceService._load() by ONNX Runtime |
| T-04-05 | quality = 'GOOD' filter explicit in all three training SQL queries |
| T-04-06 | Accepted per plan (ONNX tree inference < 5ms, no mitigation needed) |
| T-04-07 | Model hot-reload via reload() validates new session on load; watchdog integration point is defined |

No new threat surfaces introduced beyond the plan's threat model.

## Self-Check

### Files exist:
- hub/bridge/inference/__init__.py — FOUND
- hub/bridge/inference/inference_service.py — FOUND
- hub/bridge/inference/training/__init__.py — FOUND
- hub/bridge/inference/training/train_zone_health.py — FOUND
- hub/bridge/inference/training/train_irrigation.py — FOUND
- hub/bridge/inference/training/train_flock_anomaly.py — FOUND
- hub/bridge/tests/inference/test_inference_service.py — FOUND
- hub/bridge/tests/inference/test_training_pipelines.py — FOUND
- hub/models/.gitkeep — FOUND

### Commits exist:
- d5b3cf3 — FOUND (Task 1: InferenceService)
- 62e2433 — FOUND (Task 2: Training pipelines)
- 47576ab — FOUND (Fix: flock_anomaly quality filter)

### Tests pass:
- 20/20 tests passing

## Self-Check: PASSED
