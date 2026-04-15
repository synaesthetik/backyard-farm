---
phase: 4
slug: onnx-ai-layer-and-recommendation-engine
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python backend), vitest (Svelte dashboard) |
| **Config file** | hub/bridge/pytest.ini, hub/dashboard/vitest.config.ts |
| **Quick run command** | `cd hub/bridge && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd hub/bridge && python -m pytest tests/ -v && cd ../../hub/dashboard && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd hub/bridge && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | AI-06 | — | GOOD-flag filter enforced | unit | `pytest tests/inference/test_feature_aggregator.py` | TDD | ⬜ pending |
| 04-01-02 | 01 | 1 | AI-06 | — | Maturity tracking persists | unit | `pytest tests/inference/test_maturity_tracker.py` | TDD | ⬜ pending |
| 04-02-01 | 02 | 1 | AI-03 | — | ONNX inference produces recommendation dicts | unit | `pytest tests/inference/test_inference_service.py` | TDD | ⬜ pending |
| 04-02-02 | 02 | 1 | AI-03 | — | Training pipelines with regression protection | unit | `pytest tests/inference/test_training_pipelines.py` | TDD | ⬜ pending |
| 04-03-01 | 03 | 2 | AI-03 | — | Scheduler runs inference jobs + weekly retraining | structural | `python -c "from inference.inference_scheduler import InferenceScheduler; print('OK')"` | plan-created | ⬜ pending |
| 04-04-01 | 04 | 3 | AI-07 | — | AI Status card and toggle render | component | `npx vitest run --reporter=verbose` | TDD | ⬜ pending |
| 04-05-01 | 05 | 4 | AI-07 | — | End-to-end integration | manual | browser verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No separate Wave 0 plan required. Plans 04-01 and 04-02 use TDD-style tasks that create tests and implementation atomically within Wave 1. Test files are created by the implementing tasks themselves.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI Status card renders on Home tab | AI-07 | Visual layout and responsive behavior | Open dashboard, verify card appears with maturity progress per domain |
| ONNX/Rules toggle works at runtime | D-05 | Runtime state change in browser | Toggle AI/Rules on settings page, verify next inference uses selected engine |
| Model hot-reload picks up new .onnx file | D-09 | Filesystem watch behavior | Drop new .onnx file in models/, verify bridge loads it without restart |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or TDD-created tests
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not needed — TDD tasks create tests atomically
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
