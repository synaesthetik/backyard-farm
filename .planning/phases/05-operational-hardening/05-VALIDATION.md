---
phase: 5
slug: operational-hardening
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 5 — Validation Strategy

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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 05-01-01 | 01 | 1 | ZONE-07 | unit | `pytest tests/test_calibration.py` | TDD |
| 05-02-01 | 02 | 1 | ZONE-07 | unit+component | `pytest tests/ && npx vitest run` | TDD |
| 05-03-01 | 03 | 2 | — | unit | `pytest tests/test_retention.py` | TDD |
| 05-04-01 | 04 | 2 | NOTF-03 | unit+component | `pytest tests/test_ntfy.py && npx vitest run` | TDD |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

No separate Wave 0 plan required. Plans use TDD-style tasks that create tests and implementation atomically.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pH calibration alert appears in alert bar | ZONE-07 | Requires running bridge + dashboard with stale calibration date | Set last_calibration_date to 3 weeks ago, verify amber alert appears |
| ntfy delivers push to phone | NOTF-03 | Requires external ntfy server + mobile device | Configure ntfy URL, trigger an alert, verify phone notification |
| Purge Now deletes raw data | — | Destructive action, verify data is actually removed | Run purge, query sensor_readings for >90 day old data |

---

## Validation Sign-Off

- [x] All tasks have automated verify or TDD-created tests
- [x] Sampling continuity maintained
- [x] Wave 0 not needed — TDD tasks create tests atomically
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
