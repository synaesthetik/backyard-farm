---
phase: 4
slug: onnx-ai-layer-and-recommendation-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 04-01-01 | 01 | 1 | AI-06 | — | GOOD-flag filter enforced | unit | `pytest tests/test_feature_aggregation.py` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | AI-03 | — | N/A (spike) | manual | benchmark script output | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | AI-03 | — | Model produces recommendation dicts | unit | `pytest tests/test_onnx_inference.py` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | AI-03 | — | Flock anomaly signals feed alert engine | unit | `pytest tests/test_flock_anomaly.py` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 3 | AI-07 | — | Maturity indicator renders | component | `npx vitest run --reporter=verbose` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `hub/bridge/tests/test_feature_aggregation.py` — stubs for AI-06 feature window tests
- [ ] `hub/bridge/tests/test_onnx_inference.py` — stubs for AI-03 inference output shape tests
- [ ] `hub/bridge/tests/test_flock_anomaly.py` — stubs for flock anomaly detection tests
- [ ] `onnxruntime` added to hub/bridge requirements — if not already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI Status card renders on Home tab | AI-07 | Visual layout and responsive behavior | Open dashboard, verify card appears with maturity progress per domain |
| ONNX/Rules toggle works at runtime | D-05 | Runtime state change in browser | Toggle AI/Rules on settings page, verify next inference uses selected engine |
| Model hot-reload picks up new .onnx file | D-09 | Filesystem watch behavior | Drop new .onnx file in models/, verify bridge loads it without restart |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
