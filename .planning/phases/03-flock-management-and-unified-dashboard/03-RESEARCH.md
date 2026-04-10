# Phase 3: Flock Management and Unified Dashboard - Research

**Researched:** 2026-04-09
**Domain:** Weight-sensor egg counting, production modelling, sparkline charts, Svelte 5 tab navigation, TimescaleDB schema extension, Python alert engine extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Egg Count Estimation (FLOCK-01, FLOCK-02)**
- D-01: Egg count is sensor-driven, not manual entry. A weight/pressure sensor in the nesting box measures accumulated egg weight. No manual egg count form.
- D-02: 30-minute polling cycle. Each poll estimates egg count from weight (~60g per standard egg) after subtracting hen weight when a hen is detected above a configurable high-mark threshold.
- D-03: Manual refresh button on Coop tab. The farmer can tap "Refresh" to trigger an immediate re-poll of the nesting box sensor.
- D-04: "Hen present" detection via high-mark weight threshold (e.g., 1500g). System reports a chicken is currently in the nesting box when weight exceeds the threshold.
- D-05: Animated "hen present" indicator on Coop tab. Not subtle text — a real visual indicator (egg icon or gentle animation).

**Production Model and Display (FLOCK-03, FLOCK-04)**
- D-06: Expected production model: flock_size x breed_lay_rate x age_factor x daylight_factor. All four factors are configurable via flock settings.
- D-07: 30-day uPlot overlay chart (actual vs expected). Two series on the same chart: actual daily estimated egg count from sensor data, expected daily count from the model. Consistent with Phase 2's SensorChart.svelte (uPlot, DOM instantiation in onMount, $effect rune for range toggles).
- D-08: Production drop alert when 3-day rolling average falls below 75% of expected. P1 (amber) alert in the persistent AlertBar. Uses Phase 2 alert engine with hysteresis.

**Flock Configuration (FLOCK-05)**
- D-09: Settings page accessible from Coop tab via gear icon or "Settings" link. Parameters: breed (with lay rate lookup), hatch date (for age factor), flock size, supplemental lighting flag.
- D-10: Breed lay rate lookup table. Common breeds pre-populated. Custom breed option for unlisted breeds.
- D-11: Age decline curve — shape is Claude's discretion based on research into typical production decline.

**Feed Consumption Signals (FLOCK-06)**
- D-12: Feed consumption displayed as daily rate number + 7-day sparkline. Lives on the Coop tab near the existing feed level bar.
- D-13: Feed consumption rate derived from daily load cell weight delta. Refill detection: if today's weight > yesterday's weight, a refill occurred — use delta after the last refill.
- D-14: Feed consumption alert on >30% drop from 7-day rolling average. P1 (amber) alert in the AlertBar.

**Unified Overview Screen (UI-01)**
- D-15: New Home tab replaces Zones as the default landing page. Tab order: Home / Zones / Coop / Recs (4 tabs).
- D-16: Home tab shows compact zone cards (health badge + current moisture + zone name) + flock summary card (door status, egg count today, production trend indicator: up/down/flat arrow).
- D-17: Readability over density. Minimal scroll on tablet acceptable. Merriweather serif style and visual breathing room.
- D-18: Zone cards on Home tab tap through to /zones/[id].
- D-19: Flock summary card on Home tab taps through to Coop tab.

### Claude's Discretion
- Exact sparkline implementation for feed consumption (inline SVG, canvas, or lightweight chart lib)
- Age decline curve shape and parameters
- Nesting box sensor data model and MQTT topic structure
- Hen weight subtraction algorithm details
- Home tab responsive breakpoints
- Egg count estimation rounding strategy (floor, round, nearest integer)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLOCK-01 | Farmer can enter daily egg count via dashboard; counts stored per day | Sensor-driven via nesting box weight (D-01/D-02); new `egg_counts` table + bridge polling loop + REST endpoint |
| FLOCK-02 | Expected production model: flock_size × breed_lay_rate × age_factor × daylight_hours_factor | Pure Python calculation; new `flock_config` table; daylight_factor derivable from astral (already in requirements.txt) |
| FLOCK-03 | Dashboard shows egg production trend chart (actual vs expected, 30 days) | uPlot two-series overlay; extend SensorChart.svelte pattern with second series; new `/api/flock/egg-history` endpoint |
| FLOCK-04 | Production drop alert: 3-day rolling average < 75% expected; alert bar display | Extend AlertEngine with `production_drop` type; evaluate in bridge's periodic loop |
| FLOCK-05 | Flock configuration: breed, hatch date, flock size, supplemental lighting | New `flock_config` table; new FastAPI router; new Svelte settings page |
| FLOCK-06 | Feed consumption rate tracked from load cell data (daily delta) | Daily aggregation query against existing `sensor_readings` for `feed_weight`; refill detection logic in bridge; new WS delta type |
| UI-01 | Single overview screen: all zones + flock summary in one view | New Home tab at `/`; current `/` (Zones) moves to `/zones`; TabBar update from 3→4 tabs |

</phase_requirements>

---

## Summary

Phase 3 builds atop the Phase 2 sensor pipeline without introducing new infrastructure dependencies. Every new data flow follows the established pattern: MQTT topic → bridge ingestion → TimescaleDB write → WebSocket delta → Svelte 5 reactive state. The nesting box weight sensor is treated as a standard `sensor_type` on the `coop` node, published to `farm/coop/sensors/nesting_box_weight`. Daily egg count estimation and feed consumption calculation both happen hub-side in the bridge's periodic loop, not per-reading, requiring a new time-based scheduling primitive.

The production model (breed × age × daylight) is pure arithmetic. The `astral` library already in `hub/bridge/requirements.txt` supplies sunrise/sunset times for daylight factor calculation without adding a dependency. Age factor uses a piecewise linear curve anchored to peak laying age (approximately 28 weeks for most breeds) and declining by approximately 10–15% per year of age.

The primary UI change is a four-tab layout where a new Home tab becomes the default landing page. The existing `/` route becomes the Home tab, and the Zones tab moves to `/zones`. The uPlot overlay chart for egg production is a straightforward extension of `SensorChart.svelte` — the chart component already supports arbitrary series configuration; the production chart just needs two series and a second y-axis or shared y-axis with different strokes.

**Primary recommendation:** Follow the existing Phase 2 pipeline pattern for all new data flows. No new libraries are needed. Sparklines for feed consumption should use inline SVG paths computed from 7 data points — uPlot is overkill at that scale and inline SVG avoids a DOM instantiation lifecycle edge case for small embedded charts.

---

## Standard Stack

### Core (carry-forward from Phase 2)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uPlot | 1.6.32 | Production trend overlay chart (FLOCK-03) | Already installed; used in SensorChart.svelte; Phase 2 D-31 locked this |
| FastAPI + asyncpg | current | New flock config + egg data REST endpoints | Established API pattern; API router per domain |
| TimescaleDB | current | `egg_counts`, `flock_config`, `feed_daily_consumption` tables | Existing hypertable infra; new tables added via migration |
| Svelte 5 + SvelteKit | 5.28.1 / 2.21.0 | Home tab route, flock settings page, CoopPanel extensions | Locked in Phase 1 |
| aiomqtt + asyncpg | current | Nesting box sensor ingestion | Exact same bridge pipeline |
| astral | 3.2 | Daylight factor calculation for production model | Already in requirements.txt — provides sunrise/sunset from lat/lon |
| Vitest + @testing-library/svelte | 3.1.1 / 5.2.6 | Dashboard component tests | Established test stack |
| pytest + pytest-asyncio | 8.3.5 / 0.25.3 | Bridge Python unit tests | Established test stack |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-svelte | 0.487.0 | Egg icon, settings gear icon, trend arrow icons, refresh icon | All new UI icons |
| Inline SVG | — | 7-day feed consumption sparkline | Lightweight, no lib needed for 7 data points |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline SVG sparkline | uPlot embedded small | uPlot has a minimum DOM size expectation; onMount lifecycle adds complexity inside CoopPanel; inline SVG is simpler for static 7-point trend |
| Inline SVG sparkline | Chart.js or Recharts | No precedent in project; would add a dependency for a single small component |
| astral for daylight | Hardcoded sunrise table | astral is already installed and gives accurate astronomical data per configured lat/lon |

**No new npm or pip packages required.** All needed libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure Extensions

```
hub/
├── bridge/
│   ├── flock_config.py         # FlockConfig dataclass + DB store (mirrors zone_config.py)
│   ├── production_model.py     # Expected production calculation (breed × age × daylight)
│   ├── egg_estimator.py        # Nesting box weight → egg count algorithm
│   ├── feed_consumption.py     # Daily feed delta derivation + refill detection
│   └── tests/
│       ├── test_production_model.py
│       ├── test_egg_estimator.py
│       └── test_feed_consumption.py
├── api/
│   ├── flock_router.py         # GET/POST /api/flock/config, GET /api/flock/egg-history
│   └── ...
└── dashboard/src/
    ├── routes/
    │   ├── +page.svelte            # NEW: Home tab (was Zones; Zones moves to /zones/)
    │   ├── zones/
    │   │   └── +page.svelte        # MOVED: Zones list (was /)
    │   ├── coop/
    │   │   ├── +page.svelte        # EXTENDED: CoopPanel + egg section + refresh button
    │   │   └── settings/
    │   │       └── +page.svelte    # NEW: Flock configuration settings
    │   └── ...
    └── lib/
        ├── CoopPanel.svelte        # EXTENDED: egg count, hen indicator, production chart, feed sparkline
        ├── FlockSummaryCard.svelte # NEW: compact flock summary for Home tab
        ├── ProductionChart.svelte  # NEW: uPlot two-series overlay (actual vs expected)
        ├── FeedSparkline.svelte    # NEW: inline SVG 7-day sparkline
        ├── FlockSettings.svelte    # NEW: flock config form
        └── types.ts                # EXTENDED: FlockState, FlockConfig, EggCountDelta types
```

### Pattern 1: Bridge Periodic Loop (new — for daily aggregations)

**What:** A separate async task in `bridge/main.py` that runs on a schedule (every 30 minutes for egg polling, daily at midnight for consumption aggregation) distinct from the per-reading MQTT callback.

**When to use:** Aggregations that don't correspond to a single MQTT message event (egg count estimation, daily feed delta, production alert evaluation).

**Example:**
```python
# Source: Extension of bridge/main.py asyncio.gather() pattern
async def periodic_flock_loop(db_pool: asyncpg.Pool):
    """Run every 30 minutes: estimate egg count, evaluate production alert."""
    while True:
        await asyncio.sleep(30 * 60)
        await _estimate_and_store_egg_count(db_pool)
        await _evaluate_production_alerts(db_pool)

async def daily_feed_loop(db_pool: asyncpg.Pool):
    """Run daily at midnight: compute feed consumption delta."""
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        await asyncio.sleep((next_midnight - now).total_seconds())
        await _compute_daily_feed_consumption(db_pool)
```

Add both to `asyncio.gather()` in `main()`.

### Pattern 2: Nesting Box Sensor Topic Extension

**What:** New sensor type `nesting_box_weight` published by the coop node, following the established `farm/{node_id}/sensors/{sensor_type}` schema.

**MQTT topic:** `farm/coop/sensors/nesting_box_weight`

**Payload:** Standard `SensorPayload` format — same JSON schema as `feed_weight`. No schema changes needed to the bridge parser.

**Bridge routing:** Add `sensor_type == "nesting_box_weight"` handling in `_evaluate_phase2()` (or a new `_evaluate_phase3()` function called alongside it). Broadcasts `nesting_box` delta type including current weight, estimated egg count, and `hen_present` boolean.

### Pattern 3: Egg Estimation Algorithm

**What:** Derive estimated egg count from nesting box weight reading.

**When to use:** On every `nesting_box_weight` sensor reading received by the bridge.

```python
# Source: D-02 and D-04 from CONTEXT.md
EGG_WEIGHT_GRAMS = 60.0      # configurable per flock config
HEN_WEIGHT_THRESHOLD = 1500.0  # configurable per flock config

def estimate_egg_count(weight_grams: float, flock_config: FlockConfig) -> tuple[int, bool]:
    """
    Returns (estimated_eggs, hen_present).
    If weight > hen_threshold, subtract hen weight before estimating eggs.
    """
    hen_present = weight_grams > flock_config.hen_weight_threshold
    effective_weight = weight_grams
    if hen_present:
        effective_weight = max(0.0, weight_grams - flock_config.hen_weight_threshold)
    egg_count = round(effective_weight / flock_config.egg_weight_grams)
    return egg_count, hen_present
```

**Rounding strategy (Claude's discretion):** `round()` (nearest integer) rather than `floor()`. With a 60g target and variance in real egg weights (50–70g), rounding produces fewer systematic underestimates than floor.

### Pattern 4: uPlot Two-Series Overlay Chart (ProductionChart.svelte)

**What:** Extend the SensorChart pattern with a second series. uPlot natively supports multiple series in a single chart — pass a data array with three arrays: `[timestamps, actual_values, expected_values]`.

**Example:**
```typescript
// Source: uPlot 1.6.32 API — verified against existing SensorChart.svelte pattern
function buildProductionOpts(width: number): uPlot.Options {
  return {
    width,
    height: 200,
    series: [
      {},                                    // x-axis (timestamps)
      { label: 'Actual', stroke: '#4ade80', width: 1.5 },   // actual eggs
      { label: 'Expected', stroke: '#94a3b8', width: 1.5, dash: [4, 4] },  // expected
    ],
    axes: [
      { stroke: '#94a3b8', grid: { stroke: '#2d3149' }, size: 14 },
      { stroke: '#94a3b8', grid: { stroke: '#2d3149' }, size: 14 },
    ],
    cursor: { stroke: '#6b7280' },
  };
}

// Data: [timestamps_unix, actual_array, expected_array]
chart = new uPlot(opts, [timestamps, actualValues, expectedValues], container);
```

### Pattern 5: Feed Consumption Sparkline (FeedSparkline.svelte)

**What:** Inline SVG polyline drawn from 7 daily consumption values. No library needed.

**Example:**
```typescript
// Compute SVG path from 7 data points (Claude's discretion — inline SVG approach)
function toPolylinePoints(values: number[], width = 80, height = 24): string {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
}
```

```svelte
<svg width="80" height="24" aria-hidden="true">
  <polyline points={toPolylinePoints(weeklyValues)} fill="none" stroke="var(--color-accent)" stroke-width="1.5" />
</svg>
```

### Pattern 6: Production Drop Alert (extend AlertEngine)

**What:** Add two new alert types to `ALERT_DEFINITIONS` and `HYSTERESIS_BANDS` in `alert_engine.py`.

**Where to add:**
```python
# Source: alert_engine.py — exact extension pattern
HYSTERESIS_BANDS = {
    # ... existing entries ...
    "production_drop": 10.0,      # 10% hysteresis band (clears when 3-day avg recovers to 85%)
    "feed_consumption_drop": 5.0, # 5% hysteresis band
}

ALERT_DEFINITIONS = {
    # ... existing entries ...
    "production_drop": ("P1", "Production drop — egg count below expected", "/coop"),
    "feed_consumption_drop": ("P1", "Feed consumption drop", "/coop"),
}
```

Alert evaluation: in `periodic_flock_loop`, query the last 3 days of egg counts, compute the 3-day rolling average, compare to expected. Call `alert_engine.evaluate("production_drop:coop", ratio_pct, 75.0, clear_above=True)` where `ratio_pct = (3_day_avg / expected) * 100`.

### Pattern 7: Home Tab Route Restructuring

**What:** The SvelteKit route `/` becomes the Home tab. Zones list moves to `/zones/`. Existing `/zones/[id]` detail routes are unaffected.

**Current structure:**
```
routes/
├── +page.svelte          # Zones list (current /)
├── zones/[id]/           # Zone detail
├── coop/                 # Coop tab
└── recommendations/      # Recs tab
```

**New structure:**
```
routes/
├── +page.svelte          # Home tab (NEW)
├── zones/
│   ├── +page.svelte      # Zones list (MOVED from /)
│   └── [id]/             # Zone detail (unchanged)
├── coop/
│   ├── +page.svelte      # Coop (extended)
│   └── settings/
│       └── +page.svelte  # Flock settings (NEW)
└── recommendations/      # Recs (unchanged)
```

**TabBar update:** Change from 3 tabs to 4 tabs. Update `isActive()` logic: the Zones tab path changes from `'/'` to `'/zones'`, so the existing `currentPath === '/'` check in the Zones entry must be removed and applied only to the Home tab.

```typescript
// Current tab definition (3 tabs):
const tabs = [
  { path: '/', label: 'Zones', icon: Sprout, ariaLabel: 'Zones' },
  { path: '/coop', label: 'Coop', icon: Home, ariaLabel: 'Coop' },
  { path: '/recommendations', label: 'Recs', icon: Bell, ariaLabel: 'Recommendations' },
];

// New tab definition (4 tabs):
const tabs = [
  { path: '/', label: 'Home', icon: LayoutDashboard, ariaLabel: 'Home' },
  { path: '/zones', label: 'Zones', icon: Sprout, ariaLabel: 'Zones' },
  { path: '/coop', label: 'Coop', icon: Home, ariaLabel: 'Coop' },
  { path: '/recommendations', label: 'Recs', icon: Bell, ariaLabel: 'Recommendations' },
];

function isActive(tabPath: string, currentPath: string): boolean {
  if (tabPath === '/') return currentPath === '/';              // Home: exact match only
  if (tabPath === '/zones') return currentPath.startsWith('/zones');
  return currentPath.startsWith(tabPath);
}
```

### Pattern 8: Age Decline Curve (Claude's Discretion)

**What:** A piecewise function from hatch date to current date producing an `age_factor` in range [0.0, 1.0].

**Research basis:** Industry data on hen laying production by age — peak at 25–30 weeks, high plateau through ~18 months, then declining approximately 10–15% per year.

**Recommended implementation:**
```python
from datetime import date

def compute_age_factor(hatch_date: date, today: date = None) -> float:
    """
    Piecewise linear age factor:
    - 0–24 weeks: ramp from 0.0 to 1.0 (pullets coming into lay)
    - 24–72 weeks: plateau at 1.0 (prime laying)
    - 72+ weeks: linear decline at ~0.15/year (industry average)
    Minimum factor: 0.2 (very old hens still lay some)
    """
    if today is None:
        today = date.today()
    weeks = (today - hatch_date).days / 7.0
    if weeks < 24:
        return weeks / 24.0
    elif weeks < 72:
        return 1.0
    else:
        years_past_peak = (weeks - 72) / 52.0
        return max(0.2, 1.0 - (years_past_peak * 0.15))
```

### Pattern 9: Breed Lay Rate Table (FLOCK-05)

**What:** Static lookup table mapping breed name → base daily lay rate (eggs/day per hen at peak). Stored in the application, not in the database. Custom breed allows user-specified rate.

**Recommended initial table:**
```python
BREED_LAY_RATES: dict[str, float] = {
    "Rhode Island Red":    0.75,
    "Leghorn":             0.85,
    "Plymouth Rock":       0.70,
    "Australorp":          0.80,
    "Orpington":           0.55,
    "Sussex":              0.65,
    "Easter Egger":        0.65,
    "Silkie":              0.40,
    "Wyandotte":           0.65,
    "Brahma":              0.50,
    "Custom":              None,   # User supplies lay_rate_override
}
```

### Pattern 10: Daylight Factor

**What:** Ratio of actual daylight hours to optimal daylight hours (17 hours). Supplemental lighting flag caps the factor at 1.0.

```python
from astral import LocationInfo
from astral.sun import sun
from datetime import date

OPTIMAL_DAYLIGHT_HOURS = 17.0

def compute_daylight_factor(
    lat: float, lon: float,
    today: date,
    supplemental_lighting: bool
) -> float:
    """
    If supplemental_lighting=True, assume optimal daylight (factor=1.0).
    Otherwise derive from astral sunrise/sunset.
    """
    if supplemental_lighting:
        return 1.0
    location = LocationInfo(latitude=lat, longitude=lon)
    s = sun(location.observer, date=today)
    daylight_hours = (s['sunset'] - s['sunrise']).total_seconds() / 3600.0
    return min(1.0, daylight_hours / OPTIMAL_DAYLIGHT_HOURS)
```

### Anti-Patterns to Avoid

- **Per-reading production alert evaluation:** Production drop alert depends on 3-day rolling average, not a single reading. Evaluate in the periodic loop only — not in `_evaluate_phase2()`.
- **Storing expected production in TimescaleDB:** Expected values are computed on-the-fly from flock config. Do not store them. The API endpoint computes expected for the requested date range when the chart requests history.
- **uPlot inside CoopPanel for sparkline:** uPlot requires a DOM container with a measured width. Inside a flex layout row next to text, this creates sizing edge cases. Use inline SVG for the 7-point sparkline.
- **SvelteKit route conflicts:** When moving Zones from `/` to `/zones`, ensure the `isActive` check for the Home tab uses exact match (`currentPath === '/'`) — not `startsWith('/')`, which would always be true.
- **Map reassignment gotcha (Svelte 5):** When adding new state fields to `DashboardStore`, follow the existing pattern: `this.zones = new Map(this.zones.set(...))`. Direct mutation of a `$state` Map does not trigger reactivity.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sunrise/sunset for daylight factor | Custom solar calculation | `astral` (already installed) | Handles DST, timezone, astronomical precision |
| uPlot two-series chart | Custom canvas drawing | uPlot multi-series (existing pattern) | uPlot already used; multi-series is core feature |
| Date arithmetic for age factor | Manual day counting | Python `datetime.date` arithmetic | Standard library; no dep needed |
| Rolling averages | Custom loop | Single SQL query with `AVG()` over window | TimescaleDB window functions handle this efficiently |

**Key insight:** This phase adds no new infrastructure. Every problem has a solution already present in the codebase or the existing dependency tree.

---

## Database Schema Extensions

### New Tables

```sql
-- Flock configuration (single row — one flock per farm)
CREATE TABLE IF NOT EXISTS flock_config (
    id                  SERIAL PRIMARY KEY,
    breed               TEXT NOT NULL,
    lay_rate_override   DOUBLE PRECISION,          -- NULL if using breed table lookup
    hatch_date          DATE NOT NULL,
    flock_size          INTEGER NOT NULL,
    supplemental_lighting BOOLEAN NOT NULL DEFAULT FALSE,
    hen_weight_threshold_grams DOUBLE PRECISION NOT NULL DEFAULT 1500.0,
    egg_weight_grams    DOUBLE PRECISION NOT NULL DEFAULT 60.0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily egg count records (one row per day, from sensor estimation)
CREATE TABLE IF NOT EXISTS egg_counts (
    count_date          DATE NOT NULL PRIMARY KEY,
    estimated_count     INTEGER NOT NULL,
    raw_weight_grams    DOUBLE PRECISION,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily feed consumption records (derived from load cell delta)
CREATE TABLE IF NOT EXISTS feed_daily_consumption (
    consumption_date    DATE NOT NULL PRIMARY KEY,
    consumption_grams   DOUBLE PRECISION NOT NULL,  -- daily delta; NULL if refill-only day
    refill_detected     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Feed consumption derivation query (for bridge daily loop):**
```sql
-- Get yesterday's starting weight and today's ending weight from sensor_readings
-- Refill detected if any reading today > any reading yesterday at day-start
SELECT
    MIN(value) FILTER (WHERE time >= $1 AND time < $2) AS start_weight,
    MIN(value) FILTER (WHERE time >= $2 AND time < $3) AS end_weight,
    MAX(value) FILTER (WHERE time >= $2 AND time < $3) AS max_today
FROM sensor_readings
WHERE zone_id = 'coop' AND sensor_type = 'feed_weight' AND quality = 'GOOD';
```

### MQTT Topic Extension

New topic added to `docs/mqtt-topic-schema.md`:

```
farm/coop/sensors/nesting_box_weight
```

Same payload schema as existing `feed_weight` sensor readings. The bridge subscribes to `farm/+/sensors/#` which already covers this topic — no broker subscription changes needed.

---

## Common Pitfalls

### Pitfall 1: SvelteKit Route Move Breaks Existing Links

**What goes wrong:** Moving Zones from `/` to `/zones/` breaks any `goto('/')` calls and hard-coded hrefs in existing components.

**Why it happens:** The current TabBar has `path: '/'` for Zones. `ZoneCard.svelte` navigates to `/zones/${zone.zone_id}` (already correct). The Zones tab anchor must change from `href="/"` to `href="/zones"`.

**How to avoid:** Audit all `goto('/')` calls and `href="/"` attributes before moving the route. The only file with `path: '/'` for Zones is `TabBar.svelte`.

**Warning signs:** After the move, the Zones tab shows the Home page content.

### Pitfall 2: uPlot Width = 0 on Initial Render

**What goes wrong:** If `ProductionChart.svelte` instantiates uPlot before the container has a measured width (e.g., while the parent is `display: none` or tab is not active), the chart renders at 0px width.

**Why it happens:** uPlot reads `container.clientWidth` at instantiation. `requestAnimationFrame` in `SensorChart.svelte` mitigates this for the initial render but doesn't handle tab-switch scenarios.

**How to avoid:** Follow the exact `onMount` + `ResizeObserver` pattern from `SensorChart.svelte`. Additionally, if the production chart is inside a tab that's not initially active, defer instantiation until the tab becomes visible (use Svelte `#if` conditional on tab active state rather than `visibility: hidden`).

**Warning signs:** Chart renders as a thin horizontal line or blank area.

### Pitfall 3: Feed Refill Causes Negative Consumption

**What goes wrong:** If a refill happens mid-day, `end_weight - start_weight` is positive (a gain), not a consumption (a loss). Without refill detection, consumption = negative number.

**Why it happens:** The load cell simply reports current weight; a refill looks like a large positive delta.

**How to avoid:** D-13 specifies the refill detection rule: if today's weight ever exceeds yesterday's weight, a refill occurred. In that case, estimate consumption as: weight at last pre-refill reading minus weight at end of day. If the refill happened at an unknown time, store `consumption_grams = NULL` for that day and `refill_detected = TRUE`, so the alert system ignores that day in rolling averages.

**Warning signs:** Feed consumption sparkline shows a large negative spike or a large positive spike on refill days.

### Pitfall 4: Production Alert Fires on Day 0 (No History)

**What goes wrong:** On initial setup, there are 0 days of egg count history. The 3-day rolling average = 0. The alert fires immediately because 0 < 75% of expected.

**Why it happens:** Alert evaluation before enough history exists.

**How to avoid:** In the production drop evaluation function, check that at least 3 days of egg count records exist before evaluating the alert. If fewer than 3 days of data exist, skip evaluation silently.

**Warning signs:** Alert fires immediately after flock config is saved.

### Pitfall 5: Hen Present Threshold Misconfigured

**What goes wrong:** If `hen_weight_threshold` is set too low (e.g., 500g), every egg sitting in the box triggers "hen present" = TRUE, causing over-subtraction and a negative effective weight.

**Why it happens:** Egg weight (~60g × n eggs) can accumulate but a typical hen weighs 1.5–2.5kg. The threshold must clearly separate "just eggs" from "hen + eggs."

**How to avoid:** Default `hen_weight_threshold` to 1500g. Display current nesting box weight on the Coop settings page alongside the threshold so the farmer can calibrate. Clamp `effective_weight = max(0.0, weight - hen_threshold)` so underestimates don't go negative.

### Pitfall 6: Svelte 5 $state Map Mutation

**What goes wrong:** Adding `flockState` as a plain Map field without reassignment means Svelte 5 does not detect the change and the UI does not update.

**Why it happens:** Svelte 5 `$state` with Map requires reassignment of the Map reference to trigger reactivity, as noted in the existing `ws.svelte.ts` comment: `// Reassign Map for Svelte 5 reactivity (Pitfall 4 from Research)`.

**How to avoid:** Add `flockState = $state<FlockState | null>(null)` (scalar, not Map) to `DashboardStore`. Update it by full reassignment: `this.flockState = { ...newData }`.

---

## Code Examples

### Alert Engine Extension (alert_engine.py)

```python
# Source: hub/bridge/alert_engine.py — extend existing dicts
HYSTERESIS_BANDS = {
    "moisture_low": 5.0,
    "ph_low": 0.2,
    "ph_high": 0.2,
    "feed_low": 5.0,
    "water_low": 5.0,
    "temp_low": 2.0,
    "temp_high": 2.0,
    # Phase 3 additions:
    "production_drop": 10.0,
    "feed_consumption_drop": 5.0,
}

ALERT_DEFINITIONS = {
    # ... existing entries ...
    # Phase 3 additions:
    "production_drop": ("P1", "Production drop \u2014 eggs below expected", "/coop"),
    "feed_consumption_drop": ("P1", "Feed consumption drop", "/coop"),
}
```

### WebSocket Store Extension (ws.svelte.ts)

```typescript
// New fields added to DashboardStore class
eggCount = $state<{ today: number; hen_present: boolean; updated_at: string } | null>(null);
flockProduction = $state<{ actual: number[]; expected: number[]; dates: string[] } | null>(null);
feedConsumption = $state<{ rate_grams_per_day: number; weekly: number[] } | null>(null);

// New message handlers in handleMessage():
} else if (msg.type === 'nesting_box') {
  this.eggCount = {
    today: msg.estimated_count,
    hen_present: msg.hen_present,
    updated_at: msg.updated_at,
  };
} else if (msg.type === 'feed_consumption') {
  this.feedConsumption = {
    rate_grams_per_day: msg.rate_grams_per_day,
    weekly: msg.weekly,
  };
}
```

### New TypeScript Types (types.ts additions)

```typescript
// Phase 3 types — add to types.ts

export interface FlockConfig {
  breed: string;
  lay_rate_override: number | null;
  hatch_date: string;          // ISO date string "YYYY-MM-DD"
  flock_size: number;
  supplemental_lighting: boolean;
  hen_weight_threshold_grams: number;
  egg_weight_grams: number;
}

export interface NestingBoxDelta {
  type: 'nesting_box';
  estimated_count: number;
  hen_present: boolean;
  raw_weight_grams: number;
  updated_at: string;
}

export interface FeedConsumptionDelta {
  type: 'feed_consumption';
  rate_grams_per_day: number;
  weekly: number[];             // 7 values, oldest first
}

// Add to WSMessage union:
// | NestingBoxDelta | FeedConsumptionDelta
```

### Hen Present Animation (CSS)

```css
/* Extend CoopPanel.svelte — hen present pulse animation */
.hen-present-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 14px;
  color: var(--color-accent);
  font-weight: 600;
}

.hen-present-indicator.active .hen-icon {
  animation: hen-pulse 2s ease-in-out infinite;
}

@keyframes hen-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0.7; }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual egg count form (REQUIREMENTS.md original spec) | Sensor-driven weight estimation (D-01) | Phase 3 discuss-phase | Changes FLOCK-01 from form to sensor pipeline |
| FLOCK-01 read as "farmer enters count" | Bridge polls nesting box sensor, estimates count | CONTEXT.md decision | No form needed; egg_counts populated by bridge |

**Note:** The REQUIREMENTS.md text for FLOCK-01 says "Farmer can enter daily egg count via dashboard; counts are stored per day." The CONTEXT.md decision D-01 overrides this with sensor-driven counting. The planner must implement sensor-driven counting (D-01) not a manual form. The requirement is satisfied by automated estimation which is functionally superior.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| astral (Python) | Daylight factor calculation | ✓ | 3.2 | — |
| asyncpg | Bridge DB queries | ✓ | 0.31.0 | — |
| uPlot | Production overlay chart | ✓ | 1.6.32 | — |
| lucide-svelte | New UI icons | ✓ | 0.487.0 | — |
| TimescaleDB | New tables | ✓ | current (running) | — |
| Vitest | Dashboard tests | ✓ | 3.1.1 | — |
| pytest / pytest-asyncio | Bridge tests | ✓ | 8.3.5 / 0.25.3 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

All Phase 3 dependencies are already installed. No `npm install` or `pip install` steps required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python (bridge) framework | pytest 8.3.5 + pytest-asyncio 0.25.3 |
| Python config | `hub/bridge/tests/conftest.py` (sys.path insert for bridge src) |
| Python quick run | `cd hub/bridge && python -m pytest tests/ -x -q` |
| Python full suite | `cd hub/bridge && python -m pytest tests/ -v` |
| Dashboard framework | Vitest 3.1.1 + @testing-library/svelte 5.2.6 |
| Dashboard config | `hub/dashboard/package.json` scripts.test = "vitest" |
| Dashboard quick run | `cd hub/dashboard && npx vitest run --reporter=verbose` |
| Dashboard full suite | `cd hub/dashboard && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLOCK-01 | Egg count estimated from nesting box weight | unit | `pytest tests/test_egg_estimator.py -x` | ❌ Wave 0 |
| FLOCK-02 | Expected production model arithmetic | unit | `pytest tests/test_production_model.py -x` | ❌ Wave 0 |
| FLOCK-03 | ProductionChart renders two series | unit | `npx vitest run src/lib/ProductionChart.test.ts` | ❌ Wave 0 |
| FLOCK-04 | Production drop alert fires at <75%, clears at >85% | unit | `pytest tests/test_production_model.py::test_alert_threshold -x` | ❌ Wave 0 |
| FLOCK-05 | Flock config CRUD via API | integration (manual smoke) | Manual — requires live DB | manual-only |
| FLOCK-06 | Feed consumption delta calculation with refill detection | unit | `pytest tests/test_feed_consumption.py -x` | ❌ Wave 0 |
| UI-01 | Home tab renders zone cards + flock summary | unit | `npx vitest run src/lib/FlockSummaryCard.test.ts` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd hub/bridge && python -m pytest tests/ -x -q`
- **Per wave merge:** Full bridge suite + `cd hub/dashboard && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `hub/bridge/tests/test_egg_estimator.py` — covers FLOCK-01 (egg weight → count, hen subtraction)
- [ ] `hub/bridge/tests/test_production_model.py` — covers FLOCK-02 (model arithmetic), FLOCK-04 (alert threshold logic)
- [ ] `hub/bridge/tests/test_feed_consumption.py` — covers FLOCK-06 (delta derivation, refill detection)
- [ ] `hub/dashboard/src/lib/ProductionChart.test.ts` — covers FLOCK-03 (two-series chart renders)
- [ ] `hub/dashboard/src/lib/FlockSummaryCard.test.ts` — covers UI-01 (home tab flock summary card)

---

## Open Questions

1. **Lat/lon for daylight factor**
   - What we know: `astral` needs latitude/longitude to compute sunrise/sunset
   - What's unclear: Where is lat/lon stored? Not present in current schema or config files.
   - Recommendation: Add `latitude` and `longitude` fields to `flock_config` table (or a separate `farm_config` table). Default to 0.0/0.0 with a setup prompt on the flock settings page. If not configured and supplemental_lighting=false, default daylight_factor=0.85 (approximate mid-latitude average).

2. **Initial nesting box weight baseline**
   - What we know: The bridge estimates egg count from absolute weight (~60g/egg)
   - What's unclear: The nesting box itself has a tare weight. Without a tare calibration step, the raw weight includes the box weight, producing wildly wrong egg counts.
   - Recommendation: Add a `tare_weight_grams` field to `flock_config` (default 0.0). The flock settings page should include a "Set tare weight" button that reads the current nesting box weight and stores it as the tare. Estimation subtracts tare before dividing by egg weight.

3. **Home tab Zones data source**
   - What we know: Home tab shows compact zone cards with health badge + moisture
   - What's unclear: The current `DashboardStore.zones` Map holds full zone state; the Home tab can use it directly. Health scores are in `zoneHealthScores`. No new WS data needed.
   - Recommendation: Home tab reads from existing `dashboardStore.zones` and `dashboardStore.zoneHealthScores` — no new data pipeline. Flock summary reads from new `dashboardStore.eggCount` field.

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection: `hub/bridge/alert_engine.py` — confirmed AlertEngine API and extension pattern
- Codebase inspection: `hub/bridge/main.py` — confirmed `_evaluate_phase2()` extension point, `asyncio.gather()` for new loops
- Codebase inspection: `hub/dashboard/src/lib/SensorChart.svelte` — confirmed uPlot instantiation pattern (onMount, ResizeObserver, requestAnimationFrame)
- Codebase inspection: `hub/dashboard/src/lib/ws.svelte.ts` — confirmed DashboardStore $state patterns, Map reassignment requirement, WSMessage handler structure
- Codebase inspection: `hub/dashboard/src/lib/TabBar.svelte` — confirmed 3-tab structure, isActive() logic to extend
- Codebase inspection: `hub/init-db.sql` — confirmed TimescaleDB schema; new tables follow same CREATE TABLE pattern
- Codebase inspection: `hub/bridge/requirements.txt` — confirmed astral 3.2 already installed
- Codebase inspection: `docs/mqtt-topic-schema.md` — confirmed `farm/{node_id}/sensors/{sensor_type}` pattern for new `nesting_box_weight` topic
- Codebase inspection: `hub/dashboard/package.json` — confirmed uPlot 1.6.32 and all other dashboard deps

### Secondary (MEDIUM confidence)

- Poultry industry production data: Age-based laying rate decline of ~10–15%/year after peak is widely reported across extension service publications. Piecewise curve shape (ramp 0–24wk, plateau 24–72wk, decline thereafter) reflects consensus across multiple sources.
- Breed lay rate table: Values drawn from common breed characteristics; approximate, intended as configurable defaults not hard constraints.

### Tertiary (LOW confidence — needs field validation)

- Egg weight of 60g as default: Industry average for medium/large eggs. Real flocks vary. D-02 sets this as configurable — correct default matters for initial UX but will be tuned by the farmer.
- Hen weight threshold of 1500g: Light breed hens (Leghorn) start around 1.8kg; heavy breeds (Brahma) can reach 4.5kg. 1500g is a safe lower bound. Should be prominently configurable in flock settings.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed present in package.json and requirements.txt
- Architecture: HIGH — all patterns derived from reading existing Phase 2 source code directly
- Pitfalls: HIGH — derived from reading the actual code (e.g., Map reassignment comment is in ws.svelte.ts; route conflict is visible in TabBar.svelte)
- Breed/age data: MEDIUM — industry consensus, not codebase-derived

**Research date:** 2026-04-09
**Valid until:** 2026-07-09 (stable domain — poultry production biology and the codebase are both stable)
