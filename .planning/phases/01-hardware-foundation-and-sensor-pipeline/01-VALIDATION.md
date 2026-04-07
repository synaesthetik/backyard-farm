---
phase: 1
slug: hardware-foundation-and-sensor-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Python framework** | pytest 9.0.2 |
| **Python config** | `pytest.ini` or `pyproject.toml` — none yet, Wave 0 creates |
| **Python quick run** | `pytest tests/ -x -q` |
| **Python full suite** | `pytest tests/ -v` |
| **Frontend framework** | vitest 4.1.3 |
| **Frontend config** | `vitest.config.ts` — none yet, Wave 0 creates |
| **Frontend quick run** | `npx vitest run` |
| **Frontend full suite** | `npx vitest run --coverage` |
| **Estimated runtime** | ~30 seconds (unit tests only) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q && npx vitest run`
- **After every plan wave:** Run `pytest tests/ -v && npx vitest run --coverage`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | — | N/A | smoke | `docker compose ps` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-08 | — | ACL rejects unauthorized topics | manual | Mosquitto client test | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | INFRA-03 | — | SQLite buffer flushes in order on reconnect | unit | `pytest tests/test_buffer.py -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | INFRA-02 | — | Quality flag logic range checks | unit | `pytest tests/test_quality.py -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | IRRIG-03 | — | Emergency shutoff triggers at >=95% VWC | unit | `pytest tests/test_rules.py -x` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | COOP-04 | — | Coop hard-close triggers at COOP_HARD_CLOSE_HOUR | unit | `pytest tests/test_rules.py -x` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | INFRA-02 | — | Calibration offsets applied before DB write | unit | `pytest tests/test_calibration.py -x` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 3 | INFRA-07 | — | Stuck-reading detected after 30 identical values | unit | `pytest tests/test_quality.py::test_stuck_detection -x` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 3 | ZONE-04 | — | ZoneCard shows stale border when age >= 5 min | unit (vitest) | `npx vitest run src/lib/ZoneCard.test.ts` | ❌ W0 | ⬜ pending |
| 1-06-02 | 06 | 3 | UI-07 | — | NodeHealthRow shows OFFLINE after 3 missed heartbeats | unit (vitest) | `npx vitest run src/lib/NodeHealthRow.test.ts` | ❌ W0 | ⬜ pending |
| 1-06-03 | 06 | 3 | INFRA-05 | — | INFRA-09/UI-04 HTTPS accessible from LAN | smoke (manual) | Manual: open `https://farm.local` in browser | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `hub/bridge/tests/test_quality.py` — stubs for INFRA-02 quality flag logic (range checks + GOOD/SUSPECT/BAD boundaries)
- [ ] `hub/bridge/tests/test_calibration.py` — covers ZONE-03 calibration offset application
- [ ] `hub/bridge/tests/test_heartbeat.py` — covers INFRA-05 heartbeat miss detection logic
- [ ] `edge/daemon/tests/test_buffer.py` — covers INFRA-03 SQLite buffer flush ordering
- [ ] `edge/daemon/tests/test_rules.py` — covers INFRA-04 emergency shutoff and hard-close rules
- [ ] `hub/dashboard/src/lib/ZoneCard.test.ts` — covers ZONE-04, INFRA-06, INFRA-07 UI states
- [ ] `hub/dashboard/src/lib/NodeHealthRow.test.ts` — covers UI-07 node health display states
- [ ] `hub/bridge/tests/conftest.py` — shared fixtures (mock MQTT payloads, mock DB pool)
- [ ] `hub/dashboard/vitest.config.ts` — vitest + svelte plugin configuration
- [ ] Python test install: `pip install pytest pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTTPS endpoint accessible from LAN browser | INFRA-09, UI-04 | Requires physical network and browser — cannot be automated in CI without a browser and LAN fixture | Open `https://farm.local` in browser on LAN device; confirm no cert warning on second visit |
| Cold-boot relay state confirmed safe | IRRIG-03, COOP-04 | Requires physical relay hardware to be present and powered | Power cycle relay board with GPIO uninitialized; confirm all relays remain in safe (NC/off) state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
