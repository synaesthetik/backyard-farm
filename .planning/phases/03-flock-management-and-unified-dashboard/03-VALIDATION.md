---
phase: 3
slug: flock-management-and-unified-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 + pytest-asyncio 0.25.3 (Python bridge); Vitest 3.1.1 + @testing-library/svelte 5.2.6 (dashboard) |
| **Config file** | `hub/bridge/tests/conftest.py` (Python); `hub/dashboard/vitest.config.ts` (dashboard) |
| **Quick run command** | `cd hub/bridge && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd hub/bridge && python -m pytest tests/ -v` + `cd hub/dashboard && npx vitest run --reporter=verbose` |
| **Estimated runtime** | ~10 seconds (Python); ~8 seconds (dashboard) |

---

## Sampling Rate

- **After every task commit:** Run `cd hub/bridge && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite: Python + `cd hub/dashboard && npx vitest run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | FLOCK-01 | — | N/A | unit | `pytest tests/test_egg_estimator.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | FLOCK-02 | — | N/A | unit | `pytest tests/test_production_model.py -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | FLOCK-06 | — | N/A | unit | `pytest tests/test_feed_consumption.py -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | FLOCK-04 | — | Alert fires <75%, clears >85% | unit | `pytest tests/test_production_model.py::test_alert_threshold -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | UI-01 | — | N/A | unit | `npx vitest run src/lib/FlockSummaryCard.test.ts` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | FLOCK-03 | — | N/A | unit | `npx vitest run src/lib/ProductionChart.test.ts` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | FLOCK-05 | — | N/A | unit | `npx vitest run src/lib/FlockSettings.test.ts` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 3 | All | — | N/A | manual | Human checkpoint | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `hub/bridge/tests/test_egg_estimator.py` — stubs for FLOCK-01 (egg weight → count, hen subtraction)
- [ ] `hub/bridge/tests/test_production_model.py` — stubs for FLOCK-02 (model arithmetic), FLOCK-04 (alert threshold)
- [ ] `hub/bridge/tests/test_feed_consumption.py` — stubs for FLOCK-06 (delta derivation, refill detection)
- [ ] `hub/dashboard/src/lib/ProductionChart.test.ts` — stubs for FLOCK-03 (two-series chart)
- [ ] `hub/dashboard/src/lib/FlockSummaryCard.test.ts` — stubs for UI-01 (home tab flock summary)
- [ ] `hub/dashboard/src/lib/FlockSettings.test.ts` — stubs for FLOCK-05 (breed select, validation)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flock config CRUD via API | FLOCK-05 | Requires live TimescaleDB | Start Docker stack, POST to /api/flock/config, verify GET returns saved values |
| Home tab no-scroll on tablet | UI-01 | Requires physical tablet or browser responsive mode | Open on 10" tablet viewport, verify all zones + flock summary visible with minimal scroll |
| Hen present animation | FLOCK-01 | Visual animation requires human eye | Open Coop tab, simulate hen weight threshold, verify pulsing egg animation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
