---
phase: 01-hardware-foundation-and-sensor-pipeline
reviewed: 2026-04-09
status: issues_found
scope: gap-closure (plans 01-07, 01-08)
depth: standard
files_reviewed: 7
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
---

# Phase 01: Gap-Closure Code Review

**Scope:** Gap-closure plans 01-07 (WebSocket routing fix) and 01-08 (dashboard unit tests)
**Files reviewed:** 7
**Status:** Issues found — 0 critical, 2 warnings, 3 info

---

## Findings

### WR-01: server.js — No error handler on HTTP server (warning)

**File:** `hub/dashboard/server.js:6-10`
**Severity:** Warning
**Description:** The Node.js HTTP server has no `.on('error', ...)` handler. Port binding failures (e.g., EADDRINUSE) produce an unhandled exception that crashes the process with a stack trace but no useful log message.

```js
// Current
const server = createServer(handler);
server.listen(PORT, () => { ... });

// Recommended
server.on('error', (err) => {
  console.error('Dashboard server failed to start:', err.message);
  process.exit(1);
});
```

**Impact:** Low — Docker Compose restart policy handles crashes, but the crash message is cryptic.

---

### WR-02: SensorValue.test.ts — Temperature test uses Droplets icon instead of Thermometer (warning)

**File:** `hub/dashboard/src/lib/SensorValue.test.ts:90`
**Severity:** Warning
**Description:** The "rounds temperature to integer" test passes `Droplets` as the icon instead of `Thermometer`. The test still passes (icon identity is not asserted), but the description implies temperature rendering while using a moisture icon.

```ts
// Line 90 — misleading
icon: Droplets,
// Should be
icon: Thermometer,
```

**Impact:** Low — test passes, but assertion coverage for icon switching is missing.

---

### IN-01: Caddyfile — Route ordering (info, no action needed)

**File:** `hub/Caddyfile`
**Note:** Review tooling flagged route ordering. After manual inspection, `/api/*` and `/ws/dashboard` have no path overlap (different prefixes: `/api/` vs `/ws/`). Caddy's `handle` directive evaluates path specificity correctly. No change required.

---

### IN-02: NodeHealthRow.test.ts — Permissive regex assertions (info)

**File:** `hub/dashboard/src/lib/NodeHealthRow.test.ts:40,49`
**Description:** `/Heartbeat.*ago/` and `/Last seen.*ago/` are permissive patterns. Acceptable for smoke-testing copy; would not catch copy mutations. No change required.

---

### IN-03: vitest.config.ts — No global setup file (info)

**File:** `hub/dashboard/vitest.config.ts`
**Description:** No `setupFiles` configured. Each test file handles its own cleanup via `afterEach(cleanup)`. Not a bug — future improvement if test count grows.

---

## Verified Clean

| File | Result | Notes |
|------|--------|-------|
| `hub/Caddyfile` | ✓ Clean | Route fix correct; path precedence verified |
| `hub/dashboard/server.js` | ⚠ WR-01 | Missing error handler |
| `hub/dashboard/src/lib/ZoneCard.svelte` | ✓ Clean | `$derived.by` fix is correct |
| `hub/dashboard/src/lib/SensorValue.test.ts` | ⚠ WR-02 | Wrong icon in temperature test |
| `hub/dashboard/src/lib/ZoneCard.test.ts` | ✓ Clean | Factory pattern and assertions correct |
| `hub/dashboard/src/lib/NodeHealthRow.test.ts` | ✓ Clean | Tests are adequate |
| `hub/dashboard/vitest.config.ts` | ✓ Clean | Browser condition fix correct |

---

## Summary

The gap-closure changes are correct and safe to ship. The WebSocket routing fix is a clean one-line change. The `ZoneCard.svelte` `$derived.by` bug fix (caught during test creation) is significant — stale/stuck indicators were always rendering regardless of data state. Two minor warnings are advisory and do not block phase completion.
