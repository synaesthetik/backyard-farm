# Phase 2: Actuator Control, Alerts, and Dashboard V1 - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

The farmer can monitor all garden zones, manually control irrigation and the coop door, and act on rule-based recommendations from the recommend-and-confirm queue — all from a mobile-friendly PWA.

This phase delivers:
- Multi-route SvelteKit SPA with bottom tab bar
- Irrigation control (manual valve commands, single-zone invariant, sensor-feedback loop)
- Coop door automation (NOAA astronomical clock, limit switch confirmation, stuck-door alert)
- Feed and water level display on coop page
- Recommend-and-confirm UX (rule-based engine, deduplication, rejection back-off)
- Persistent alert bar (debounce/hysteresis, tappable deep-links)
- Zone health composite score (green/yellow/red) per zone
- Sensor history charts (7-day and 30-day) per zone on zone detail route
- PWA service worker + offline shell + mobile-first responsive layout

Phase 2 does NOT deliver: egg production tracking, flock health alerts, unified overview screen (Phase 3), ONNX ML recommendations (Phase 4), pH calibration workflows or ntfy push notifications (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Navigation and Routing Structure

- **D-01: Multi-route SPA with SvelteKit routing.** Phase 2 introduces client-side routing. Do not add routing adapters — SvelteKit's built-in routing with the existing `@sveltejs/adapter-node` is sufficient.
- **D-02: Bottom tab bar with 3 tabs: Zones / Coop / Recommendations.** The tab bar is a persistent component in `+layout.svelte`, visible on all routes. Active tab is highlighted. The Zones tab is the default landing tab.
- **D-03: Routes:**
  - `/` — Zones tab: ZoneCard grid + SystemHealthPanel (same as Phase 1 main page, extended)
  - `/zones/[id]` — Zone detail: current sensor readings, composite health score, irrigation controls, sensor history charts
  - `/coop` — Coop tab: door status + controls, feed level, water level
  - `/recommendations` — Recommendations tab: full recommendation queue
- **D-04: Alert bar taps deep-link to the relevant route.** Low moisture alert → `/zones/[id]`. Stuck door → `/coop`. Production drop (Phase 3) → `/recommendations`. Implement via SvelteKit `goto()`.

### Recommendation Queue (AI-01, AI-02, AI-04, AI-05)

- **D-05: Recommendation card shows: action description + supporting sensor reading with context + explanation of why.** Example: "Irrigate Zone A" / "Moisture: 18% VWC (target range: 40–60%)" / "Below low threshold for 2h". Matches AI-01 exactly.
- **D-06: Two controls per card: Approve and Reject. No reason required on reject.** One tap to reject starts the back-off window immediately. Per-rejection reason tagging is explicitly v2 (AI2-02) — do not implement in Phase 2.
- **D-07: Deduplication: if a pending recommendation of the same type exists for a zone, suppress new duplicates until the pending one is resolved.** Implemented in the rule engine (hub-side), not the UI. The UI simply renders what the hub provides.
- **D-08: Rejection back-off window is configurable per recommendation type** (AI-05). The rule engine must not re-generate the same recommendation type for a zone until the back-off window expires. Back-off duration is an env var (e.g., `RECOMMENDATION_BACKOFF_MINUTES`, default: 60).

### Alert Bar (UI-02, UI-03, NOTF-01, NOTF-02)

- **D-09: Alert bar is positioned below the header (48px), above page content.** It is part of the layout, stacked between the header and the main content area. On all routes.
- **D-10: Alerts auto-clear when the condition resolves past the hysteresis band.** No farmer dismiss. The condition is the source of truth (NOTF-02). Alert fires on threshold crossing, clears only when value recovers past hysteresis band.
- **D-11: Debounce and hysteresis are hub-side.** The UI renders whatever alert state the hub sends via WebSocket. It does not implement its own debounce.
- **D-12: Duplicate alert types are grouped.** If 3 zones have low moisture simultaneously, the alert bar shows one grouped entry: "Low moisture — 3 zones" with the count (UI-02). Tapping navigates to `/` (zones overview) rather than a single zone.
- **D-13: Alert severity levels — P0 (red) and P1 (amber).** Stuck door, node offline → P0. Low moisture, low pH, low feed/water → P1. Color corresponds to `--color-offline` (#ef4444) and `--color-stale` (#f59e0b) from the existing design system.

### Command Feedback (Irrigation and Coop Door)

- **D-14: Button spinner + disabled state while command is in flight.** The tapped control button shows a loading spinner and is disabled for the duration of the hub→edge→relay→ack roundtrip. Do not optimistically update status.
- **D-15: Status updates only on confirmed ack from the hub.** When the hub receives limit switch confirmation (coop) or relay ack (irrigation), it sends a WebSocket delta. The UI updates status from that delta.
- **D-16: On command timeout or failure: show a toast error, re-enable the button.** Toast disappears after 5 seconds. No auto-retry. Farmer can re-tap.
- **D-17: Single-zone-at-a-time invariant (IRRIG-02) is enforced hub-side.** If the farmer attempts to open a second zone while one is already open, the hub rejects the command and the UI shows an error toast: "Another zone is already irrigating." The open valve's button remains as-is.

### Irrigation Control (IRRIG-01, IRRIG-02, IRRIG-04, IRRIG-05, IRRIG-06)

- **D-18: Manual irrigation controls live on the zone detail page `/zones/[id]`.** Open valve and Close valve buttons. Irrigation status (open/closed/moving) is shown prominently.
- **D-19: Sensor-feedback irrigation loop: once approved, hub commands valve open, monitors VWC, closes valve when target VWC is reached or max duration exceeded.** Max duration is a configurable env var (e.g., `IRRIGATION_MAX_DURATION_MINUTES`, default: 30).
- **D-20: Cool-down window after an irrigation event suppresses re-triggering.** Duration is configurable (e.g., `IRRIGATION_COOLDOWN_MINUTES`, default: 120). The rule engine checks the last irrigation timestamp before generating a new recommendation for the same zone.

### Coop Door Automation (COOP-01, COOP-02, COOP-03, COOP-05)

- **D-21: NOAA astronomical clock for sunrise/sunset.** The hub calculates sunrise and sunset from configured `HUB_LATITUDE` and `HUB_LONGITUDE` env vars. Configurable offset in minutes (`COOP_OPEN_OFFSET_MINUTES`, `COOP_CLOSE_OFFSET_MINUTES`).
- **D-22: Hard time limits as safety backstop (COOP-02).** Force-close no later than `COOP_HARD_CLOSE_HOUR` (default: 21, i.e., 21:00 local time). This is the same env var defined in Phase 1 (D-14 of 01-CONTEXT.md).
- **D-23: Limit switch confirmation (COOP-03).** Hub waits up to 60 seconds for the expected limit switch to confirm. If not reached: raises a stuck-door alert (P0), sends no further commands until manually reset.
- **D-24: Coop door states: open / closed / moving / stuck.** The hub tracks and broadcasts these states. The UI renders them with clear visual distinction (color + label).
- **D-25: Manual override buttons on the `/coop` page.** Open and Close buttons with the same spinner/ack/error flow as irrigation (D-14 through D-16).

### Feed and Water Level (COOP-06, COOP-07)

- **D-26: Feed level displayed as fill percentage (0–100%) derived from load cell weight.** Low threshold is configurable. Alert fires when below threshold (NOTF-01). Feed sensor data arrives via MQTT the same as zone sensor data.
- **D-27: Water level monitoring with low-level alert.** Display style matches feed: fill percentage or volume estimate depending on sensor type. Alert on low.

### Zone Health Composite Score (ZONE-06)

- **D-28: Composite health score is computed hub-side and broadcast in the WebSocket state.** Three tiers: green (all sensors within target ranges) / yellow (one sensor outside target but not critically) / red (any sensor critically out of range or BAD quality flag). The zone detail page shows which sensor(s) contributed to a non-green score.
- **D-29: Health score is visible on the ZoneCard (main Zones tab).** A color indicator (badge or card border highlight) using `--color-accent` (green), `--color-stale` (yellow), `--color-offline` (red) from the existing palette.

### Sensor History Charts (ZONE-05)

- **D-30: Charts live on the zone detail route `/zones/[id]`.** All three sensors charted: moisture, pH, temperature. Two time range options: 7-day and 30-day. Toggle between ranges without a page reload.
- **D-31: Chart library: uPlot.** ~45KB canvas-based time-series library. Wrap in a Svelte component (`SensorChart.svelte`). No Svelte-specific uPlot wrapper package needed — instantiate directly in `onMount`, destroy in `onDestroy`.
- **D-32: Data fetched from a new REST endpoint** (e.g., `GET /api/zones/{zone_id}/history?sensor_type={type}&days=7`). FastAPI serves aggregated TimescaleDB data (time-bucketed to reduce payload size: 30-minute buckets for 7-day, 2-hour buckets for 30-day).

### PWA (UI-05, UI-06)

- **D-33: SvelteKit service worker for offline shell.** Pre-cache the app shell (HTML, CSS, JS). Data endpoints are not cached offline — stale display is acceptable and already handled by the Phase 1 freshness system.
- **D-34: Mobile-first responsive layout.** Existing grid/spacing system from Phase 1 extends naturally. Bottom tab bar uses safe-area-inset-bottom padding (already in Phase 1 CSS). Touch targets: 44px minimum (already a Phase 1 requirement).

### Design System Extensions

- **D-35: No component library in Phase 2.** Continue hand-authored Svelte 5 components. Phase 2 component additions: `TabBar.svelte`, `AlertBar.svelte`, `RecommendationCard.svelte`, `CoopPanel.svelte`, `SensorChart.svelte`, `CommandButton.svelte` (spinner + disabled state wrapper), `HealthBadge.svelte`.
- **D-36: Toast notifications** for command errors. A lightweight `Toast.svelte` component (no library) — fixed position, auto-dismiss after 5 seconds. Reuse `--color-offline` for error toasts.

### Claude's Discretion

- FastAPI endpoint design for actuator commands (REST vs WebSocket commands)
- TimescaleDB query design for time-bucketed history data
- uPlot configuration details (axes, colors, grid lines — match dark theme)
- SvelteKit service worker cache strategy specifics
- Exact hysteresis band values for each alert type (within the constraint: alert fires on crossing, clears past hysteresis)
- Back-off window defaults for each recommendation type
- NOAA astronomical clock implementation (Python library vs formula)
- WebSocket delta message types for actuator state, alert state, recommendation queue

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 Core
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, 6 pre-defined plan slugs (02-01 through 02-06), critical design note on recommend-and-confirm UX
- `.planning/REQUIREMENTS.md` — Full requirement text for ZONE-05, ZONE-06, IRRIG-01, IRRIG-02, IRRIG-04, IRRIG-05, IRRIG-06, COOP-01, COOP-02, COOP-03, COOP-05, COOP-06, COOP-07, AI-01, AI-02, AI-04, AI-05, UI-02, UI-03, UI-05, UI-06, NOTF-01, NOTF-02

### Phase 1 Decisions (carry forward)
- `.planning/phases/01-hardware-foundation-and-sensor-pipeline/01-CONTEXT.md` — Hardware decisions (D-06 to D-09), quality flag logic (D-10 to D-12), emergency thresholds (D-13, D-14), dashboard UI patterns (D-15, D-16)
- `.planning/phases/01-hardware-foundation-and-sensor-pipeline/01-UI-SPEC.md` — Approved design system: color palette, spacing scale, typography, component patterns, accessibility minimums

### Existing Code (must read before planning)
- `hub/dashboard/src/lib/types.ts` — Existing TypeScript types; Phase 2 must extend, not replace
- `hub/dashboard/src/routes/+page.svelte` — Current single-page layout to be refactored into routed structure
- `hub/dashboard/src/app.css` — CSS variable palette and spacing scale (authoritative)
- `hub/bridge/models.py` — Pydantic models for MQTT payloads; Phase 2 adds actuator command models
- `hub/bridge/main.py` — Bridge pipeline; Phase 2 adds recommendation rule engine and alert debounce logic
- `docs/mqtt-topic-schema.md` — MQTT topic schema; Phase 2 adds actuator command topics

### Project Context
- `.planning/STATE.md` — Current blockers, accumulated decisions, phase progress

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ZoneCard.svelte` — Zone sensor display with stale/stuck state handling. Phase 2 adds a health badge and tap-to-navigate behavior.
- `SensorValue.svelte` — Sensor row with icon, label, value, unit, quality. Reuse on zone detail page.
- `SystemHealthPanel.svelte` — Node health grid. Stays on Zones tab (main page), no changes needed.
- `ws.svelte.ts` — WebSocket store with `isStale()` and `formatElapsed()` utilities. Phase 2 extends the snapshot/delta types to include alerts, recommendations, and actuator states.
- `src/app.css` — CSS variables for colors and spacing are the single source of truth. No duplication.

### Established Patterns
- Svelte 5 `$state` / `$derived` / `$props()` runes — all components use this pattern. No Options API.
- Component-scoped `<style>` blocks — no Tailwind or utility classes.
- Lucide icons via `lucide-svelte` — continue for Phase 2 icons (door, feed bucket, water drop, check, x, alert triangle).
- `onMount` / `onDestroy` for lifecycle (WebSocket, will be needed for uPlot chart instances).

### Integration Points
- `GET /api/zones/{zone_id}/history` — New endpoint needed on FastAPI for chart data.
- `POST /api/actuators/irrigate` (or similar) — New actuator command endpoint.
- `POST /api/actuators/coop-door` — New coop door command endpoint.
- WebSocket `/ws/dashboard` — Must be extended to broadcast: alert state, recommendation queue, actuator pending/confirmed states, coop door state, feed/water levels.
- MQTT topics — New actuator command topics (hub→edge direction) must be defined; see `docs/mqtt-topic-schema.md`.

</code_context>

<specifics>
## Specific Ideas

- Bottom tab bar: use `page.url.pathname` from SvelteKit's `$page` store to highlight the active tab. Icons: `Sprout` (Zones), `Home` (Coop), `Bell` (Recommendations) from Lucide.
- uPlot: dark theme integration — override uPlot's default white background with `--color-bg`, grid lines with `--color-border`, series colors with `--color-accent` (moisture), `#60a5fa` (pH), `#fb923c` (temp).
- Alert bar height: auto-height based on number of active alerts (each alert is one row). No collapse animation needed — keep it simple for Phase 2.
- Command timeout: hub should return an error response if the edge node ack is not received within 10 seconds. The API endpoint should not hang indefinitely. The UI's 5-second toast timeout is for display; the actual ack timeout is server-side.
- NOAA astronomical clock: `astral` Python library (pure Python, no system deps) is a clean fit for sunrise/sunset calculation from lat/long. Alternatively, a simple formula implementation to avoid the dependency.

</specifics>

<deferred>
## Deferred Ideas

None raised during discussion.

</deferred>

---

*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Context gathered: 2026-04-09*
