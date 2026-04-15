# Phase 5: Operational Hardening — Research

**Researched:** 2026-04-15
**Domain:** pH calibration workflow, ntfy push notifications, TimescaleDB data retention policies, sensor calibration management UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**pH Calibration Workflow (ZONE-07)**
- D-01: pH calibration reminder appears in the alert bar as P1 (amber). Same pattern as low moisture, stuck door, etc. "pH calibration overdue — Zone A" uses the existing AlertEngine hysteresis pattern. Alert fires when `last_calibration_date` is older than 2 weeks, clears when the farmer records a new calibration.
- D-02: Calibration recording UX is Claude's discretion. Choose the right approach based on the existing zone detail page structure — either a button on /zones/[id] next to the pH row, or a dedicated calibration management page, whichever integrates more naturally.
- D-03: New column `last_calibration_date` on `calibration_offsets` table. Nullable TIMESTAMPTZ. When the farmer records a calibration, this is set to NOW(). The bridge checks this field during alert evaluation to determine if a reminder is needed.

**Sensor Calibration Management (05-02)**
- D-04: Calibration is hub-only — no edge push needed. The existing CalibrationStore applies offsets at ingestion on the hub side. Edge nodes send raw values. When the farmer updates dry/wet values or temp coefficient, the hub's in-memory cache is refreshed. No MQTT config push to edge nodes required.
- D-05: Calibration management UI shows per-sensor offsets, dry/wet values, temp coefficient, and last calibration date. The farmer can view and edit these values. Changes take effect on the next sensor reading (CalibrationStore reload).

**ntfy Push Notifications (NOTF-03)**
- D-06: External ntfy server — farmer provides URL. No ntfy Docker container in the compose stack. The bridge sends HTTP POST to the farmer's ntfy server (could be ntfy.sh public or their own instance). Configuration is a URL + topic.
- D-07: Env vars set defaults, dashboard settings page overrides at runtime. `NTFY_URL` and `NTFY_TOPIC` in hub.env provide the initial configuration. A settings page (/settings/notifications or similar) lets the farmer update URL, topic, and toggle on/off without restarting. Include a "Send Test" button.
- D-08: ntfy fires for the same events that trigger in-app alerts. Same event list as AlertEngine output: low moisture, pH out of range, low feed/water, production drop, stuck coop door, node offline, pH calibration overdue. In-app alerts remain the baseline; ntfy is purely additive.
- D-09: ntfy is optional — system works fully without it. If NTFY_URL is empty/unset, ntfy is silently disabled. No errors, no warnings.

**Data Retention Policies (05-03)**
- D-10: TimescaleDB built-in retention policies for automated purge. Use `add_retention_policy()` on the `sensor_readings` hypertable with a 90-day interval.
- D-11: Hourly rollup via TimescaleDB continuous aggregate. Create a continuous aggregate `sensor_readings_hourly` that computes avg, min, max per (zone_id, sensor_type) per hour. Retained for 2 years (730 days).
- D-12: Dedicated storage section on a settings page. Shows per-table sizes (raw readings, rollups, egg counts, etc.), retention policy status, last purge date, and a manual "Purge Now" button.

### Claude's Discretion

- pH calibration recording UX placement (zone detail button vs dedicated page)
- Calibration management page layout and route path
- ntfy HTTP POST format (ntfy supports simple POST with title/body/priority headers)
- ntfy settings page route (/settings/notifications or part of existing /settings/ai)
- Continuous aggregate refresh policy interval
- Storage section page layout and route
- Whether to include a "Purge Now" confirmation dialog

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ZONE-07 | pH calibration workflow: tracks calibration date per sensor, shows due-date reminder when calibration is overdue (2-week cadence), records calibration offset on hub | D-01 through D-05; alert_engine.py extension pattern; CalibrationStore extension; DB migration; Svelte settings page pattern |
| NOTF-03 | Self-hosted push notifications via ntfy (optional V1 stretch goal — in-app alerts are the baseline) | D-06 through D-09; ntfy HTTP POST API; aiohttp bridge integration; AISettings JSON sidecar pattern for NtfySettings; inference_settings_router.py proxy pattern |
</phase_requirements>

---

## Summary

Phase 5 has four plans and two primary requirements. The work is largely additive to existing systems — no rewrites, only targeted extensions of proven patterns already established in Phases 2–4.

**ZONE-07 (pH calibration)** extends `calibration_offsets` with a nullable `last_calibration_date` column, extends `CalibrationStore` with `is_overdue()` and `record_calibration()` methods, adds a `ph_calibration_overdue` alert type to `alert_engine.py` using `set_alert`/`clear_alert` (not the threshold-based `evaluate()` path since this is a date comparison, not a sensor value comparison), and adds a calibration management UI following the `/settings/ai` page pattern.

**NOTF-03 (ntfy)** uses the ntfy HTTP POST API with `aiohttp` (already a bridge dependency) to send notifications when alerts fire. Settings (NTFY_URL, NTFY_TOPIC, enabled) are persisted in a JSON sidecar file following the `AISettings` pattern exactly. The API proxy pattern from `inference_settings_router.py` applies directly to the new ntfy settings router.

**Data retention (05-03)** uses TimescaleDB 2.26.1 (already deployed) built-in `add_retention_policy()` and continuous aggregates. The critical constraint: the continuous aggregate refresh policy `start_offset` must be set to a smaller interval than the raw retention `drop_after` to prevent the cagg from erasing aggregated data when it refreshes over dropped raw data.

**Primary recommendation:** Extend existing patterns exactly — CalibrationStore, AlertEngine, AISettings JSON sidecar, inference_settings_router proxy, /settings/ai page layout — rather than inventing new architecture.

---

## Standard Stack

### Core (all already in hub requirements)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.31.0 | DB queries — CalibrationStore reload, storage stats | Already used throughout bridge and API |
| aiohttp | 3.11.16 | ntfy HTTP POST from bridge; settings proxy from bridge internal server | Already bridge dependency for `notify_api()` |
| FastAPI | 0.135.3 | New routers: calibration, ntfy settings, storage | Already used in API service |
| Pydantic v2 | 2.12.5 | Request/response models for new routers | Already used everywhere |
| TimescaleDB | 2.26.1-pg17 | Continuous aggregates, retention policies | Already deployed; built-in features only |
| SvelteKit | 2.21.0 | New settings pages: /settings/notifications, /settings/storage, /settings/calibration | Already dashboard framework |
| Svelte 5 | 5.28.1 | Component authoring with $state/$props | Already in use |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.3.5 | Bridge unit tests | All Python bridge/API tests |
| pytest-asyncio | 0.25.3 | Async test coroutines | When testing async bridge code |
| vitest | 3.2.4 | Dashboard component tests | All Svelte component tests |
| @testing-library/svelte | 5.2.6 | Render/query in vitest | Component rendering assertions |
| threading.Lock | stdlib | NtfySettings thread safety | Same pattern as AISettings |
| json | stdlib | NtfySettings JSON sidecar | Same pattern as AISettings |

**Version verification:** All versions confirmed from `hub/bridge/requirements.txt`, `hub/api/requirements.txt`, and `hub/dashboard/package.json`. [VERIFIED: codebase grep]

**No new packages required.** Every dependency for Phase 5 is already installed.

---

## Architecture Patterns

### Pattern 1: pH Calibration Overdue Alert (Non-Threshold Alert)

**What:** The pH calibration overdue check is a *date comparison*, not a sensor value threshold. Use `alert_engine.set_alert()` / `alert_engine.clear_alert()` directly — NOT the `evaluate()` method.

**When to use:** Any alert that fires on a discrete event or date condition rather than a continuous sensor value crossing.

**Example:**
```python
# In a periodic calibration check loop (runs every hour in bridge)
# Source: hub/bridge/alert_engine.py set_alert/clear_alert methods

async def check_calibration_overdue(zone_id: str, sensor_type: str):
    is_overdue = calibration_store.is_overdue(zone_id, sensor_type)
    alert_key = f"ph_calibration_overdue:{zone_id}"

    was_active = alert_key in alert_engine._active_alerts
    if is_overdue and not was_active:
        alert_engine.set_alert(alert_key)
        await notify_api({
            "type": "alert_state",
            "alerts": alert_engine.get_alert_state(),
        })
    elif not is_overdue and was_active:
        alert_engine.clear_alert(alert_key)
        await notify_api({
            "type": "alert_state",
            "alerts": alert_engine.get_alert_state(),
        })
```

**ALERT_DEFINITIONS entry to add (in alert_engine.py):**
```python
"ph_calibration_overdue": ("P1", "pH calibration overdue \u2014 {zone_id}", "/zones/{zone_id}"),
```

The deep_link template `/zones/{zone_id}` satisfies the CONTEXT.md specific idea that the alert deep-links to the zone where calibration is needed. [VERIFIED: codebase grep of alert_engine.py]

### Pattern 2: CalibrationStore Extension

**What:** Add `last_calibration_date` tracking to `CalibrationStore`. Load from DB on startup, refresh after recording a calibration. Add `is_overdue()` and `record_calibration()` methods.

```python
# Source: hub/bridge/calibration.py — extend existing class

from datetime import datetime, timedelta, timezone

TWO_WEEKS = timedelta(weeks=2)

class CalibrationStore:
    def __init__(self):
        self._offsets: dict[tuple[str, str], float] = {}
        self._calibration_dates: dict[tuple[str, str], datetime | None] = {}
        # Also store extended fields
        self._dry_values: dict[tuple[str, str], float | None] = {}
        self._wet_values: dict[tuple[str, str], float | None] = {}
        self._temp_coefficients: dict[tuple[str, str], float] = {}

    async def load_from_db(self, db_pool):
        rows = await db_pool.fetch(
            "SELECT zone_id, sensor_type, offset_value, dry_value, wet_value, "
            "temp_coefficient, last_calibration_date FROM calibration_offsets"
        )
        self._offsets = {(r["zone_id"], r["sensor_type"]): r["offset_value"] for r in rows}
        self._calibration_dates = {
            (r["zone_id"], r["sensor_type"]): r["last_calibration_date"] for r in rows
        }
        # ... dry/wet/temp_coefficient similarly

    def is_overdue(self, zone_id: str, sensor_type: str) -> bool:
        """Return True if last_calibration_date is None or older than 2 weeks."""
        key = (zone_id, sensor_type)
        last_cal = self._calibration_dates.get(key)
        if last_cal is None:
            return True  # Never calibrated
        now = datetime.now(timezone.utc)
        # asyncpg returns timezone-aware datetimes for TIMESTAMPTZ
        if last_cal.tzinfo is None:
            last_cal = last_cal.replace(tzinfo=timezone.utc)
        return (now - last_cal) > TWO_WEEKS

    async def record_calibration(self, zone_id: str, sensor_type: str,
                                  offset: float, db_pool, dry_value=None,
                                  wet_value=None, temp_coefficient=0.0):
        """Record calibration event: update in-memory cache and DB."""
        key = (zone_id, sensor_type)
        now = datetime.now(timezone.utc)
        self._offsets[key] = offset
        self._calibration_dates[key] = now
        await db_pool.execute(
            """
            INSERT INTO calibration_offsets
              (zone_id, sensor_type, offset_value, dry_value, wet_value,
               temp_coefficient, last_calibration_date, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (zone_id, sensor_type) DO UPDATE
              SET offset_value = EXCLUDED.offset_value,
                  dry_value = EXCLUDED.dry_value,
                  wet_value = EXCLUDED.wet_value,
                  temp_coefficient = EXCLUDED.temp_coefficient,
                  last_calibration_date = EXCLUDED.last_calibration_date,
                  updated_at = NOW()
            """,
            zone_id, sensor_type, offset, dry_value, wet_value, temp_coefficient, now
        )
```

### Pattern 3: NtfySettings JSON Sidecar (mirrors AISettings exactly)

**What:** Persist ntfy configuration (URL, topic, enabled) in a JSON file. Thread-safe read/write. Bridge reads on startup, API proxy lets dashboard update at runtime without restart.

```python
# Source pattern: hub/bridge/inference/ai_settings.py (verified structure)

import json, os, threading, logging

NTFY_SETTINGS_FILE = os.getenv(
    "NTFY_SETTINGS_FILE",
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "ntfy_settings.json"),
)

_DEFAULT_NTFY = {"url": "", "topic": "", "enabled": False}

class NtfySettings:
    def __init__(self, settings_file=NTFY_SETTINGS_FILE):
        self._file = settings_file
        self._lock = threading.Lock()
        self._settings = {}
        self.load()

    def load(self):
        with self._lock:
            # Seed from env vars if file doesn't exist
            env_url = os.getenv("NTFY_URL", "")
            env_topic = os.getenv("NTFY_TOPIC", "")
            defaults = {"url": env_url, "topic": env_topic, "enabled": bool(env_url)}
            if os.path.exists(self._file):
                with open(self._file) as f:
                    loaded = json.load(f)
                self._settings = {**defaults, **loaded}
            else:
                self._settings = defaults
                self._save_locked()

    def is_enabled(self) -> bool:
        with self._lock:
            return bool(self._settings.get("enabled")) and bool(self._settings.get("url"))

    def get_all(self) -> dict:
        with self._lock:
            return dict(self._settings)

    def update(self, **kwargs) -> None:
        with self._lock:
            self._settings.update(kwargs)
            self._save_locked()

    def _save_locked(self):
        os.makedirs(os.path.dirname(self._file), exist_ok=True)
        with open(self._file, "w") as f:
            json.dump(self._settings, f, indent=2)
```

### Pattern 4: ntfy HTTP POST (Python/aiohttp)

**What:** Send push notification via ntfy HTTP API. Bridge already uses `aiohttp` in `notify_api()`. Add ntfy dispatch in the alert broadcast path.

```python
# Source: docs.ntfy.sh/publish/ — verified via official docs fetch

async def send_ntfy_notification(ntfy_settings: NtfySettings, alert: dict):
    """Send a single alert to the configured ntfy server.

    ntfy HTTP POST format:
      POST {url}/{topic}  OR  POST {url}/ with topic in JSON body
    Headers:  Title, Priority (1-5), Tags
    Priority mapping: P0 -> 5 (urgent), P1 -> 3 (default)
    """
    if not ntfy_settings.is_enabled():
        return
    settings = ntfy_settings.get_all()
    url = settings["url"].rstrip("/")
    topic = settings["topic"]
    priority = "5" if alert.get("severity") == "P0" else "3"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}/{topic}",
                data=alert["message"],
                headers={
                    "Title": "Farm Alert",
                    "Priority": priority,
                    "Tags": "warning",
                },
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status >= 400:
                    logger.warning("ntfy POST failed: %s %s", resp.status, await resp.text())
    except Exception as exc:
        logger.warning("ntfy notification failed (non-critical): %s", exc)
```

**Integration point:** Call `send_ntfy_notification()` in the same code paths that call `notify_api({"type": "alert_state", ...})` after alert state changes. [VERIFIED: official ntfy docs]

### Pattern 5: ntfy Settings Router (mirrors inference_settings_router.py exactly)

```python
# Source: hub/api/inference_settings_router.py — verified structure

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiohttp, os, logging

router = APIRouter()
BRIDGE_INTERNAL_URL = os.getenv("BRIDGE_INTERNAL_URL", "http://bridge:8001")

class NtfySettingsPatch(BaseModel):
    url: str | None = None
    topic: str | None = None
    enabled: bool | None = None

@router.get("/api/settings/notifications")
async def get_ntfy_settings():
    """Proxy GET /internal/ntfy-settings to bridge."""
    ...  # same aiohttp ClientSession pattern as get_ai_settings()

@router.patch("/api/settings/notifications")
async def patch_ntfy_settings(body: NtfySettingsPatch):
    """Proxy PATCH /internal/ntfy-settings to bridge."""
    ...  # same pattern as patch_ai_settings()

@router.post("/api/settings/notifications/test")
async def test_ntfy():
    """Send a test notification via bridge."""
    ...  # POST /internal/ntfy-test to bridge
```

### Pattern 6: TimescaleDB Continuous Aggregate + Two-Level Retention

**What:** Create hourly rollup cagg, add refresh policy, add retention policies on both raw table and cagg. The `start_offset` of the cagg refresh policy MUST be less than the raw data retention interval to avoid erasing cagg data.

```sql
-- Source: docs.tigerdata.com/use-timescale/latest/continuous-aggregates
--         (TimescaleDB docs redirected from docs.timescale.com in 2025)
-- Verified: TimescaleDB 2.26.1-pg17 in docker-compose.yml

-- Step 1: Create continuous aggregate (hourly bucketing)
CREATE MATERIALIZED VIEW sensor_readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    zone_id,
    sensor_type,
    AVG(value)   AS avg_value,
    MIN(value)   AS min_value,
    MAX(value)   AS max_value,
    COUNT(*)     AS reading_count,
    MODE() WITHIN GROUP (ORDER BY quality) AS dominant_quality
FROM sensor_readings
WHERE quality = 'GOOD'
GROUP BY bucket, zone_id, sensor_type
WITH NO DATA;

-- Step 2: Add continuous aggregate refresh policy
-- start_offset (7 days) MUST be < raw retention (90 days) so refresh
-- never looks at dropped raw data and erases existing cagg entries.
SELECT add_continuous_aggregate_policy('sensor_readings_hourly',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Step 3: Retention policy on raw hypertable (90 days)
SELECT add_retention_policy('sensor_readings', INTERVAL '90 days');

-- Step 4: Retention policy on continuous aggregate (2 years)
SELECT add_retention_policy('sensor_readings_hourly', INTERVAL '730 days');
```

**Critical ordering:** Raw retention policy must be added AFTER the cagg refresh policy is defined. [CITED: github.com/timescale/docs/blob/latest/use-timescale/data-retention/data-retention-with-continuous-aggregates.md]

### Pattern 7: Storage Stats Query

**What:** Per-table size query for the storage settings page.

```sql
-- Source: TimescaleDB hypertable_detailed_size function
-- Returns table sizes for dashboard display

SELECT
    hypertable_name,
    pg_size_pretty(total_bytes) AS total_size,
    pg_size_pretty(heap_bytes) AS data_size,
    pg_size_pretty(index_bytes) AS index_size
FROM timescaledb_information.hypertable_detailed_size('sensor_readings');

-- For non-hypertables (egg_counts, etc.)
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size
FROM pg_class
WHERE relname IN ('egg_counts', 'feed_daily_consumption', 'calibration_offsets');
```

**Simpler combined query for the dashboard:**
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

### Pattern 8: Calibration Overdue Periodic Loop in Bridge

**What:** Add a periodic coroutine to `main()` asyncio.gather() that checks all pH sensor calibration dates once per hour. Pattern mirrors `periodic_flock_loop` and `daily_feed_loop`.

```python
# Source: hub/bridge/main.py — periodic_flock_loop pattern

async def periodic_calibration_check(db_pool: asyncpg.Pool):
    """Hourly check: fire/clear ph_calibration_overdue alerts per zone."""
    while True:
        await asyncio.sleep(60 * 60)  # 1 hour
        try:
            # Check all zones that have pH sensors in calibration_offsets
            rows = await db_pool.fetch(
                "SELECT zone_id FROM calibration_offsets WHERE sensor_type = 'ph'"
            )
            alert_changed = False
            for row in rows:
                zone_id = row["zone_id"]
                alert_key = f"ph_calibration_overdue:{zone_id}"
                is_overdue = calibration_store.is_overdue(zone_id, "ph")
                was_active = alert_key in alert_engine._active_alerts
                if is_overdue and not was_active:
                    alert_engine.set_alert(alert_key)
                    alert_changed = True
                elif not is_overdue and was_active:
                    alert_engine.clear_alert(alert_key)
                    alert_changed = True
            if alert_changed:
                await notify_api({
                    "type": "alert_state",
                    "alerts": alert_engine.get_alert_state(),
                })
        except Exception as e:
            logger.error("periodic_calibration_check error: %s", e)
```

Add to `asyncio.gather()` in `main()`: `periodic_calibration_check(db_pool)`.

### Recommended Project Structure (Phase 5 additions only)

```
hub/
├── bridge/
│   ├── calibration.py          # extend: is_overdue(), record_calibration(), dry/wet/temp_coeff
│   ├── alert_engine.py         # extend: ph_calibration_overdue entry in ALERT_DEFINITIONS
│   ├── main.py                 # extend: periodic_calibration_check, ntfy dispatch in alert path
│   ├── ntfy_settings.py        # new: NtfySettings JSON sidecar (mirrors ai_settings.py)
│   └── tests/
│       ├── test_calibration.py       # extend: is_overdue, record_calibration tests
│       ├── test_alert_engine.py      # extend: ph_calibration_overdue alert tests
│       └── test_ntfy_settings.py    # new: NtfySettings load/save/is_enabled tests
├── api/
│   ├── main.py                 # extend: include calibration_router, ntfy_router, storage_router
│   ├── calibration_router.py   # new: GET/PATCH /api/calibration/{zone_id}/{sensor_type}
│   ├── ntfy_router.py          # new: GET/PATCH /api/settings/notifications, POST .../test
│   └── storage_router.py       # new: GET /api/storage/stats, POST /api/storage/purge
├── init-db.sql                 # extend: ALTER TABLE + CREATE MATERIALIZED VIEW + policies
└── dashboard/src/
    └── routes/settings/
        ├── notifications/+page.svelte  # new: ntfy URL/topic/toggle + Test button
        ├── storage/+page.svelte        # new: table sizes + retention status + Purge Now
        └── calibration/+page.svelte   # new: per-sensor calibration management
```

### Anti-Patterns to Avoid

- **Using `evaluate()` for calibration overdue:** The `evaluate()` method is for continuous sensor values with hysteresis bands. Calibration overdue is a date comparison — use `set_alert()`/`clear_alert()` directly.
- **Refreshing cagg with start_offset >= raw retention drop_after:** If `start_offset = INTERVAL '90 days'` and raw retention also drops at 90 days, the cagg refresh will see deleted raw data and erase the aggregated historical data. Keep start_offset at 7 days or less.
- **NtfySettings without thread safety:** The JSON sidecar is written from the aiohttp request handler (asyncio thread) and read from the MQTT loop. Use the same `threading.Lock` pattern as `AISettings`.
- **Calling ntfy synchronously in bridge main loop:** Use `asyncio.create_task()` or wrap in a non-blocking async call so a slow/unavailable ntfy server doesn't stall sensor processing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Automated data purge | Custom cron job or bridge purge loop | `add_retention_policy()` on TimescaleDB hypertable | TimescaleDB handles chunk-level deletion; custom loops miss edge cases and don't handle hypertable chunk boundaries |
| Hourly time-series aggregation | Manual INSERT into summary table from bridge | `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` | Auto-refreshes in background worker, handles backfill, gap-fill support, optimized chunk scanning |
| Push notification gateway | Custom WebSocket push, APNs/FCM integration | ntfy HTTP POST | ntfy handles iOS/Android delivery, queueing, persistence; farmer self-hosts |
| Storage size calculation | Recursive directory walk on filesystem | `pg_total_relation_size()` / `timescaledb_information.hypertable_detailed_size()` | TimescaleDB tracks this exactly including TOAST and indexes; filesystem walk misses PostgreSQL internals |
| Settings persistence for ntfy | Writing to DB table | JSON sidecar file (NtfySettings pattern) | Consistent with AISettings; no DB dependency during bridge startup; survives DB restart ordering issues |

---

## Common Pitfalls

### Pitfall 1: Cagg Refresh Erasing Historical Aggregate Data

**What goes wrong:** Retention policy on sensor_readings drops chunks older than 90 days. If the cagg refresh policy has `start_offset => INTERVAL '91 days'` or greater, the next refresh run scans the dropped data window, sees NULLs, and erases the corresponding cagg rows.

**Why it happens:** The cagg refresh interprets "no raw data in this window" as "aggregate should be NULL/zero."

**How to avoid:** Set cagg refresh `start_offset` to 7 days or less. The refresh only looks back 7 days; raw data for that window still exists. Older cagg rows are untouched.

**Warning signs:** Hourly rollup data disappears from history charts after 90-day mark despite a 730-day cagg retention policy.

### Pitfall 2: NtfySettings Race Condition on Bridge Startup

**What goes wrong:** Bridge starts, `NtfySettings.load()` seeds from `NTFY_URL` env var, but the models/ directory doesn't exist yet (first boot, no Docker volume). `os.makedirs()` fails silently if permissions are wrong.

**Why it happens:** models/ directory is created by the model watcher in Phase 4, but NtfySettings.load() runs before `start_model_watcher()`.

**How to avoid:** Call `os.makedirs(..., exist_ok=True)` at the top of `_save_locked()` (same guard pattern as AISettings). Load gracefully falls back to env var defaults if directory creation fails.

**Warning signs:** ntfy settings reset to env var defaults on every bridge restart.

### Pitfall 3: pH Calibration Alert Fires on Zones Without pH Sensors

**What goes wrong:** The periodic calibration check queries all zones. A zone without a pH sensor has no row in `calibration_offsets` for `sensor_type='ph'`. If the alert check incorrectly fires for zones with no pH sensor, the farmer gets spurious alerts.

**Why it happens:** Query returns all zones, but the `is_overdue()` check for a missing key returns `True` (never calibrated is overdue). Zones without pH sensors shouldn't have a calibration row.

**How to avoid:** Query is `SELECT zone_id FROM calibration_offsets WHERE sensor_type = 'ph'` — only fires for zones that actually have pH calibration records. Don't check zones that have no `calibration_offsets` row for `ph`.

**Warning signs:** Calibration overdue alerts appear for zones that have no pH sensor hardware.

### Pitfall 4: ntfy Blocking the MQTT Processing Loop

**What goes wrong:** `send_ntfy_notification()` called in-line when alert fires. If ntfy server is slow or unreachable, the 5-second timeout blocks the alert evaluation coroutine for 5 seconds on every alert change. During heavy sensor activity this can cause message queue backup in aiomqtt.

**Why it happens:** aiohttp `ClientSession.post()` is async but still awaited in the critical path.

**How to avoid:** Wrap ntfy dispatch in `asyncio.create_task()` so it runs concurrently — same pattern used for `trigger_zone_reinference()` in Phase 4. The call is fire-and-forget (non-critical path).

```python
# Good: non-blocking
asyncio.create_task(send_ntfy_notification(ntfy_settings, alert))

# Bad: blocks alert evaluation loop
await send_ntfy_notification(ntfy_settings, alert)
```

### Pitfall 5: DB Migration Ordering — init-db.sql vs ALTER TABLE

**What goes wrong:** `init-db.sql` is run only on first container creation (Docker entrypoint behavior). The `last_calibration_date` column addition must be an `ALTER TABLE` migration, not just editing `init-db.sql`, for existing deployments.

**Why it happens:** TimescaleDB Docker image runs `init-db.sql` only when the data volume is empty. Existing `data/timescaledb` volume already has the schema.

**How to avoid:** Provide BOTH:
1. Edit `init-db.sql` so new deployments get the column
2. Provide a migration SQL snippet (e.g., `migrations/05-add-last-calibration-date.sql`) for existing deployments with idempotent `ALTER TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`.

**Warning signs:** Bridge fails on startup with `column "last_calibration_date" does not exist` on an existing deployment.

### Pitfall 6: asyncpg TIMESTAMPTZ Timezone Handling

**What goes wrong:** `asyncpg` returns `datetime` objects that may be timezone-naive or timezone-aware depending on PostgreSQL column type and driver settings. Comparing naive and aware datetimes raises `TypeError`.

**Why it happens:** `TIMESTAMPTZ` columns return aware datetimes in asyncpg (UTC). If code uses `datetime.utcnow()` (naive) for comparison, the comparison raises.

**How to avoid:** Always use `datetime.now(timezone.utc)` (aware) for comparisons. In `is_overdue()`, defensively check `if last_cal.tzinfo is None: last_cal = last_cal.replace(tzinfo=timezone.utc)`.

---

## Code Examples

### DB Migration DDL

```sql
-- For existing deployments (hub/migrations/05-add-last-calibration-date.sql)
ALTER TABLE calibration_offsets
  ADD COLUMN IF NOT EXISTS last_calibration_date TIMESTAMPTZ;

-- For init-db.sql (new deployments — add after CREATE TABLE calibration_offsets)
-- Already shown in Standard Stack section above.

-- Continuous aggregate (idempotent via CREATE MATERIALIZED VIEW IF NOT EXISTS)
-- TimescaleDB does NOT support IF NOT EXISTS on cagg; wrap in DO $$ BEGIN EXCEPTION END $$
-- or simply document that this is run once.
```

### NtfySettings Test

```python
# Source: mirrors hub/bridge/tests/test_calibration.py pattern
import tempfile, os, pytest
from ntfy_settings import NtfySettings

def test_ntfy_disabled_when_url_empty(tmp_path):
    settings = NtfySettings(settings_file=str(tmp_path / "ntfy.json"))
    assert settings.is_enabled() is False

def test_ntfy_enabled_when_url_set(tmp_path, monkeypatch):
    monkeypatch.setenv("NTFY_URL", "https://ntfy.example.com")
    monkeypatch.setenv("NTFY_TOPIC", "farm")
    settings = NtfySettings(settings_file=str(tmp_path / "ntfy.json"))
    assert settings.is_enabled() is True

def test_ntfy_update_persists(tmp_path):
    f = str(tmp_path / "ntfy.json")
    settings = NtfySettings(settings_file=f)
    settings.update(url="https://ntfy.sh", topic="myfarm", enabled=True)
    settings2 = NtfySettings(settings_file=f)
    assert settings2.get_all()["url"] == "https://ntfy.sh"
    assert settings2.is_enabled() is True
```

### Svelte Notification Settings Page (pattern from /settings/ai)

```svelte
<!-- hub/dashboard/src/routes/settings/notifications/+page.svelte -->
<script lang="ts">
  let ntfyUrl = $state('');
  let ntfyTopic = $state('');
  let ntfyEnabled = $state(false);
  let testStatus = $state<'idle' | 'sending' | 'ok' | 'error'>('idle');

  async function saveSettings() { ... }  // PATCH /api/settings/notifications
  async function sendTest() {
    testStatus = 'sending';
    const res = await fetch('/api/settings/notifications/test', { method: 'POST' });
    testStatus = res.ok ? 'ok' : 'error';
  }
</script>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual cron job for data purge | TimescaleDB `add_retention_policy()` background worker | TimescaleDB 1.x+ | Chunk-level deletion is orders of magnitude faster than row-level DELETE |
| Manual INSERT to summary tables | TimescaleDB continuous aggregates with auto-refresh | TimescaleDB 1.7+ | Background worker handles gap-fill and backfill; no custom code |
| FCM/APNs for push notifications | Self-hosted ntfy HTTP POST | ntfy v1.0+ (2022), iOS app added 2022 | No cloud dependency; local network compatible; simple HTTP POST |
| ntfy docs on docs.timescale.com | Redirected to docs.tigerdata.com in 2025 | 2025 | Same content, new domain — all TimescaleDB docs now at tigerdata.com |

**Deprecated/outdated:**
- `timescaledb_information.chunks` for size queries: prefer `timescaledb_information.hypertable_detailed_size()` function (available since TimescaleDB 2.x)
- `datetime.utcnow()` (naive): deprecated in Python 3.12+; use `datetime.now(timezone.utc)` throughout

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ADD COLUMN IF NOT EXISTS` syntax is supported by PostgreSQL 17 (PG17 in docker-compose) | Architecture Patterns, Pitfall 5 | Syntax has been in PG since 9.6 — extremely low risk |
| A2 | ntfy iOS and Android apps are available and receive HTTP POST notifications reliably | Standard Stack | Verified iOS app exists on App Store; Android on Play Store; docs confirm — LOW risk |
| A3 | The models/ directory (used by Phase 4 for AI model storage) is the appropriate location for ntfy_settings.json | Architecture Patterns | Could use a dedicated /config directory instead; impact is cosmetic — LOW risk |

---

## Open Questions

1. **Should the calibration management page be /settings/calibration or integrated into /zones/[id]?**
   - What we know: D-02 leaves this to Claude's discretion; /settings/ai is the existing settings pattern; zone detail pages show current sensor values.
   - What's unclear: Whether farmers want to see calibration alongside zone data (contextual) or alongside other system settings (categorized).
   - Recommendation: Use `/settings/calibration` as a dedicated page listing all zone+sensor combinations in a table. Zone detail pages can show the current `last_calibration_date` and link to `/settings/calibration#zone-id` for recording. This avoids cluttering the zone detail view with form inputs.

2. **"Purge Now" button — should it drop raw data only, or also refresh the cagg?**
   - What we know: `drop_chunks()` deletes raw data immediately; cagg refresh can be triggered with `CALL refresh_continuous_aggregate(...)`.
   - What's unclear: Whether forcing an immediate cagg refresh after a manual purge is expected behavior.
   - Recommendation: Implement "Purge Now" as `SELECT drop_chunks('sensor_readings', INTERVAL '90 days')` only. The cagg refresh runs on its own 1-hour schedule and will naturally reflect the purge on next refresh cycle. Add a confirmation dialog.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Bridge tests, calibration/ntfy code | ✓ | 3.10.17 | — |
| pytest | Bridge unit tests | ✓ | 8.3.5 (in requirements.txt) | — |
| Node.js | Dashboard tests | ✓ | 25.3.0 | — |
| vitest | Dashboard component tests | ✓ | 3.2.4 (package.json) | — |
| Docker | Container build | ✓ | 29.1.4 | — |
| TimescaleDB 2.26.1 | Continuous aggregates, retention policies | ✓ (in docker-compose.yml) | 2.26.1-pg17 | — |
| ntfy server | Push notifications (D-06) | External (farmer provides) | — | System works without it (D-09) |
| aiohttp | ntfy HTTP POST from bridge | ✓ | 3.11.16 (in requirements.txt) | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** ntfy server is external and optional by design (D-09). Bridge is silently no-op when NTFY_URL is unset.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Bridge framework | pytest 8.3.5 + pytest-asyncio 0.25.3 |
| Bridge config file | `hub/bridge/requirements.txt` (no pytest.ini; conftest.py at `hub/bridge/tests/`) |
| Dashboard framework | vitest 3.2.4 + @testing-library/svelte 5.2.6 |
| Dashboard config file | `hub/dashboard/vitest.config.ts` |
| Bridge quick run | `cd hub/bridge && python3 -m pytest tests/ -x -q` |
| Bridge full suite | `cd hub/bridge && python3 -m pytest tests/ -v` |
| Dashboard quick run | `cd hub/dashboard && npm test -- --run` |
| Dashboard full suite | `cd hub/dashboard && npm test -- --run --reporter=verbose` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ZONE-07 | CalibrationStore.is_overdue() returns True when >2 weeks since last calibration | unit | `cd hub/bridge && python3 -m pytest tests/test_calibration.py -x -q` | ✅ (extend existing) |
| ZONE-07 | CalibrationStore.is_overdue() returns False when calibrated recently | unit | same | ✅ (extend existing) |
| ZONE-07 | CalibrationStore.record_calibration() updates in-memory date and DB | unit | same | ✅ (extend existing) |
| ZONE-07 | AlertEngine ph_calibration_overdue alert fires and clears correctly | unit | `cd hub/bridge && python3 -m pytest tests/test_alert_engine.py -x -q` | ✅ (extend existing) |
| ZONE-07 | pH calibration overdue alert renders in AlertBar with P1 severity | unit | `cd hub/dashboard && npm test -- --run src/lib/AlertBar.test.ts` | ✅ (extend existing) |
| ZONE-07 | CalibrationSettings Svelte component renders sensor rows with last_calibration_date | unit | `cd hub/dashboard && npm test -- --run` | ❌ Wave 0 |
| NOTF-03 | NtfySettings.is_enabled() returns False when url is empty | unit | `cd hub/bridge && python3 -m pytest tests/test_ntfy_settings.py -x -q` | ❌ Wave 0 |
| NOTF-03 | NtfySettings.update() persists to JSON and reloads correctly | unit | same | ❌ Wave 0 |
| NOTF-03 | NtfySettings seeds from NTFY_URL env var on first load | unit | same | ❌ Wave 0 |
| NOTF-03 | ntfy settings page renders URL/topic fields and Test button | unit | `cd hub/dashboard && npm test -- --run` | ❌ Wave 0 |
| 05-03 | Storage stats API returns table sizes and retention policy info | smoke (manual) | `curl http://localhost:8000/api/storage/stats` | ❌ Wave 0 (no unit test; manual smoke) |

### Sampling Rate

- **Per task commit:** `cd hub/bridge && python3 -m pytest tests/ -x -q && cd hub/dashboard && npm test -- --run`
- **Per wave merge:** Full suite both bridge and dashboard
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `hub/bridge/tests/test_ntfy_settings.py` — covers NOTF-03 NtfySettings unit tests
- [ ] `hub/dashboard/src/lib/CalibrationSettings.test.ts` — covers ZONE-07 calibration UI component
- [ ] `hub/dashboard/src/lib/NtfySettings.test.ts` — covers NOTF-03 ntfy settings form component
- [ ] `hub/bridge/ntfy_settings.py` must exist before test file is written (plan 05-04 creates it)
- [ ] No new framework installs required — all test infrastructure already in place

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user LAN system — no new auth surfaces |
| V3 Session Management | no | No new session endpoints |
| V4 Access Control | no | No multi-user access control |
| V5 Input Validation | yes | Pydantic BaseModel on all PATCH bodies (NtfySettingsPatch, CalibrationPatch); parameterized asyncpg queries ($1 placeholders) throughout |
| V6 Cryptography | no | No new crypto; ntfy topic is a shared secret (existing pattern) |

### Known Threat Patterns for Phase 5 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ntfy URL injection (farmer provides arbitrary URL) | Tampering | Pydantic `HttpUrl` type or explicit URL scheme check (must start with `http://` or `https://`); reject arbitrary URLs with other schemes |
| Calibration offset SQL injection | Tampering | asyncpg parameterized queries ($1, $2 placeholders) — same pattern as all existing queries |
| Storage "Purge Now" without confirmation | Tampering / DoS | Require POST body with `{"confirm": true}` token; optionally add confirmation dialog in UI (Claude's discretion) |
| ntfy topic as password | Information Disclosure | Document in hub.env that NTFY_TOPIC should be a hard-to-guess string (same as MQTT_BRIDGE_PASS guidance) |

---

## Sources

### Primary (HIGH confidence)

- `hub/bridge/calibration.py` — CalibrationStore class structure [VERIFIED: codebase read]
- `hub/bridge/alert_engine.py` — AlertEngine set_alert/clear_alert/ALERT_DEFINITIONS [VERIFIED: codebase read]
- `hub/bridge/main.py` — notify_api, periodic_flock_loop, asyncio.gather pattern [VERIFIED: codebase read]
- `hub/bridge/inference/ai_settings.py` — JSON sidecar pattern with threading.Lock [VERIFIED: codebase read]
- `hub/api/inference_settings_router.py` — GET/PATCH proxy pattern to bridge internal server [VERIFIED: codebase read]
- `hub/init-db.sql` — calibration_offsets schema (missing last_calibration_date confirmed) [VERIFIED: codebase read]
- `hub/docker-compose.yml` — TimescaleDB 2.26.1-pg17 confirmed [VERIFIED: codebase read]
- `hub/bridge/requirements.txt` — all Python dependency versions confirmed [VERIFIED: codebase read]
- `hub/dashboard/package.json` — all JS dependency versions confirmed [VERIFIED: codebase read]
- docs.ntfy.sh/publish/ — HTTP POST API, headers (Title, Priority, Tags), Python example [CITED: https://docs.ntfy.sh/publish/]

### Secondary (MEDIUM confidence)

- github.com/timescale/docs data-retention-with-continuous-aggregates.md — two-level retention strategy, start_offset constraint [CITED: https://github.com/timescale/docs/blob/latest/use-timescale/data-retention/data-retention-with-continuous-aggregates.md]
- docs.tigerdata.com/use-timescale/latest/continuous-aggregates — CREATE MATERIALIZED VIEW WITH (timescaledb.continuous) syntax, add_continuous_aggregate_policy [CITED: https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates]

### Tertiary (LOW confidence)

- None — no WebSearch-only unverified claims.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all library versions confirmed from codebase; no new dependencies introduced
- Architecture: HIGH — extends proven patterns from Phases 2–4; code read directly from source
- ntfy HTTP API: HIGH — verified from official docs.ntfy.sh/publish/
- TimescaleDB cagg/retention: MEDIUM — official docs confirmed via tigerdata.com; start_offset constraint confirmed from GitHub docs; syntax verified against TimescaleDB 2.x documentation
- Pitfalls: HIGH — derived from code reading and verified API behavior

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable libraries; TimescaleDB API very stable across 2.x releases)
