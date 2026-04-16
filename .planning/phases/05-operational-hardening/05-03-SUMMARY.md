---
phase: 05-operational-hardening
plan: 03
subsystem: dashboard-frontend
tags: [svelte5, tdd, calibration, ntfy, storage, settings-ui]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [calibration-ui, ntfy-settings-ui, storage-settings-ui]
  affects: [hub/dashboard]
tech_stack:
  added: []
  patterns:
    - CalibrationStatusBadge pill badge with three states (overdue/due-soon/current)
    - NtfySettingsForm with toggle + text inputs + dual action buttons
    - StoragePanel with inline confirmation dialog for destructive action
    - SvelteKit nested layout for settings tab navigation
    - $effect for prop-to-state synchronization in form components
key_files:
  created:
    - hub/dashboard/src/lib/CalibrationStatusBadge.svelte
    - hub/dashboard/src/lib/CalibrationStatusBadge.test.ts
    - hub/dashboard/src/lib/NtfySettingsForm.svelte
    - hub/dashboard/src/lib/NtfySettingsForm.test.ts
    - hub/dashboard/src/lib/StoragePanel.svelte
    - hub/dashboard/src/lib/StoragePanel.test.ts
    - hub/dashboard/src/routes/settings/calibration/+page.svelte
    - hub/dashboard/src/routes/settings/notifications/+page.svelte
    - hub/dashboard/src/routes/settings/storage/+page.svelte
    - hub/dashboard/src/routes/settings/+layout.svelte
  modified:
    - hub/dashboard/src/lib/types.ts
    - hub/dashboard/src/routes/zones/[id]/+page.svelte
decisions:
  - Used SvelteKit nested layout (settings/+layout.svelte) for settings tab navigation rather than per-page sub-nav — cleaner, DRY, no duplication across four pages
  - Inline PhCalibrationInlineAction in zone detail page file (not a separate component) per plan guidance — 20 lines of markup, not worth a new file
  - Used $effect for NtfySettingsForm prop-to-state sync — correct Svelte 5 pattern for editable form fields that can be reset from parent (compiler warns on initial capture but behavior is correct)
metrics:
  duration_minutes: 25
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_created: 10
  files_modified: 2
  tests_added: 12
requirements: [ZONE-07, NOTF-03]
---

# Phase 5 Plan 03: Frontend — Calibration, Notifications, Storage Summary

**One-liner:** Svelte 5 calibration management page with per-sensor status badges, ntfy settings form with toggle and test button, storage settings page with purge confirmation, inline zone detail calibration action, and shared settings tab navigation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Types, CalibrationStatusBadge, calibration settings page, zone detail inline action | b593a0a | types.ts, CalibrationStatusBadge.svelte, CalibrationStatusBadge.test.ts, settings/calibration/+page.svelte, zones/[id]/+page.svelte |
| 2 | NtfySettingsForm, notifications page, StoragePanel, storage page, settings nav | efeedc7 | NtfySettingsForm.svelte, NtfySettingsForm.test.ts, StoragePanel.svelte, StoragePanel.test.ts, settings/notifications/+page.svelte, settings/storage/+page.svelte, settings/+layout.svelte |

## What Was Built

### CalibrationStatusBadge (hub/dashboard/src/lib/CalibrationStatusBadge.svelte)
Pill badge component with three states driven by `days_since: number | null`:
- `null` or `> 14`: "OVERDUE" — amber background (`var(--color-stale)`), dark text `#0f1117`
- `12–14`: "Due in N days" — same amber (due-soon warning)
- `< 12`: "Calibrated N days ago" — border-color background, secondary text

### Calibration Settings Page (hub/dashboard/src/routes/settings/calibration/+page.svelte)
- Fetches `/api/calibrations` on mount, filters to `sensor_type === "ph"` entries
- Each row: zone name, sensor type label, CalibrationStatusBadge, "Record Calibration" button
- Record Calibration button: outline style when not overdue, filled accent style when overdue
- POST to `/api/calibrations/{zone_id}/{sensor_type}/record` with `{offset: 0.0}`
- Expandable row reveals offset, dry value, wet value, temp coefficient inputs
- PATCH to `/api/calibrations/{zone_id}/{sensor_type}` for field edits
- Empty state: "No pH sensors configured. Add a zone with a pH sensor to begin tracking calibration."

### Zone Detail Inline Action (hub/dashboard/src/routes/zones/[id]/+page.svelte)
- `$effect` fetches `/api/calibrations` when `zoneId` changes
- Inline `ph-calibration-action` div after pH SensorValue row
- Shows CalibrationStatusBadge when overdue, plus "Record Calibration" link-button
- POST to `/api/calibrations/{zoneId}/ph/record` with success/failure toasts

### NtfySettingsForm (hub/dashboard/src/lib/NtfySettingsForm.svelte)
- Props: `settings: NtfySettings`, `onsave`, `ontest` callbacks
- Toggle switch at top: `role="switch"`, `aria-checked`, "Push Notifications" aria-label
- Empty state text when disabled and URL empty: "Push notifications are off. Enter your ntfy server URL and topic to enable."
- Two labeled inputs: "ntfy Server URL" and "Topic" (accessible `for`/`id` pairs)
- "Send Test" button: loading state shows "Sending...", `aria-busy`
- "Save Settings" button: same primary style, not optimistic (waits for 200)
- `$effect` syncs internal state when settings prop changes

### StoragePanel (hub/dashboard/src/lib/StoragePanel.svelte)
- Props: `stats: StorageStats`, `onpurge` callback
- Table of per-table sizes: name 16px/400, size 28px/600 tabular-nums right-aligned
- Retention note: "Raw readings older than 90 days are automatically purged..."
- "Purge Now" button: destructive outline style
- Inline confirmation panel on click: `rgba(239, 68, 68, 0.08)` background, warning text with `role="alert"`
- "Keep My Data" (ghost) and "Confirm Purge" (filled destructive) buttons

### Settings Navigation (hub/dashboard/src/routes/settings/+layout.svelte)
SvelteKit nested layout providing a horizontal tab bar across all settings pages:
- Tabs: AI → /settings/ai, Calibration → /settings/calibration, Notifications → /settings/notifications, Storage → /settings/storage
- Active tab: `var(--color-accent)` text and 2px bottom border
- Uses `$page.url.pathname` for active state detection

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- The `state_referenced_locally` Svelte 5 compiler warnings in NtfySettingsForm are expected when using `$state(prop.value)` initialization. A `$effect` was added to sync state when the prop changes (correct Svelte 5 pattern for editable form state). These are warnings not errors and do not affect the build or tests.

## Test Results

| Test File | Tests | Status |
|-----------|-------|--------|
| CalibrationStatusBadge.test.ts | 4 | PASS |
| NtfySettingsForm.test.ts | 4 | PASS |
| StoragePanel.test.ts | 4 | PASS |
| All other existing tests | 75 | PASS |
| **Total** | **87** | **ALL PASS** |

Build: `npm run build` succeeds with no TypeScript errors.

## Known Stubs

None — all components fetch real API endpoints established in Plans 05-01 and 05-02. No hardcoded mock data flows to the UI.

## Threat Flags

No new network endpoints introduced — all fetch calls target API routes established in Plan 05-02 (T-05-04 Pydantic validation at API boundary). T-05-09 mitigation implemented: NtfySettingsForm uses `type="url"` for the server URL input providing basic client-side format validation. T-05-11 mitigation implemented: StoragePanel inline confirmation dialog prevents accidental purge with explicit destructive warning text.

## Self-Check: PASSED

Files verified:
- hub/dashboard/src/lib/CalibrationStatusBadge.svelte: FOUND
- hub/dashboard/src/lib/NtfySettingsForm.svelte: FOUND
- hub/dashboard/src/lib/StoragePanel.svelte: FOUND
- hub/dashboard/src/routes/settings/calibration/+page.svelte: FOUND
- hub/dashboard/src/routes/settings/notifications/+page.svelte: FOUND
- hub/dashboard/src/routes/settings/storage/+page.svelte: FOUND
- hub/dashboard/src/routes/settings/+layout.svelte: FOUND

Commits verified:
- b593a0a: feat(05-03): calibration types, status badge, settings page, and zone detail inline action
- efeedc7: feat(05-03): ntfy settings form, storage panel, notification/storage pages, settings nav
