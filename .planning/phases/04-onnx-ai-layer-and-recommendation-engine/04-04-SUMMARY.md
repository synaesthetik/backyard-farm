---
phase: 04
plan: 04
subsystem: dashboard-ui
tags: [svelte, ai-ui, onnx, websocket, components, testing]
dependency_graph:
  requires: [04-01, 04-03]
  provides: [ai-status-card, ai-settings-toggle, domain-maturity-row, settings-route, source-badge]
  affects: [hub/dashboard]
tech_stack:
  added: []
  patterns: [svelte5-runes, optimistic-ui, websocket-delta, role=switch, role=progressbar]
key_files:
  created:
    - hub/dashboard/src/lib/AIStatusCard.svelte
    - hub/dashboard/src/lib/DomainMaturityRow.svelte
    - hub/dashboard/src/lib/AISettingsToggle.svelte
    - hub/dashboard/src/routes/settings/ai/+page.svelte
    - hub/dashboard/src/lib/AIStatusCard.test.ts
    - hub/dashboard/src/lib/AISettingsToggle.test.ts
  modified:
    - hub/dashboard/src/lib/types.ts
    - hub/dashboard/src/lib/ws.svelte.ts
    - hub/dashboard/src/lib/RecommendationCard.svelte
    - hub/dashboard/src/lib/RecommendationCard.test.ts
    - hub/dashboard/src/routes/+page.svelte
    - hub/dashboard/src/routes/+layout.svelte
decisions:
  - "Used $derived(entry?.mode ?? 'rules') + separate optimisticMode $state for AISettingsToggle to avoid Svelte 5 state_referenced_locally warning while enabling optimistic updates"
  - "AIStatusCard compact mode (allMature=true) suppresses all progress bars to prevent visual clutter once ONNX models are fully active"
  - "source badge defaults to RULES when recommendation.source is undefined — backward-compatible with existing rule-engine recommendations"
metrics:
  duration_seconds: 310
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 6
---

# Phase 4 Plan 4: AI Dashboard UI Summary

**One-liner:** AIStatusCard with per-domain maturity progress bars, AISettingsToggle with PATCH-on-change and optimistic revert, and RecommendationCard AI/RULES source badge — completing the AI-07 user-facing requirement.

## What Was Built

### Task 1: Types, WS store, AIStatusCard, DomainMaturityRow, source badge

**Types (`hub/dashboard/src/lib/types.ts`):**
- Added `source?: 'ai' | 'rules'` to `Recommendation` interface (optional for backward compatibility)
- Added `AIDomain`, `AIMode`, `ModelMaturityEntry`, `ModelMaturityDelta` types
- Added `model_maturity: ModelMaturityEntry[] | null` to `DashboardSnapshot`
- Added `ModelMaturityDelta` to `WSMessage` union

**WebSocket store (`hub/dashboard/src/lib/ws.svelte.ts`):**
- Added `modelMaturity = $state<ModelMaturityEntry[] | null>(null)`
- Snapshot handler populates from `msg.model_maturity ?? null`
- New `model_maturity` delta handler sets `this.modelMaturity = msg.entries`

**DomainMaturityRow.svelte:** Progress bar (8px, role=progressbar, aria-valuenow/min/max/label), mode badge (AI/RULES/BLOCKED pill), approval rate, blocked state with red fill and gate-failure message.

**AIStatusCard.svelte:** Three states — skeleton shimmer (null data), full rows with cold-start italic message (any immature), compact summary (all mature). "Configure AI" link to /settings/ai. No left-accent border (reserved for RecommendationCard per UI-SPEC).

**RecommendationCard.svelte:** Source badge (AI/RULES, 11px pill) added inside .controls before CommandButton pair. Defaults to RULES when source field is absent.

**+page.svelte:** AIStatusCard inserted before FlockSummaryCard in .flock-col; flex column with gap added to .flock-col.

**Tests:** 6 AIStatusCard tests + 4 new RecommendationCard source badge tests — all passing.

### Task 2: AISettingsToggle, /settings/ai route, header settings icon

**AISettingsToggle.svelte:** role=switch, aria-checked, aria-disabled. Optimistic UI with `optimisticMode $state` + `serverMode $derived` pattern (avoids Svelte 5 state_referenced_locally warning). PATCH /api/settings/ai on toggle. Reverts on failure with error toast. Disabled (opacity 0.5, cursor not-allowed, title tooltip) when gate_passed=false.

**`/settings/ai/+page.svelte`:** Renders 3 AISettingsToggle instances for irrigation, zone_health, flock_anomaly. Gets entry from dashboardStore.modelMaturity by domain.

**+layout.svelte:** Settings icon (lucide-svelte `Settings`, 20px) added in header-right flex container with ws-dot. aria-label="Open AI settings", min 44px touch target, muted color with hover.

**Tests:** 7 AISettingsToggle tests — all passing.

## Test Results

- Total: 75 tests across 12 test files — all passing
- Build: `npm run build` succeeds with no TypeScript errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Svelte 5 state_referenced_locally warning in AISettingsToggle**
- **Found during:** Task 2
- **Issue:** `let mode = $state(entry?.mode ?? 'rules')` captures only the initial value of the `entry` prop, causing a Svelte compiler warning
- **Fix:** Replaced with `let serverMode = $derived(entry?.mode ?? 'rules')` + `let optimisticMode = $state<AIMode | null>(null)` + `let mode = $derived(optimisticMode ?? serverMode)`. Optimistic updates set `optimisticMode`; revert sets it back. Server mode tracks the prop reactively.
- **Files modified:** `hub/dashboard/src/lib/AISettingsToggle.svelte`
- **Commit:** 4d37572

## Known Stubs

None. All components are wired to live data from dashboardStore.modelMaturity (WebSocket). The settings page reads live maturity state. The source badge reads from the recommendation object (populated by the backend).

## Threat Flags

None. No new network endpoints or auth paths introduced. The PATCH /api/settings/ai call was already planned and validated server-side by Pydantic in 04-03 (T-04-12 mitigated).

## Self-Check

- [x] `hub/dashboard/src/lib/AIStatusCard.svelte` — FOUND
- [x] `hub/dashboard/src/lib/DomainMaturityRow.svelte` — FOUND
- [x] `hub/dashboard/src/lib/AISettingsToggle.svelte` — FOUND
- [x] `hub/dashboard/src/routes/settings/ai/+page.svelte` — FOUND
- [x] `hub/dashboard/src/lib/AIStatusCard.test.ts` — FOUND
- [x] `hub/dashboard/src/lib/AISettingsToggle.test.ts` — FOUND
- [x] Task 1 commit d7294fd — FOUND
- [x] Task 2 commit 4d37572 — FOUND

## Self-Check: PASSED
