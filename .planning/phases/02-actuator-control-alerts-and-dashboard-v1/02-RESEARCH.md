# Phase 2: Actuator Control, Alerts, and Dashboard V1 - Research

**Researched:** 2026-04-09
**Domain:** SvelteKit SPA routing, FastAPI actuator command flow, MQTT command/ack pattern, TimescaleDB time-series queries, uPlot charting, Python astronomical clock, PWA service worker, hub-side rule engine
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Navigation and Routing (D-01 through D-04)**
- Multi-route SPA with SvelteKit built-in routing; `@sveltejs/adapter-node` stays; no new routing adapters
- Bottom tab bar (3 tabs: Zones / Coop / Recommendations) in `+layout.svelte`, persistent on all routes
- Routes: `/` (Zones + SystemHealthPanel), `/zones/[id]` (detail + irrigation controls + charts), `/coop`, `/recommendations`
- Alert bar taps deep-link via SvelteKit `goto()`

**Recommendation Queue (D-05 through D-08)**
- Card shows: action description + sensor reading with context + explanation. No reason required on reject.
- Deduplication implemented hub-side (rule engine); UI renders hub-provided list only
- Rejection back-off: `RECOMMENDATION_BACKOFF_MINUTES` env var (default: 60); per recommendation type per zone

**Alert Bar (D-09 through D-13)**
- Positioned below header (48px), above page content; part of `+layout.svelte`
- Alerts auto-clear when condition resolves past hysteresis band; no farmer dismiss
- Debounce and hysteresis are hub-side; UI renders whatever alert state WebSocket delivers
- Duplicate alert types are grouped ("Low moisture — 3 zones"); tapping grouped alerts routes to `/` (zones overview)
- Severity: P0 = `--color-offline` (#ef4444); P1 = `--color-stale` (#f59e0b)

**Command Feedback (D-14 through D-17)**
- Button spinner + disabled while command is in flight; no optimistic update
- Status updates only on confirmed ack from the hub (WebSocket delta)
- On timeout/failure: error toast (5 seconds, no auto-retry); button re-enabled
- Single-zone-at-a-time invariant enforced hub-side; UI shows "Another zone is already irrigating." toast

**Irrigation Control (D-18 through D-20)**
- Manual controls on `/zones/[id]`; irrigation status shown prominently
- Sensor-feedback loop: hub commands open, monitors VWC, closes at target or max duration (`IRRIGATION_MAX_DURATION_MINUTES`, default: 30)
- Cool-down suppression: `IRRIGATION_COOLDOWN_MINUTES` env var (default: 120); checked against last irrigation timestamp

**Coop Door Automation (D-21 through D-25)**
- NOAA astronomical clock via `HUB_LATITUDE` / `HUB_LONGITUDE` env vars with configurable offsets (`COOP_OPEN_OFFSET_MINUTES`, `COOP_CLOSE_OFFSET_MINUTES`)
- Hard time limit backstop: `COOP_HARD_CLOSE_HOUR` env var (default: 21); same as Phase 1 D-14
- Limit switch confirmation: 60-second timeout, then stuck-door P0 alert, no further commands until manual reset
- Door states: open / closed / moving / stuck; hub tracks and broadcasts; UI renders with color + label
- Manual override on `/coop` with same spinner/ack/error pattern as irrigation

**Feed and Water Level (D-26 through D-27)**
- Feed: fill percentage (0–100%) from load cell; configurable low threshold; P1 alert on low
- Water: fill percentage or volume; same alert pattern

**Zone Health Composite Score (D-28 through D-29)**
- Computed hub-side; three tiers: green / yellow / red; broadcast in WebSocket state
- HealthBadge visible on ZoneCard; zone detail shows which sensor(s) caused non-green score

**Sensor History Charts (D-30 through D-32)**
- Charts on `/zones/[id]`; three sensors; 7-day and 30-day toggles without page reload
- Chart library: uPlot — direct instantiation in `onMount`/`onDestroy`; no Svelte wrapper package
- Data from new REST endpoint: `GET /api/zones/{zone_id}/history?sensor_type={type}&days=7`; FastAPI serves TimescaleDB time-bucketed data (30-min buckets for 7-day, 2-hour buckets for 30-day)

**PWA (D-33 through D-34)**
- SvelteKit built-in service worker (src/service-worker.ts); pre-cache app shell only; no data endpoint caching
- Mobile-first; bottom tab bar with `env(safe-area-inset-bottom)`; 44px touch targets

**Design System (D-35 through D-36)**
- No component library; hand-authored Svelte 5 runes; 8 new components (listed below)
- Toast.svelte for command errors: fixed position, 5 seconds, `--color-offline`, no library

**New Components**
`TabBar.svelte`, `AlertBar.svelte`, `RecommendationCard.svelte`, `CoopPanel.svelte`,
`SensorChart.svelte`, `CommandButton.svelte`, `HealthBadge.svelte`, `Toast.svelte`

### Claude's Discretion
- FastAPI endpoint design for actuator commands (REST vs WebSocket commands)
- TimescaleDB query design for time-bucketed history data
- uPlot configuration details (axes, colors, grid lines — match dark theme)
- SvelteKit service worker cache strategy specifics
- Exact hysteresis band values for each alert type (within the constraint: alert fires on crossing, clears past hysteresis)
- Back-off window defaults for each recommendation type
- NOAA astronomical clock implementation (Python library vs formula)
- WebSocket delta message types for actuator state, alert state, recommendation queue

### Deferred Ideas (OUT OF SCOPE)
None raised during discussion.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ZONE-05 | 7-day and 30-day sensor history graphs per zone | TimescaleDB time_bucket query + uPlot direct instantiation in onMount; REST history endpoint pattern documented |
| ZONE-06 | Composite health score (green/yellow/red) per zone | Hub-side computation; WebSocket broadcast; HealthBadge component pattern |
| IRRIG-01 | Manual irrigation control — open/close valve command routed hub → edge → relay | REST command endpoint + MQTT command/ack topic pattern; CommandButton spinner pattern |
| IRRIG-02 | Hub enforces single-zone-at-a-time invariant | Hub-side state check before MQTT publish; error response → UI toast |
| IRRIG-04 | Threshold-based irrigation recommendations in queue | Rule engine in bridge/main.py; recommendation queue WebSocket broadcast |
| IRRIG-05 | Sensor-feedback irrigation loop — VWC-targeted close | Hub monitors VWC readings during active irrigation; closes on target or timeout |
| IRRIG-06 | Irrigation recommendations suppressed during cool-down window | Last-irrigation timestamp tracked in hub state; rule engine checks before generating recommendation |
| COOP-01 | Coop door opens at sunrise, closes at sunset; configurable offset | astral 3.2 Python library; `sun()` from `astral.sun`; scheduler runs in hub |
| COOP-02 | Hard time limit backstop for coop door | Same `COOP_HARD_CLOSE_HOUR` env var as Phase 1 D-14; hub scheduler compares current time |
| COOP-03 | Limit switch confirmation within 60 seconds | Hub listens for ack on `farm/coop/ack/{command_id}`; asyncio timeout 60s; raises P0 alert on miss |
| COOP-05 | Dashboard shows coop door state + manual override | `actuator_state` WebSocket delta; CoopPanel component; CommandButton door variant |
| COOP-06 | Feed level — fill percentage + low alert | `feed_weight` sensor already in MQTT schema; hub converts to percentage; alert broadcast |
| COOP-07 | Water level monitoring + low alert | `water_level` sensor already in MQTT schema; same pattern as feed |
| AI-01 | Recommendation queue UI — action, sensor values, explanation, approve/reject | RecommendationCard component; WebSocket `recommendation_queue` delta type |
| AI-02 | Rule-based recommendation engine generates irrigation/coop recommendations | Rule engine module in bridge pipeline; reads in-memory zone state; emits `recommendation_queue` deltas |
| AI-04 | Recommendations deduplicated — pending suppresses duplicates | In-memory recommendation registry on hub; checked before emitting new recommendation |
| AI-05 | Rejection back-off window prevents re-recommendation | Hub tracks `rejected_at` + `backoff_minutes` per (zone_id, recommendation_type); checked before emit |
| UI-02 | P0/P1 persistent alert bar; groups duplicates with count | AlertBar in +layout.svelte; receives `alert_state` delta; renders grouped rows |
| UI-03 | Alert bar items are tappable, route to relevant screen | SvelteKit `goto()` in alert row click handler; deep-link targets defined per alert type |
| UI-05 | PWA installable on iOS and Android | SvelteKit service worker at src/service-worker.ts; manifest.webmanifest already exists; HTTPS via Caddy already configured |
| UI-06 | Mobile-first responsive layout, usable on phone in yard | Existing spacing system + 44px touch targets; tab bar safe-area-inset-bottom; already established in Phase 1 |
| NOTF-01 | In-app alerts in persistent alert bar | Alert evaluation on hub (bridge); broadcast via WebSocket `alert_state` delta; rendered by AlertBar |
| NOTF-02 | Alert debounce + hysteresis | Hub-side: alert fires on threshold crossing; clears when value recovers past hysteresis band; no re-fire on sustained condition |
</phase_requirements>

---

## Summary

Phase 2 is a full-stack build across three layers: (1) the hub backend gains a rule engine, an alert system, actuator command routing, and a scheduler; (2) the FastAPI service gains five new REST endpoints and extended WebSocket message types; (3) the SvelteKit frontend is restructured into a multi-route SPA with a bottom tab bar, alert bar, seven new components, and a PWA service worker.

The existing codebase is healthy and well-structured. The bridge (`hub/bridge/main.py`), WebSocket manager (`hub/api/ws_manager.py`), and TypeScript store (`ws.svelte.ts`) are all extension points, not rewrites. The WebSocket delta/snapshot pattern is clean: new Phase 2 message types (`alert_state`, `recommendation_queue`, `actuator_state`, `zone_health_score`, `feed_level`, `water_level`) simply extend the existing `WSMessage` union type in `types.ts` and the `NotifyPayload` model in `hub/api/models.py`.

The critical design choice left to discretion is how the hub routes actuator commands: REST POST is the right answer (not WebSocket commands) because it gives a synchronous request/response channel for the command ack flow, while the confirmed state is broadcast back to clients via WebSocket. The MQTT command/ack topic prefixes are already reserved in the Phase 1 schema (`farm/{node_id}/commands/{command_type}` and `farm/{node_id}/ack/{command_id}`).

**Primary recommendation:** Use REST POST for actuator commands, `asyncio.wait_for` with 10-second timeout for MQTT ack, hub-side in-memory state for recommendation/alert tracking, `astral` 3.2 for astronomical clock, and SvelteKit's built-in service worker (`$service-worker` module) for PWA — no additional libraries needed.

---

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| SvelteKit | 2.21.0 | Routing, SSR, service worker | Installed |
| Svelte 5 | 5.28.1 | Reactive UI, runes ($state/$derived/$props) | Installed |
| @sveltejs/adapter-node | 5.2.13 | Node.js server adapter | Installed |
| FastAPI | 0.135.3 | REST API + WebSocket server | Installed |
| asyncpg | 0.31.0 | Async PostgreSQL/TimescaleDB queries | Installed |
| aiomqtt | 2.5.1 | MQTT subscriber in bridge | Installed |
| pydantic | 2.12.5 | Data models and validation | Installed |
| lucide-svelte | 0.487.0 | Icons (Sprout, Home, Bell, DoorOpen, DoorClosed, AlertTriangle, Loader2, XCircle) | Installed |
| vitest | 3.1.1 | Component and unit testing | Installed |
| @testing-library/svelte | 5.2.6 | Svelte component testing | Installed |

### New Dependencies to Install

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| uplot | 1.6.32 (latest) | Time-series canvas charts | Locked decision D-31; ~45KB, MIT, no wrapper needed |
| astral | 3.2 (latest) | Sunrise/sunset from lat/long | Pure Python, no system deps; identified in CONTEXT.md specifics |

**Installation:**
```bash
# Dashboard frontend
cd hub/dashboard && npm install uplot

# Hub bridge (add to requirements.txt)
# astral==3.2
```

**Version verification:** Confirmed via `npm view uplot version` (1.6.32) and `pip3 index versions astral` (3.2).

### What Does NOT Need to Be Installed

| Problem | Don't Install | Use Instead |
|---------|--------------|-------------|
| Spinner animation | Any spinner library | CSS animation on `Loader2` Lucide icon |
| Toast notifications | react-toastify or similar | Hand-authored `Toast.svelte` |
| Service worker | workbox, @vite-pwa/sveltekit | SvelteKit built-in `$service-worker` module |
| uPlot Svelte wrapper | uplot-svelte or uplot-wrappers | Direct instantiation in `onMount`/`onDestroy` |
| WebSocket client library | socket.io-client | Native `WebSocket` API (already used) |

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)

```
hub/
├── api/
│   ├── main.py                  # Add 5 new REST endpoints
│   ├── models.py                # Extend NotifyPayload; add command/alert/recommendation models
│   ├── ws_manager.py            # Extend to cache alert_state, recommendations, actuator_state
│   ├── actuator_router.py       # NEW — POST endpoints for irrigation and coop door commands
│   └── history_router.py        # NEW — GET /api/zones/{id}/history endpoint
├── bridge/
│   ├── main.py                  # Extend with recommendation rule engine, alert evaluation
│   ├── models.py                # Add ActuatorCommandPayload, AckPayload, RecommendationModel, AlertModel
│   ├── rule_engine.py           # NEW — threshold-based recommendation generation
│   ├── alert_engine.py          # NEW — debounce/hysteresis alert evaluation
│   └── coop_scheduler.py        # NEW — NOAA astronomical clock scheduler
hub/dashboard/src/
├── routes/
│   ├── +layout.svelte           # REWRITE — add TabBar, AlertBar, WebSocket lifecycle
│   ├── +page.svelte             # EXTEND — ZoneCard gets HealthBadge + tap-to-navigate
│   ├── zones/
│   │   └── [id]/
│   │       └── +page.svelte     # NEW — zone detail with irrigation controls + SensorChart × 3
│   ├── coop/
│   │   └── +page.svelte         # NEW — CoopPanel
│   └── recommendations/
│       └── +page.svelte         # NEW — RecommendationCard list
├── lib/
│   ├── types.ts                 # EXTEND — new WS message types, recommendation, alert types
│   ├── ws.svelte.ts             # EXTEND — handle 6 new delta message types
│   ├── TabBar.svelte            # NEW
│   ├── AlertBar.svelte          # NEW
│   ├── CommandButton.svelte     # NEW
│   ├── HealthBadge.svelte       # NEW
│   ├── RecommendationCard.svelte # NEW
│   ├── CoopPanel.svelte         # NEW
│   ├── SensorChart.svelte       # NEW — uPlot wrapper
│   ├── Toast.svelte             # NEW
│   └── ZoneCard.svelte          # EXTEND — add HealthBadge, tap navigation
└── service-worker.ts            # NEW — app shell precache
```

### Pattern 1: Actuator Command Flow (REST + MQTT + WebSocket ack)

**What:** Farmer taps a button → REST POST → hub publishes MQTT command → edge executes → edge publishes ack → hub receives ack → hub broadcasts WebSocket delta → UI updates.

**When to use:** All actuator commands (irrigation valve open/close, coop door open/close).

```python
# Source: CONTEXT.md D-14, D-15; FastAPI docs
# hub/api/actuator_router.py

import asyncio, uuid
from fastapi import APIRouter, HTTPException
from aiomqtt import Client as MQTTClient

router = APIRouter()
# Shared pending-ack registry: {command_id: asyncio.Event}
pending_acks: dict[str, asyncio.Event] = {}

@router.post("/api/actuators/irrigate")
async def irrigate(zone_id: str, action: str):  # action: "open" | "close"
    command_id = str(uuid.uuid4())
    ack_event = asyncio.Event()
    pending_acks[command_id] = ack_event

    # Publish MQTT command (farm/{node_id}/commands/irrigate)
    async with MQTTClient(MQTT_HOST) as client:
        payload = {"command_id": command_id, "action": action, "zone_id": zone_id}
        await client.publish(f"farm/{zone_id}/commands/irrigate", json.dumps(payload), qos=1)

    try:
        await asyncio.wait_for(ack_event.wait(), timeout=10.0)  # D-17: 10s server-side timeout
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Command timeout — edge node did not ack")
    finally:
        pending_acks.pop(command_id, None)

    return {"status": "confirmed", "command_id": command_id}
```

**The ack receiver** (in bridge MQTT loop) calls `pending_acks[command_id].set()` when it sees `farm/{node_id}/ack/{command_id}`. On ack, it also broadcasts the actuator state delta via WebSocket.

### Pattern 2: Hub-Side Rule Engine (bridge extension)

**What:** After each sensor reading is ingested, the rule engine evaluates the zone's current state against configured thresholds. If conditions are met and no pending recommendation / cool-down blocks it, a new recommendation is added to the queue and broadcast.

**When to use:** Called inside `process_sensor_message()` after TimescaleDB write.

```python
# Source: CONTEXT.md D-07, D-08, D-19, D-20
# hub/bridge/rule_engine.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import os

BACKOFF_MINUTES = int(os.getenv("RECOMMENDATION_BACKOFF_MINUTES", "60"))
COOLDOWN_MINUTES = int(os.getenv("IRRIGATION_COOLDOWN_MINUTES", "120"))

@dataclass
class RecommendationState:
    recommendation_id: str
    zone_id: str
    rec_type: str          # e.g. "irrigate"
    status: str            # "pending" | "approved" | "rejected"
    created_at: datetime
    rejected_at: Optional[datetime] = None
    last_irrigated_at: Optional[datetime] = None

class RuleEngine:
    def __init__(self):
        self._recommendations: dict[str, RecommendationState] = {}  # keyed by zone_id+type
        self._last_irrigated: dict[str, datetime] = {}              # zone_id -> datetime

    def evaluate_zone(self, zone_id: str, sensor_type: str, value: float,
                      zone_config: dict) -> Optional[dict]:
        """Returns a new recommendation dict or None."""
        if sensor_type != "moisture":
            return None

        low_threshold = zone_config.get("vwc_low_threshold", 30.0)
        if value >= low_threshold:
            return None

        key = f"{zone_id}:irrigate"
        existing = self._recommendations.get(key)

        # D-07: suppress if pending
        if existing and existing.status == "pending":
            return None

        # D-08: suppress if in rejection back-off window
        if existing and existing.status == "rejected" and existing.rejected_at:
            elapsed = (datetime.now(timezone.utc) - existing.rejected_at).total_seconds() / 60
            if elapsed < BACKOFF_MINUTES:
                return None

        # D-20: suppress if in cool-down window
        last = self._last_irrigated.get(zone_id)
        if last:
            elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
            if elapsed < COOLDOWN_MINUTES:
                return None

        # Emit new recommendation
        import uuid
        rec_id = str(uuid.uuid4())
        self._recommendations[key] = RecommendationState(
            recommendation_id=rec_id, zone_id=zone_id, rec_type="irrigate",
            status="pending", created_at=datetime.now(timezone.utc)
        )
        return {
            "recommendation_id": rec_id,
            "zone_id": zone_id,
            "type": "irrigate",
            "action_description": f"Irrigate {zone_id}",
            "sensor_reading": f"Moisture: {value:.1f}% VWC (target range: {low_threshold}–{zone_config.get('vwc_high_threshold', 60.0)}%)",
            "explanation": "Below low threshold",
        }
```

### Pattern 3: Alert Debounce and Hysteresis (hub-side)

**What:** Alert fires when a value crosses a threshold. It clears only when the value recovers past a hysteresis band (threshold + band). The same condition does not re-fire while it is sustained.

**When to use:** All alert types (low moisture, low feed, low water, stuck door, node offline).

```python
# Source: CONTEXT.md D-10, D-11; NOTF-02
# hub/bridge/alert_engine.py

# Hysteresis bands (discretion area):
HYSTERESIS = {
    "moisture_low": 5.0,   # clears when VWC recovers to low_threshold + 5%
    "feed_low": 5.0,       # clears when feed recovers to low_threshold + 5%
    "water_low": 5.0,
}

class AlertEngine:
    def __init__(self):
        self._active_alerts: dict[str, dict] = {}  # alert_key -> alert dict

    def evaluate(self, alert_key: str, value: float,
                 fire_threshold: float, hysteresis: float) -> tuple[bool, bool]:
        """
        Returns (changed, is_active).
        Fires when value < fire_threshold.
        Clears when value > fire_threshold + hysteresis.
        """
        was_active = alert_key in self._active_alerts
        if not was_active and value < fire_threshold:
            self._active_alerts[alert_key] = {"key": alert_key, "fired_at": ...}
            return True, True   # changed, now active
        elif was_active and value > (fire_threshold + hysteresis):
            del self._active_alerts[alert_key]
            return True, False  # changed, now cleared
        return False, was_active  # no change
```

### Pattern 4: Astronomical Clock Scheduler (astral 3.2)

**What:** Calculate today's sunrise/sunset from lat/long, add configured offset, schedule MQTT coop-door commands.

```python
# Source: astral 3.2 docs (https://sffjunkie.github.io/astral/package.html)
# hub/bridge/coop_scheduler.py

from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime, timezone, timedelta
import asyncio, os

LAT = float(os.getenv("HUB_LATITUDE", "37.7749"))
LON = float(os.getenv("HUB_LONGITUDE", "-122.4194"))
OPEN_OFFSET = int(os.getenv("COOP_OPEN_OFFSET_MINUTES", "0"))
CLOSE_OFFSET = int(os.getenv("COOP_CLOSE_OFFSET_MINUTES", "0"))
HARD_CLOSE_HOUR = int(os.getenv("COOP_HARD_CLOSE_HOUR", "21"))

def get_today_schedule() -> dict:
    location = LocationInfo(latitude=LAT, longitude=LON)
    s = sun(location.observer, date=date.today(), tzinfo=timezone.utc)
    open_time = s["sunrise"] + timedelta(minutes=OPEN_OFFSET)
    close_time = s["sunset"] + timedelta(minutes=CLOSE_OFFSET)
    # Hard close backstop: no later than HARD_CLOSE_HOUR local
    hard_close = datetime.now(timezone.utc).replace(
        hour=HARD_CLOSE_HOUR, minute=0, second=0, microsecond=0
    )
    close_time = min(close_time, hard_close)
    return {"open_at": open_time, "close_at": close_time}
```

**Scheduler loop:** Run as `asyncio.create_task` in the bridge. Calculates schedule once per day at midnight, sets two `asyncio.sleep` calls (seconds until open_at and close_at), then publishes coop-door commands.

### Pattern 5: TimescaleDB Time-Bucketed History Query

**What:** Aggregate raw sensor readings into time buckets for chart display. Reduces payload from thousands of rows to ~336 (7-day / 30-min) or ~360 (30-day / 2-hour).

```python
# Source: TimescaleDB docs (https://docs.timescale.com/api/latest/hyperfunctions/time_bucket/)
# hub/api/history_router.py

HISTORY_QUERY = """
    SELECT
        time_bucket($1::interval, time) AS bucket,
        AVG(value) AS avg_value
    FROM sensor_readings
    WHERE zone_id = $2
      AND sensor_type = $3
      AND time >= NOW() - $4::interval
      AND quality != 'BAD'
    GROUP BY bucket
    ORDER BY bucket ASC
"""

@router.get("/api/zones/{zone_id}/history")
async def zone_history(zone_id: str, sensor_type: str, days: int = 7,
                       db: asyncpg.Pool = Depends(get_db)):
    bucket_interval = "30 minutes" if days <= 7 else "2 hours"
    range_interval = f"{days} days"
    rows = await db.fetch(HISTORY_QUERY, bucket_interval, zone_id, sensor_type, range_interval)
    return [{"ts": row["bucket"].isoformat(), "value": row["avg_value"]} for row in rows]
```

### Pattern 6: uPlot Direct Instantiation in Svelte 5

**What:** Instantiate uPlot in `onMount`, destroy in `onDestroy`. Re-instantiate when time range changes (fetch new data, recreate chart with new data).

```typescript
// Source: uPlot README (https://github.com/leeoniya/uPlot#readme); CONTEXT.md D-31
// hub/dashboard/src/lib/SensorChart.svelte

<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import uPlot from 'uplot';
  import 'uplot/dist/uPlot.min.css';

  let { zoneId, sensorType, days = $bindable(7) } = $props();
  let container: HTMLDivElement;
  let chart: uPlot | null = null;

  const SERIES_COLORS: Record<string, string> = {
    moisture: '#4ade80',   // --color-accent
    ph: '#60a5fa',
    temperature: '#fb923c',
  };

  async function loadAndRender() {
    chart?.destroy();
    const res = await fetch(`/api/zones/${zoneId}/history?sensor_type=${sensorType}&days=${days}`);
    const data = await res.json();
    // uPlot expects [timestamps_array, values_array]
    const timestamps = data.map((d: any) => new Date(d.ts).getTime() / 1000);
    const values = data.map((d: any) => d.value);

    chart = new uPlot({
      width: container.clientWidth,
      height: days <= 7 ? 160 : 160,  // responsive height via CSS
      series: [
        {},  // x-axis (timestamps)
        { stroke: SERIES_COLORS[sensorType], width: 1.5 },
      ],
      axes: [
        { stroke: '#94a3b8', grid: { stroke: '#2d3149' }, ticks: { stroke: '#2d3149' }, size: 14 },
        { stroke: '#94a3b8', grid: { stroke: '#2d3149' }, ticks: { stroke: '#2d3149' }, size: 14 },
      ],
      cursor: { stroke: '#6b7280' },
    }, [timestamps, values], container);
  }

  onMount(loadAndRender);
  onDestroy(() => chart?.destroy());

  // Re-render when days changes (time range toggle)
  $effect(() => { if (days) loadAndRender(); });
</script>

<div bind:this={container}></div>
```

**Critical uPlot pitfall:** uPlot CSS must be imported (`uplot/dist/uPlot.min.css`). Without it, the chart cursor and tooltip styling break.

### Pattern 7: SvelteKit Service Worker (PWA)

**What:** Pre-cache the app shell (HTML, CSS, JS, manifest, icons) so the dashboard renders offline. Do NOT cache `/api/*` or `/ws/*`.

```typescript
// Source: SvelteKit docs (https://svelte.dev/docs/kit/service-workers)
// hub/dashboard/src/service-worker.ts

/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />
/// <reference types="@sveltejs/kit" />

import { build, files, version } from '$service-worker';

const CACHE = `farm-${version}`;
const ASSETS = [...build, ...files];  // build = vite output; files = /static assets

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
});

self.addEventListener('fetch', (event: FetchEvent) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  // Do NOT cache API or WebSocket endpoints
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;

  event.respondWith(
    caches.match(event.request).then(cached => cached ?? fetch(event.request))
  );
});
```

**Important:** The service worker file at `src/service-worker.ts` is detected automatically by SvelteKit and registered during build. It does NOT work in `npm run dev` — only in `npm run build && npm run preview` or production.

### Pattern 8: WebSocket Delta Extension (TypeScript types)

**What:** Extend `WSMessage` union type to include Phase 2 delta message types.

```typescript
// Source: CONTEXT.md Real-Time Behavior Contract; existing types.ts
// Extension to hub/dashboard/src/lib/types.ts

export interface AlertEntry {
  key: string;            // e.g. "moisture_low:zone-01"
  severity: 'P0' | 'P1';
  message: string;        // e.g. "Low moisture — Zone A"
  deep_link: string;      // e.g. "/zones/zone-01"
  count: number;          // >=1; >1 = grouped
}

export interface AlertStateDelta {
  type: 'alert_state';
  alerts: AlertEntry[];   // full current list; UI replaces its state
}

export interface Recommendation {
  recommendation_id: string;
  zone_id: string;
  rec_type: string;
  action_description: string;
  sensor_reading: string;
  explanation: string;
}

export interface RecommendationQueueDelta {
  type: 'recommendation_queue';
  recommendations: Recommendation[];  // full current queue
}

export interface ActuatorStateDelta {
  type: 'actuator_state';
  device: 'irrigation' | 'coop_door';
  zone_id?: string;            // for irrigation
  state: string;               // "open" | "closed" | "moving" | "stuck" | "irrigating"
}

export interface ZoneHealthScoreDelta {
  type: 'zone_health_score';
  zone_id: string;
  score: 'green' | 'yellow' | 'red';
  contributing_sensors: string[];  // e.g. ["moisture"] when yellow/red
}

export interface FeedLevelDelta {
  type: 'feed_level';
  percentage: number;   // 0-100
  below_threshold: boolean;
}

export interface WaterLevelDelta {
  type: 'water_level';
  percentage: number;
  below_threshold: boolean;
}

export type WSMessage =
  | DashboardSnapshot
  | SensorDelta
  | HeartbeatDelta
  | AlertStateDelta
  | RecommendationQueueDelta
  | ActuatorStateDelta
  | ZoneHealthScoreDelta
  | FeedLevelDelta
  | WaterLevelDelta;
```

### Anti-Patterns to Avoid

- **Optimistic UI updates:** Never update actuator state before hub ack. CONTEXT.md D-15 is explicit — wait for WebSocket delta.
- **Client-side alert debounce:** All debounce/hysteresis logic lives in the hub. UI is a dumb renderer of hub-provided alert state.
- **Client-side recommendation deduplication:** Same principle — the hub's rule engine is the source of truth. UI renders what it receives.
- **Polling for history data:** Use a single REST fetch per time-range selection; do not poll. The time-range toggle re-fetches once.
- **uPlot auto-resize without observer:** uPlot charts do not auto-resize on window resize. Attach a `ResizeObserver` to the container and call `chart.setSize()` on resize.
- **Service worker in dev mode:** SvelteKit service workers only run after `npm run build`. Dev testing of SW requires `npm run preview`.
- **asyncio.sleep in bridge without structured concurrency:** The coop scheduler must run as a separate `asyncio.create_task` alongside the MQTT loop, not blocking it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sunrise/sunset calculation | Custom NOAA formula implementation | `astral` 3.2 (`astral.sun.sun()`) | Handles edge cases: polar day/night, DST, timezone conversion; pure Python, no system deps |
| Time-series aggregation | Manual GROUP BY + Python-side averaging | `time_bucket()` in TimescaleDB | Native hypertable index; query performance at scale; reduces payload by 20–100x |
| Service worker caching | Custom fetch handler logic | SvelteKit `$service-worker` module (`build`, `files`, `version`) | Auto-generates asset manifest at build time; versioned cache; no stale asset risk |
| Chart rendering | SVG-based custom chart | uPlot 1.6.32 | Canvas-based: no DOM manipulation per frame; handles 10k+ points; mobile scroll performance |
| Command ack tracking | Database-backed ack queue | In-memory `dict[str, asyncio.Event]` with `asyncio.wait_for` | Acks are transient (10s window); no persistence needed; asyncio events are zero-overhead |
| WebSocket state cache | Redis or external cache | In-memory dicts in `ws_manager.py` | Single-process FastAPI; all clients get the same full snapshot from the same process state |

**Key insight:** The hub is a single-process asyncio service. In-memory state (recommendation registry, alert state, pending ack events, actuator states) is correct for this architecture. Do not introduce external state stores (Redis, SQLite) for ephemeral runtime state.

---

## Common Pitfalls

### Pitfall 1: Svelte 5 Map Reactivity
**What goes wrong:** Mutating a `Map` directly (e.g., `this.zones.set(...)`) does not trigger Svelte 5 reactive updates. The UI does not re-render.
**Why it happens:** Svelte 5 `$state` tracks object identity, not deep mutations.
**How to avoid:** Always reassign: `this.zones = new Map(this.zones.set(key, value))`. This pattern is already established in `ws.svelte.ts` (line 93) — apply the same pattern for all new delta handlers.
**Warning signs:** UI shows stale values after WebSocket delta; no console errors.

### Pitfall 2: uPlot Container Width at Mount Time
**What goes wrong:** uPlot `width` is set to `container.clientWidth` in `onMount`, but the container has `clientWidth: 0` because the component mounted before layout completed.
**Why it happens:** `onMount` fires synchronously before the browser paint cycle completes layout.
**How to avoid:** Use `requestAnimationFrame` inside `onMount` before reading `clientWidth`, or set `width: container.offsetWidth` after a `tick()` call. Alternatively, set a CSS `min-width` on the container to guarantee a non-zero value.
**Warning signs:** Chart renders as 0px wide; invisible on first load; visible only after resize.

### Pitfall 3: SvelteKit Route Params Type Safety
**What goes wrong:** `$page.params.id` is typed as `string` but may be undefined if the route file is misnamed.
**Why it happens:** SvelteKit uses filename-based routing. `/routes/zones/[id]/+page.svelte` must use exactly `[id]` to match `$page.params.id`.
**How to avoid:** Use `load` functions with `params.id` typed via `PageLoad` from SvelteKit. Run `svelte-kit sync` after creating new routes.

### Pitfall 4: asyncio Event Loop in FastAPI Background Tasks
**What goes wrong:** The coop scheduler `asyncio.create_task` created inside `bridge_loop()` gets cancelled when the MQTT connection drops and restarts.
**Why it happens:** `asyncio.create_task` created inside a coroutine is tied to the task's lifetime.
**How to avoid:** Create the scheduler task at the `main()` level using `asyncio.gather(bridge_loop(...), coop_scheduler_loop(...))` so it is independent of the MQTT reconnect loop.

### Pitfall 5: WebSocket Full Snapshot Must Include Phase 2 State
**What goes wrong:** A new dashboard client connects and sees the Zones tab correctly, but AlertBar is empty and RecommendationCard list is empty — even though alerts and recommendations are active.
**Why it happens:** The existing `DashboardSnapshot` in `ws_manager.py` only includes `zones` and `nodes`. New Phase 2 state (alerts, recommendations, actuator states, health scores, feed/water levels) must be added to the snapshot.
**How to avoid:** Extend `ws_manager.py`'s `connect()` method to include all Phase 2 state in the initial snapshot. Extend `WebSocketManager` to cache `_alert_state`, `_recommendation_queue`, `_actuator_states`, `_zone_health_scores`, `_feed_level`, `_water_level`.

### Pitfall 6: MQTT Command QoS and Command ID Uniqueness
**What goes wrong:** Hub publishes a command at QoS 1; edge node acks twice due to QoS 1 re-delivery; hub processes two acks and tries to set an already-resolved `asyncio.Event`.
**Why it happens:** QoS 1 guarantees at-least-once delivery; duplicate acks are possible.
**How to avoid:** The hub's ack handler must use `event.set()` idempotently (already idempotent in asyncio). Clean up `pending_acks[command_id]` immediately after the first ack resolves the event. The edge node should use the command_id as an idempotency key.

### Pitfall 7: uPlot CSS Import
**What goes wrong:** Chart renders but crosshair cursor is invisible; tooltip position is wrong.
**Why it happens:** uPlot requires `uplot/dist/uPlot.min.css` to be imported for cursor/tooltip styling.
**How to avoid:** Import the CSS in `SensorChart.svelte`: `import 'uplot/dist/uPlot.min.css'`. Vite will bundle it correctly.

### Pitfall 8: astral Timezone Handling
**What goes wrong:** Calculated sunrise time is off by hours — appears as UTC rather than local time.
**Why it happens:** `sun()` returns timezone-aware datetimes, but the `tzinfo` parameter must be set correctly. If `tzinfo` is omitted, result is in UTC.
**How to avoid:** Pass `tzinfo=timezone.utc` to `sun()` and store all times as UTC in the scheduler. Convert to local display time only in the UI using the browser's `Intl.DateTimeFormat`.

---

## WebSocket Delta Message Design (Discretion Area)

The CONTEXT.md leaves WebSocket delta message types to Claude's discretion. Recommendation:

**Use full-list deltas (not partial patches) for alert state and recommendation queue.** On each change, the hub sends the complete current list. The UI replaces its state entirely. This is simpler than tracking individual add/remove operations and avoids ordering bugs. The lists are small (< 10 items typically).

**Use targeted deltas for actuator state and sensor readings.** These are frequent (every 60s for sensors) and targeted — only the changed entity is sent.

| Delta type | Strategy | Rationale |
|-----------|----------|-----------|
| `alert_state` | Full list | List is small; simplifies UI state management |
| `recommendation_queue` | Full list | Queue is small; avoids ordering bugs |
| `zone_health_score` | Targeted (zone_id + score) | Per-zone, frequent updates expected |
| `actuator_state` | Targeted (device + state) | Per-device, event-driven |
| `feed_level` | Targeted (percentage) | Single value, frequent |
| `water_level` | Targeted (percentage) | Single value, frequent |

---

## Hysteresis Band Recommendations (Discretion Area)

| Alert type | Fire threshold | Hysteresis band | Clear when |
|-----------|---------------|-----------------|------------|
| Moisture low | `vwc_low_threshold` (per zone config) | +5% VWC | VWC > low_threshold + 5% |
| Feed low | `FEED_LOW_THRESHOLD_PCT` env var (default: 20%) | +5% | Feed > 25% |
| Water low | `WATER_LOW_THRESHOLD_PCT` env var (default: 20%) | +5% | Water > 25% |
| Node offline | 3 missed heartbeats (Phase 1 D-08 equivalent) | 1 heartbeat received | Node sends any heartbeat |

pH out-of-range alert is listed in NOTF-01 but not in Phase 2 requirements — it appears in the requirement description but COOP-06/07 and IRRIG-04 focus on moisture/feed/water. Implement pH alerting using the same pattern; fire threshold from zone config `ph_low_threshold` / `ph_high_threshold`; 0.2 pH hysteresis band.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Dashboard build, npm | ✓ | v25.3.0 | — |
| npm | Package install | ✓ | 11.7.0 | — |
| Python 3 | hub bridge, hub api | ✓ | 3.10.17 | — |
| pip3 | Python package install | ✓ | 23.0.1 | — |
| Docker | Container orchestration | ✓ | 29.1.4 | — |
| Docker Compose | Service stack | ✓ | v5.0.1 | — |
| uPlot (npm) | SensorChart.svelte | ✗ (not yet installed) | 1.6.32 available | — (required) |
| astral (pip) | coop_scheduler.py | ✗ (not yet installed) | 3.2 available | Simple formula (complex, not recommended) |
| TimescaleDB | time_bucket queries | ✓ (in Docker Compose) | Via existing stack | — |
| Mosquitto MQTT | Command/ack routing | ✓ (in Docker Compose) | Via existing stack | — |

**Missing dependencies with no fallback:**
- `uplot` npm package — required for SensorChart.svelte. Install: `npm install uplot` in `hub/dashboard/`.

**Missing dependencies with fallback:**
- `astral` pip package — required for coop door astronomical schedule. Alternative is a pure-Python NOAA formula (~50 lines), but `astral` handles edge cases (polar regions, DST) correctly. Strong recommendation: use `astral`. Install: add `astral==3.2` to `hub/bridge/requirements.txt`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 3.1.1 + @testing-library/svelte 5.2.6 |
| Config file | `hub/dashboard/vitest.config.ts` (exists) |
| Quick run command | `cd hub/dashboard && npm test -- --run` |
| Full suite command | `cd hub/dashboard && npm test -- --run --reporter=verbose` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ZONE-05 | SensorChart renders with data; time-range toggle re-fetches | unit (mock fetch) | `npm test -- --run src/lib/SensorChart.test.ts` | ❌ Wave 0 |
| ZONE-06 | HealthBadge renders correct color/label for green/yellow/red | unit | `npm test -- --run src/lib/HealthBadge.test.ts` | ❌ Wave 0 |
| IRRIG-01 | CommandButton shows spinner on click, re-enables on error | unit | `npm test -- --run src/lib/CommandButton.test.ts` | ❌ Wave 0 |
| IRRIG-02 | Hub returns 409 / error toast appears for second-zone attempt | unit (mock API) | `npm test -- --run src/lib/CommandButton.test.ts` | ❌ Wave 0 |
| AI-01 | RecommendationCard renders action/sensor/explanation/buttons | unit | `npm test -- --run src/lib/RecommendationCard.test.ts` | ❌ Wave 0 |
| UI-02 | AlertBar renders P0 row red, P1 row amber; groups duplicates | unit | `npm test -- --run src/lib/AlertBar.test.ts` | ❌ Wave 0 |
| UI-03 | AlertBar row tap navigates to deep-link target | unit (mock goto) | `npm test -- --run src/lib/AlertBar.test.ts` | ❌ Wave 0 |
| NOTF-02 | Alert engine fires on threshold, stays until hysteresis clears | unit (Python) | `cd hub/bridge && python -m pytest tests/test_alert_engine.py` | ❌ Wave 0 |
| COOP-01 | get_today_schedule() returns correct sunrise/sunset with offset | unit (Python) | `cd hub/bridge && python -m pytest tests/test_coop_scheduler.py` | ❌ Wave 0 |
| IRRIG-04 | RuleEngine emits recommendation when VWC < threshold | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ Wave 0 |
| AI-04 | RuleEngine suppresses duplicate when one is pending | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ Wave 0 |
| AI-05 | RuleEngine suppresses recommendation during back-off window | unit (Python) | `cd hub/bridge && python -m pytest tests/test_rule_engine.py` | ❌ Wave 0 |
| UI-05 | PWA manifest has required fields; service worker registers | manual | Install in Chrome devtools; `npm run build && npm run preview` | — |
| COOP-03 | Stuck-door alert fires when ack not received in 60s | unit (Python, asyncio mock) | `cd hub/bridge && python -m pytest tests/test_actuator.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd hub/dashboard && npm test -- --run` (Svelte components only, ~5s)
- **Per wave merge:** Full suite: `cd hub/dashboard && npm test -- --run` + `cd hub/bridge && python -m pytest tests/` 
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `hub/dashboard/src/lib/SensorChart.test.ts` — covers ZONE-05
- [ ] `hub/dashboard/src/lib/HealthBadge.test.ts` — covers ZONE-06
- [ ] `hub/dashboard/src/lib/CommandButton.test.ts` — covers IRRIG-01, IRRIG-02
- [ ] `hub/dashboard/src/lib/RecommendationCard.test.ts` — covers AI-01
- [ ] `hub/dashboard/src/lib/AlertBar.test.ts` — covers UI-02, UI-03
- [ ] `hub/bridge/tests/__init__.py` — Python test package init
- [ ] `hub/bridge/tests/test_alert_engine.py` — covers NOTF-02
- [ ] `hub/bridge/tests/test_rule_engine.py` — covers IRRIG-04, AI-04, AI-05
- [ ] `hub/bridge/tests/test_coop_scheduler.py` — covers COOP-01
- [ ] `hub/bridge/tests/test_actuator.py` — covers COOP-03
- [ ] Python test framework: `pip install pytest pytest-asyncio` in bridge container/venv

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte 3/4 reactive stores (`writable`, `derived`) | Svelte 5 runes (`$state`, `$derived`, `$effect`) | Svelte 5 (2024) | No `writable`/`get` needed; class-based stores work with `$state` |
| astral 2.x (`import astral; city = astral.Location(...)`) | astral 3.x (`from astral import LocationInfo; from astral.sun import sun`) | astral 3.0 (2021) | API is completely different; 2.x code will fail with 3.x |
| uPlot `setData` for updates | Destroy and recreate for time-range changes | Ongoing | For simple range toggles (not live streaming), recreate is simpler and avoids stale series state |
| SvelteKit layout-level WebSocket | Component-level `onMount` | Phase 1 decision | Phase 2 moves WS lifecycle to `+layout.svelte` so all routes share the same connection |

**Deprecated/outdated:**
- astral 2.x API (`astral.Location`, `.sun`): completely removed in 3.x. Only use `LocationInfo` + `astral.sun.sun()`.
- SvelteKit `$app/navigation` `goto` import path: remains `import { goto } from '$app/navigation'` in SvelteKit 2 — unchanged.

---

## Open Questions

1. **Zone configuration source**
   - What we know: Zone config (vwc_low_threshold, vwc_high_threshold, ph_low_threshold, etc.) is referenced in the rule engine but the Phase 1 code does not implement a zone config store — `CalibrationStore` handles calibration offsets only.
   - What's unclear: Where does the rule engine read zone config? From the database? From env vars? From a hardcoded default?
   - Recommendation: Add a `ZoneConfigStore` (similar to `CalibrationStore`) that reads from a `zone_configs` table in TimescaleDB. This table should be seeded at startup from env vars or a config file. This is Claude's discretion to design.

2. **MQTT ack topic subscriptions in the hub bridge**
   - What we know: The MQTT topic schema reserves `farm/{node_id}/ack/{command_id}`. The hub bridge currently subscribes to `farm/+/sensors/#` and `farm/+/heartbeat` only.
   - What's unclear: Should ack processing live in the bridge service or the API service? The bridge has the asyncpg pool; the API has the pending_acks registry.
   - Recommendation: Ack processing belongs in the API service (via a second aiomqtt client or via the bridge forwarding acks through the `/internal/notify` endpoint as a new delta type `actuator_ack`). Forwarding via the existing notify pipeline is simpler and avoids a second MQTT client.

3. **Feed/water level percentage conversion**
   - What we know: Sensors publish raw values (`feed_weight` in grams, `water_level` in some unit). The hub must convert to percentage for display.
   - What's unclear: The conversion formula depends on container size (not yet configured). Maximum load cell value = full hopper = 100%.
   - Recommendation: Add `FEED_MAX_WEIGHT_GRAMS` and `WATER_MAX_LEVEL` env vars. Division gives percentage. Alert threshold is `FEED_LOW_THRESHOLD_PCT` env var.

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `hub/api/main.py`, `hub/api/ws_manager.py`, `hub/bridge/main.py`, `hub/bridge/models.py`, `hub/dashboard/src/lib/ws.svelte.ts`, `hub/dashboard/src/lib/types.ts` — read directly; authoritative for integration points
- `docs/mqtt-topic-schema.md` — Phase 1 locked schema; Phase 2 actuator topics already reserved
- `.planning/phases/02-actuator-control-alerts-and-dashboard-v1/02-CONTEXT.md` — locked decisions
- `.planning/phases/02-actuator-control-alerts-and-dashboard-v1/02-UI-SPEC.md` — locked component specs
- `hub/dashboard/package.json` — installed package versions verified directly
- `npm view uplot version` — confirmed 1.6.32 as latest
- `pip3 index versions astral` — confirmed 3.2 as latest

### Secondary (MEDIUM confidence)
- [SvelteKit Service Workers — Official Docs](https://svelte.dev/docs/kit/service-workers) — verified via WebFetch; `$service-worker` module confirmed
- [astral 3.2 Package Docs](https://sffjunkie.github.io/astral/package.html) — `LocationInfo` + `astral.sun.sun()` API confirmed
- [TimescaleDB time_bucket() docs](https://docs.timescale.com/api/latest/hyperfunctions/time_bucket/) — aggregation query pattern confirmed

### Tertiary (LOW confidence — training data, flagged for validation)
- uPlot `onMount`/`onDestroy` pattern: consistent with uPlot README and Svelte REPL examples found in search; the specific Svelte 5 runes variant is based on training knowledge — validate against uPlot README during implementation
- asyncio `wait_for` + `Event` for command ack: standard Python asyncio pattern; confidence HIGH

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against live npm/pip registries and installed package.json
- Architecture patterns: HIGH — derived from existing code structure + locked decisions + official library docs
- Pitfalls: HIGH — Svelte 5 Map pitfall already present in codebase comment (ws.svelte.ts line 93 references "Pitfall 4 from Research"); others derived from known library behaviors
- uPlot Svelte 5 runes integration: MEDIUM — direct instantiation pattern well-documented; `$effect` for range changes follows Svelte 5 runes semantics

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days — stack is stable; uPlot and astral have slow release cadences)
