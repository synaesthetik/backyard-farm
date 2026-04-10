# Phase 3: Flock Management and Unified Dashboard - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

The flock's health story is complete — egg production is tracked against a breed/age/daylight model, feed consumption is derived from load cell data, and production drops trigger alerts. A single overview screen surfaces all garden zones and the flock summary together.

This phase delivers:
- Nesting box weight sensor integration for automated egg count estimation
- Expected production model (breed lay rate x age factor x daylight hours)
- Production trend chart (actual vs expected, 30 days)
- Production drop alert (3-day rolling avg < 75% expected)
- Feed consumption rate with 7-day sparkline and anomaly alert
- Flock configuration settings (breed, hatch date, flock size, supplemental lighting)
- New Home tab as unified overview (zones + flock summary)
- Animated "hen present" indicator on Coop tab

Phase 3 does NOT deliver: ONNX ML recommendations (Phase 4), pH calibration or push notifications (Phase 5), hardware docs (Phase 6), or user tutorial (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Egg Count Estimation (FLOCK-01, FLOCK-02)

- **D-01: Egg count is sensor-driven, not manual entry.** A weight/pressure sensor in the nesting box measures accumulated egg weight. No manual egg count form.
- **D-02: 30-minute polling cycle.** The nesting box weight sensor is polled every 30 minutes. Each poll estimates egg count from weight (~60g per standard egg) after subtracting hen weight when a hen is detected above a configurable high-mark threshold.
- **D-03: Manual refresh button on Coop tab.** The farmer can tap a "Refresh" button to trigger an immediate re-poll of the nesting box sensor outside the 30-minute cycle.
- **D-04: "Hen present" detection via high-mark weight threshold.** When nesting box weight exceeds the configured hen-weight threshold (e.g., 1500g), the system reports that a chicken is currently in the nesting box. This is displayed as an animated indicator on the Coop tab.
- **D-05: Animated "hen present" indicator on Coop tab.** When a hen is detected, show a visible egg icon or gentle animation. Makes the dashboard feel alive — the farmer glances and knows someone's laying. Not subtle text — a real visual indicator.

### Production Model and Display (FLOCK-03, FLOCK-04)

- **D-06: Expected production model: flock_size x breed_lay_rate x age_factor x daylight_factor.** All four factors are configurable via flock settings. The model calculates daily expected egg count.
- **D-07: 30-day uPlot overlay chart (actual vs expected).** Two series on the same chart: actual daily estimated egg count from sensor data, and expected daily count from the model. Consistent with Phase 2's sensor history charts (D-31 from Phase 2).
- **D-08: Production drop alert when 3-day rolling average falls below 75% of expected.** Alert appears in the persistent AlertBar as a P1 (amber) alert. Uses the same hub-side alert engine from Phase 2 (debounce/hysteresis).

### Flock Configuration (FLOCK-05)

- **D-09: Settings page accessible from Coop tab.** A gear icon or "Settings" link on the Coop tab opens a flock configuration page. Set once, rarely changed. Parameters: breed (with lay rate lookup), hatch date (for age factor), flock size, supplemental lighting flag (affects daylight factor).
- **D-10: Breed lay rate table.** A lookup table mapping breed → base daily lay rate. Common breeds pre-populated. Custom breed option for unlisted breeds.
- **D-11: Age decline curve.** Age factor declines from 1.0 at peak laying age to lower values as the flock ages. The curve shape is Claude's discretion based on research into typical production decline.

### Feed Consumption Signals (FLOCK-06)

- **D-12: Feed consumption displayed as daily rate number + 7-day sparkline.** Example: "~120g/day" with a small inline sparkline chart showing the 7-day trend. Lives on the Coop tab near the existing feed level bar.
- **D-13: Feed consumption rate derived from daily load cell weight delta.** Each day's consumption = previous day's weight - current day's weight (accounting for refills). Refill detection: if today's weight > yesterday's weight, a refill occurred — use the delta after the last refill.
- **D-14: Feed consumption alert on >30% drop from 7-day rolling average.** Self-calibrating — no absolute threshold needed. Catches sudden drops relative to the flock's normal consumption. P1 (amber) alert in the AlertBar.

### Unified Overview Screen (UI-01)

- **D-15: New Home tab replaces Zones as the default landing page.** Tab order: Home / Zones / Coop / Recs (4 tabs). The Home tab is the first thing the farmer sees.
- **D-16: Home tab shows compact zone cards + flock summary card.** Zone cards: health badge (GOOD/WARN/CRIT) + current moisture + zone name. Flock summary: door status, egg count today, production trend indicator (up/down/flat arrow).
- **D-17: Readability over density.** Minimal scroll on tablet is acceptable. Prioritize the established Merriweather serif style and visual breathing room over cramming everything above the fold.
- **D-18: Zone cards on Home tab tap through to zone detail (/zones/[id]).** Same behavior as the existing ZoneCard component.
- **D-19: Flock summary card on Home tab taps through to Coop tab.** One tap to see the full flock picture.

### Claude's Discretion

- Exact sparkline implementation for feed consumption (inline SVG, canvas, or lightweight chart lib)
- Age decline curve shape and parameters
- Nesting box sensor data model and MQTT topic structure
- Hen weight subtraction algorithm details
- Home tab responsive breakpoints
- Egg count estimation rounding strategy (floor, round, nearest integer)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and REQUIREMENTS.md.

### Phase 2 patterns (reuse)
- `hub/bridge/alert_engine.py` — Alert engine with hysteresis; extend for production drop and feed consumption alerts
- `hub/bridge/rule_engine.py` — Rule engine pattern; may need extension for flock-related recommendations
- `hub/bridge/health_score.py` — Health score computation pattern; reference for flock health scoring
- `hub/dashboard/src/lib/ws.svelte.ts` — WebSocket store; extend for flock state (egg count, hen present, production data)
- `hub/dashboard/src/lib/types.ts` — TypeScript types; extend for flock data types
- `hub/dashboard/src/lib/CoopPanel.svelte` — Coop tab component; extend with egg count, hen indicator, feed sparkline
- `hub/dashboard/src/lib/ZoneCard.svelte` — Zone card component; reference for compact card variant on Home tab
- `hub/dashboard/src/routes/+layout.svelte` — Layout with TabBar; update for 4 tabs
- `hub/dashboard/src/lib/TabBar.svelte` — Tab bar component; add Home tab
- `docs/mqtt-topic-schema.md` — MQTT topic schema; extend for nesting box sensor topics

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AlertEngine` — extend with `production_drop` and `feed_consumption_drop` alert types; same hysteresis pattern
- `CoopPanel.svelte` — already shows door state, feed level bar, water level bar; extend with egg count, hen indicator, production chart, feed sparkline
- `SensorChart.svelte` — uPlot wrapper; reuse for production overlay chart (add second series for expected)
- `HealthBadge.svelte` — zone health badge; reuse on compact Home tab zone cards
- `ZoneCard.svelte` — has hover lift, tap navigation; create compact variant for Home tab

### Established Patterns
- Hub-side sensor pipeline: MQTT → bridge → TimescaleDB → WebSocket delta → dashboard
- Alert engine: threshold crossing with hysteresis band, hub-side evaluation, WebSocket broadcast
- uPlot chart: direct DOM instantiation in `onMount`, `$effect` rune for range toggles
- Svelte 5 runes: `$state`, `$derived`, `$effect` throughout; Map reassignment for reactivity

### Integration Points
- `hub/bridge/main.py` — `_evaluate_phase2()` loop; add Phase 3 evaluation for egg count, feed consumption, production alerts
- `hub/api/main.py` — mount new routers for flock config and egg data endpoints
- `hub/dashboard/src/lib/ws.svelte.ts` — add flock state fields to DashboardStore snapshot/delta handling
- `hub/dashboard/src/routes/+layout.svelte` — TabBar update from 3 to 4 tabs

</code_context>

<specifics>
## Specific Ideas

- Egg counting is weight-based from a nesting box sensor, NOT manual entry. This is a key architectural decision — egg data flows through the same sensor pipeline as soil sensors.
- The "hen present" animated indicator should make the dashboard feel alive — "you glance and know someone's laying."
- Greenhouse.com-inspired serif aesthetic (Merriweather) carries into Phase 3.
- The Home tab should feel like a command center — everything at a glance, tap to drill in.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-flock-management-and-unified-dashboard*
*Context gathered: 2026-04-10*
