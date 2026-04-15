---
phase: 04-onnx-ai-layer-and-recommendation-engine
plan: "03"
subsystem: inference-integration
tags: [inference, scheduler, apscheduler, watchdog, ai-settings, bridge, api]
dependency_graph:
  requires: [04-01, 04-02]
  provides: [inference-scheduler, ai-settings-toggle, model-watcher, inference-api-endpoints]
  affects: [hub/bridge/main.py, hub/api/main.py]
tech_stack:
  added:
    - apscheduler==3.11.2 (AsyncIOScheduler for interval+cron inference jobs)
    - watchdog==6.0.0 (filesystem event observer for .onnx hot-reload)
  patterns:
    - APScheduler AsyncIOScheduler attaches to existing event loop (no extra gather() coroutine)
    - Thread-safe JSON sidecar for settings (threading.Lock over file I/O)
    - Watchdog daemon thread compatible with asyncio bridge
    - Bridge-proxy pattern for API-to-bridge cross-process HTTP (aiohttp PATCH/GET)
key_files:
  created:
    - hub/bridge/inference/ai_settings.py
    - hub/bridge/inference/inference_scheduler.py
    - hub/bridge/inference/model_watcher.py
    - hub/api/inference_settings_router.py
  modified:
    - hub/bridge/main.py
    - hub/api/main.py
decisions:
  - "APScheduler runs cooperatively in asyncio event loop — no additional gather() coroutine needed"
  - "trigger_zone_reinference() uses asyncio.create_task() since _evaluate_phase2 is async"
  - "maturity_tracker wired to both _handle_approve and _handle_reject using domain=irrigation as the rule-engine recommendation type"
  - "Model watcher ignores *.prev.onnx files to avoid spurious reloads during training versioning"
metrics:
  duration_seconds: 268
  completed_date: "2026-04-15"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 04 Plan 03: Inference Engine Integration Summary

**One-liner:** APScheduler inference scheduler with weekly retraining, watchdog .onnx hot-reload, AI/Rules toggle persisted to JSON sidecar, and threshold-crossing re-inference wired into the bridge pipeline.

## What Was Built

### Task 1: AI Settings, Inference Scheduler, Model Watcher

**hub/bridge/inference/ai_settings.py** — `AISettings` class with thread-safe (threading.Lock) JSON sidecar persistence. Default state is all domains on "rules" (D-11 cold-start requirement). `set_mode()` validates domain and mode values, writes to file immediately, takes effect on next inference cycle (D-06). `get_mode()` returns "rules" for unknown domains (safe fallback).

**hub/bridge/inference/inference_scheduler.py** — `InferenceScheduler` using `APScheduler AsyncIOScheduler` with `coalesce=True, max_instances=1` job defaults. Registers six jobs:
- Inference: zone_health (every 15 min), irrigation (every 1 hour), flock_anomaly (every 30 min)
- Weekly retraining cron (D-07): retrain_zone_health (Sun 02:00), retrain_irrigation (Sun 02:20), retrain_flock_anomaly (Sun 02:40) — staggered by 20 min to avoid hub CPU contention

Each inference method checks: AI/Rules toggle (D-06), model loaded (D-04 fallback), data maturity gate (D-01) before running. `trigger_zone_reinference(zone_id)` provides immediate re-inference on threshold crossing.

Weekly retrain methods call `fetch_training_data()` then `train_and_export()` for each domain. Model watcher detects the new .onnx automatically — no manual reload needed.

**hub/bridge/inference/model_watcher.py** — `OnnxModelHandler(PatternMatchingEventHandler)` watches `*.onnx` files, ignores `*.prev.onnx` (archiving artifacts). Validates with `onnx.checker.check_model()` before calling `InferenceService.reload()`. `start_model_watcher()` returns the running `Observer` (daemon thread, asyncio-compatible per D-09).

### Task 2: Bridge Integration and API Endpoint

**hub/bridge/main.py** modifications:
- Phase 4 imports: FeatureAggregator, InferenceService, InferenceScheduler, MaturityTracker, AISettings, start_model_watcher
- Module-level: `ai_settings = AISettings()`, `inference_scheduler = None`, `_maturity_tracker = None`
- `main()`: initializes MaturityTracker (ensures table, loads from DB), InferenceService x3, InferenceScheduler (starts), start_model_watcher
- `_evaluate_phase2()`: after rule engine produces recommendation (threshold crossing), calls `asyncio.create_task(inference_scheduler.trigger_zone_reinference(zone_id))` (AI-03)
- `_handle_approve()`: calls `_maturity_tracker.record_approval("irrigation")` + persist (AI-07)
- `_handle_reject()`: calls `_maturity_tracker.record_rejection("irrigation")` + persist (AI-07)
- New internal HTTP handlers: GET `/internal/ai-settings`, PATCH `/internal/ai-settings`, GET `/internal/model-maturity`

**hub/api/inference_settings_router.py** — FastAPI router proxying to bridge:
- `GET /api/settings/ai` — return all domain toggle states
- `PATCH /api/settings/ai` — update domain toggle (Pydantic BaseModel validates domain/mode, T-04-08)
- `GET /api/model-maturity` — return domain maturity + per-zone data maturity

**hub/api/main.py** — `app.include_router(inference_settings_router)` added.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers:
- T-04-08: Pydantic BaseModel on AISettingsPatch validates domain/mode at API boundary; bridge AISettings.set_mode() validates again with ValueError (defense in depth)
- T-04-09: APScheduler coalesce=True, max_instances=1, retraining staggered by 20 min
- T-04-10: ai_settings.json only writable by bridge process

## Self-Check: PASSED

All created files verified present on disk. Both task commits exist:
- `23731c4` feat(04-03): AI settings persistence, inference scheduler with weekly retraining, and model watcher
- `48843be` feat(04-03): bridge main.py inference integration, API settings endpoint
