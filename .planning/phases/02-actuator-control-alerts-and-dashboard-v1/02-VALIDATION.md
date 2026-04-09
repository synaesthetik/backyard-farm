---
phase: 2
slug: actuator-control-alerts-and-dashboard-v1
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.1.1 + @testing-library/svelte 5.2.6 (frontend); pytest + pytest-asyncio (Python bridge) |
| **Config file** | `hub/dashboard/vitest.config.ts` (exists) |
| **Quick run command** | `cd hub/dashboard && npm test -- --run` |
| **Full suite command** | `cd hub/dashboard && npm test -- --run --reporter=verbose` + `cd hub/bridge && python -m pytest tests/` |
| **Estimated runtime** | ~15 seconds (frontend); ~10 seconds (Python) |

---

## Sampling Rate

- **After every task commit:** Run `cd hub/dashboard && npm test -- --run`
- **After every plan wave:** Run full suite: `cd hub/dashboard && npm test -- --run --reporter=verbose` + `cd hub/bridge && python -m pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | IRRIG-01 | — | N/A | unit | `npm test -- --run src/lib/CommandButton.test.ts` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | IRRIG-02 | — | Hub returns 409 on second-zone attempt | unit (mock API) | `npm test -- --run src/lib/CommandButton.test.ts` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | IRRIG-04 | — | N/A | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | AI-04 | — | N/A | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | AI-05 | — | N/A | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | COOP-01 | — | N/A | unit (Python) | `cd hub/bridge && python -m pytest tests/test_coop_scheduler.py` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | COOP-03 | — | Stuck-door alert fires when ack not received in 60s | unit (Python, asyncio mock) | `cd hub/bridge && python -m pytest tests/test_actuator.py` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | AI-01 | — | N/A | unit | `npm test -- --run src/lib/RecommendationCard.test.ts` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | AI-02 | — | N/A | unit | `npm test -- --run src/lib/RecommendationCard.test.ts` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 3 | UI-02 | — | N/A | unit | `npm test -- --run src/lib/AlertBar.test.ts` | ❌ W0 | ⬜ pending |
| 02-05-02 | 05 | 3 | UI-03 | — | N/A | unit (mock goto) | `npm test -- --run src/lib/AlertBar.test.ts` | ❌ W0 | ⬜ pending |
| 02-05-03 | 05 | 3 | NOTF-02 | — | Alert fires on threshold; stays until hysteresis clears | unit (Python) | `cd hub/bridge && python -m pytest tests/test_alert_engine.py` | ❌ W0 | ⬜ pending |
| 02-05-04 | 05 | 3 | ZONE-06 | — | N/A | unit | `npm test -- --run src/lib/HealthBadge.test.ts` | ❌ W0 | ⬜ pending |
| 02-05-05 | 05 | 3 | ZONE-05 | — | N/A | unit (mock fetch) | `npm test -- --run src/lib/SensorChart.test.ts` | ❌ W0 | ⬜ pending |
| 02-06-01 | 06 | 3 | UI-05 | — | N/A | manual | Install in Chrome devtools; `npm run build && npm run preview` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `hub/dashboard/src/lib/SensorChart.test.ts` — stubs for ZONE-05
- [ ] `hub/dashboard/src/lib/HealthBadge.test.ts` — stubs for ZONE-06
- [ ] `hub/dashboard/src/lib/CommandButton.test.ts` — stubs for IRRIG-01, IRRIG-02
- [ ] `hub/dashboard/src/lib/RecommendationCard.test.ts` — stubs for AI-01, AI-02
- [ ] `hub/dashboard/src/lib/AlertBar.test.ts` — stubs for UI-02, UI-03
- [ ] `hub/bridge/tests/__init__.py` — Python test package init
- [ ] `hub/bridge/tests/test_alert_engine.py` — stubs for NOTF-02
- [ ] `hub/bridge/tests/test_rule_engine.py` — stubs for IRRIG-04, AI-04, AI-05
- [ ] `hub/bridge/tests/test_coop_scheduler.py` — stubs for COOP-01
- [ ] `hub/bridge/tests/test_actuator.py` — stubs for COOP-03
- [ ] Python test framework: `pip install pytest pytest-asyncio` in bridge container/venv

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PWA installs on iOS and Android | UI-05 | Requires physical device or browser install flow | Build (`npm run build`), serve via `npm run preview` over HTTPS, open on device, tap "Add to Home Screen" |
| Sensor data staleness flag visible | UI-06 | Requires simulating stale WS connection | Disconnect WS, wait > staleness threshold, verify "stale" indicator appears on dashboard |
| Door state shows open/closed/moving/stuck | COOP-02 | Requires physical limit switch signals or hardware sim | Trigger door command, verify state transitions in dashboard |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
