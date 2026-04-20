---
phase: 07-interactive-tutorial-and-user-documentation
plan: 03
subsystem: documentation
tags: [troubleshooting, mkdocs, docs-build, makefile]
dependency_graph:
  requires:
    - 07-02-PLAN.md  # mkdocs.yml and requirements-docs.txt created in Plan 02
  provides:
    - docs/troubleshooting/index.md  # 20 failure modes, symptom-first
    - Makefile                        # make docs, docs-serve, docs-clean targets
    - README.md                       # Documentation section with make docs instructions
  affects:
    - docs/                           # troubleshooting guide integrated into MkDocs nav
tech_stack:
  added: []
  patterns:
    - Symptom-first troubleshooting structure (D-11/D-12/D-13)
    - Makefile targets for Python/MkDocs build pipeline
key_files:
  created:
    - Makefile
  modified:
    - docs/troubleshooting/index.md
    - README.md
decisions:
  - Replaced em-dash anchor links with single-hyphen equivalents to match MkDocs-generated IDs
  - Inserted Documentation section into README between Development and Roadmap sections
metrics:
  duration: ~20 minutes
  completed: 2026-04-16
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 7 Plan 03: Troubleshooting Guide and Docs Build Infrastructure Summary

**One-liner:** 20-failure-mode symptom-first troubleshooting guide with hardware cross-references, plus Makefile docs target running `pip install + mkdocs build --strict`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Write 20-failure-mode troubleshooting guide | 04a206f | docs/troubleshooting/index.md |
| 2 | Auto-build infrastructure — Makefile docs target and README | 3f4bc92 | Makefile, README.md |

## What Was Built

### Task 1: Troubleshooting Guide (docs/troubleshooting/index.md)

Replaced the stub with a complete 20-failure-mode guide. Each failure mode follows the Symptom / Possible Causes / Diagnostic Steps / Resolution structure per D-12. Organization is symptom-first per D-11 — section titles describe what the farmer sees ("Sensor shows STALE data"), not the component name.

Failure modes covered:
1. Sensor shows STALE data (>5 min old)
2. Sensor shows SUSPECT or BAD quality flag
3. Sensor returns static/stuck reading
4. Zone shows "No data received" after hardware setup
5. Node shows offline in System Health panel
6. MQTT disconnection — bridge shows no incoming messages
7. Irrigation valve won't open after "Open Valve" command
8. Irrigation valve won't close / zone stuck irrigating
9. Coop door stuck (P0 alert fires)
10. Coop door doesn't open/close at scheduled time
11. Recommendation queue empty when sensor is out of range
12. Recommendation appears but "Approve" does nothing
13. pH calibration overdue alert won't clear after calibration
14. ntfy push notification not delivered to phone
15. Dashboard shows blank / no data after fresh install
16. TimescaleDB disk full alert
17. AI domain toggle has no effect on recommendations
18. Production drop alert fires incorrectly
19. Hub not reachable from phone browser (HTTPS/PWA issue)
20. Power loss recovery — nodes reconnect but no data flowing

Hardware cross-reference links present for failure modes 2, 3, 5, 7, 8, 9 (linking to garden-node.md, coop-node.md, irrigation.md, hub.md). Internal cross-references between failure modes use correct MkDocs-generated anchor IDs.

### Task 2: Makefile and README

Created `Makefile` with three targets:
- `make docs` — installs deps from `requirements-docs.txt` then runs `mkdocs build --strict`
- `make docs-serve` — live preview at http://127.0.0.1:8000
- `make docs-clean` — removes `site/` directory

Added a **Documentation** section to README.md between the Development and Roadmap sections, documenting all three make targets with usage notes.

## Verification Results

```
grep -c "^## [0-9]" docs/troubleshooting/index.md  → 20
grep -c "Symptom:" docs/troubleshooting/index.md   → 20
grep -c "Diagnostic Steps:" docs/troubleshooting/index.md → 20
grep -c "Resolution:" docs/troubleshooting/index.md → 20
make docs exit code                                 → 0
ls site/troubleshooting/index.html                  → exists
grep "make docs" README.md                          → match
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken internal anchor links due to em-dash in heading ID**
- **Found during:** Task 1 verification (`mkdocs build --strict`)
- **Issue:** The heading `## 6. MQTT disconnection — bridge shows no incoming messages` contains an em-dash. The plan's content template used `--` (double hyphen) in the anchor link, but MkDocs generates a single `-` for the em-dash character. Two internal cross-reference links used the wrong anchor.
- **Fix:** Updated both `#6-mqtt-disconnection--bridge-shows-no-incoming-messages` links to `#6-mqtt-disconnection-bridge-shows-no-incoming-messages` to match the actual generated anchor.
- **Files modified:** docs/troubleshooting/index.md
- **Commit:** 04a206f

**2. [Rule 2 - Missing] Verified site/ in .gitignore before committing**
- **Found during:** Task 2 (Pitfall 3 from RESEARCH.md)
- **Outcome:** `site/` was already present in `.gitignore` from Plan 02 setup. No action needed — confirmed pre-existing.

## Known Stubs

None — the troubleshooting guide is complete with fully written content for all 20 failure modes. No placeholder text or TODO items remain.

## Threat Flags

No new network endpoints, auth paths, or data handling introduced. Documentation files only — no security-relevant surface.

## Self-Check: PASSED

- [x] `docs/troubleshooting/index.md` exists with 20 failure modes
- [x] `Makefile` exists with docs, docs-serve, docs-clean targets
- [x] `README.md` updated with Documentation section
- [x] Commit 04a206f exists (troubleshooting guide)
- [x] Commit 3f4bc92 exists (Makefile + README)
- [x] `mkdocs build --strict` exits 0
- [x] `site/troubleshooting/index.html` exists after build
