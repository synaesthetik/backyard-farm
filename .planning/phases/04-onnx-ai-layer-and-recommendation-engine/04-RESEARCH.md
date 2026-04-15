# Phase 4: ONNX AI Layer and Recommendation Engine - Research

**Researched:** 2026-04-15
**Domain:** ONNX Runtime inference, scikit-learn model export, APScheduler asyncio scheduling, filesystem hot-reload, synthetic data generation, Svelte 5 UI components
**Confidence:** HIGH (core stack verified against PyPI registry and official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Gate check is enforced in code. The inference service queries TimescaleDB for the GOOD-flag ratio per zone. If any zone is below 80% GOOD-flagged readings over 4+ weeks, that zone's ONNX model is not activated. The gate is real and runtime-enforced.
- **D-02:** A CLI script (`python scripts/generate_synthetic_data.py`) generates 6+ weeks of realistic sensor data and seeds TimescaleDB. This allows bootstrapping the gate in development or after a database reset.
- **D-03:** Synthetic data must be realistic — seasonal VWC curves, temperature swings with diurnal cycles, pH drift, realistic sensor noise, occasional SUSPECT/BAD readings, daylight variation affecting egg production.
- **D-04:** ONNX is primary with rule-based fallback. When ONNX models are loaded and the data maturity gate passes, ONNX drives recommendations. If the model is not loaded, confidence is below threshold, or the farmer toggles it off, the existing `RuleEngine` takes over automatically. No code removal — both engines coexist.
- **D-05:** Per-domain toggle on a dashboard settings page (`/settings/ai`). Three independent toggles: irrigation recommendations, zone health scoring, flock anomaly detection. Each can be set to "AI" or "Rules" independently.
- **D-06:** Toggle is runtime, no restart required. The bridge reads toggle state from the hub (persisted in a config table or JSON file). Changing the toggle takes effect on the next inference cycle.
- **D-07:** Automated retraining on a weekly schedule via APScheduler or cron. Queries latest GOOD-flagged sensor data, trains, exports to .onnx. The farmer never manually triggers training.
- **D-08:** Regression protection — keep previous model as fallback. If new model scores worse than current on holdout set, previous .onnx file is kept. Models directory retains last 2-3 versions.
- **D-09:** Hot-reload via filesystem watch. Inference service watches the models/ directory. When a new .onnx file appears and passes validation, it loads without restarting the bridge.
- **D-10:** Training uses only GOOD-quality-flagged data (AI-06 — non-negotiable). SUSPECT and BAD readings are excluded from both training datasets and live inference feature windows. Enforced in feature aggregation service.
- **D-11:** Rule engine drives all recommendations during cold start. Until models pass the maturity threshold, threshold-based rule engine handles everything.
- **D-12:** AI Status card on Home tab showing maturity progress per domain. Displays data collection progress (e.g., "3 weeks / 4 weeks needed"), recommendation count, and approval/rejection rate per type.
- **D-13:** Model maturity indicator shows approval/rejection rate per domain (AI-07).

### Claude's Discretion

- ONNX model architecture selection (random forest, gradient boosted, small neural net) — the spike (04-02) determines this based on hub hardware benchmarks
- Feature window sizes for each domain
- APScheduler configuration details (inference intervals: zone health 15min, irrigation 1hr, flock 30min)
- Validation metric selection for regression protection
- Synthetic data generator implementation details
- Model file naming convention and versioning scheme
- Threshold for "model confidence too low, fall back to rules"
- AI Status card visual design (defined in 04-UI-SPEC.md)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AI-03 | ONNX Runtime models replace rule engine for zone health scoring, irrigation schedule optimization, and flock production anomaly detection | `hub/inference/` module with InferenceService; bridge toggle bridge reads from config table; `hub/models/` for .onnx files |
| AI-06 | AI training uses only GOOD-quality-flagged sensor data; raw or SUSPECT readings are excluded | Feature aggregation query filters `WHERE quality = 'GOOD'`; enforced at both training and live inference time |
| AI-07 | Model maturity indicator in UI: shows recommendation count and approval/rejection rate per recommendation type | AIStatusCard.svelte component on Home tab; model_maturity table tracks counts; WebSocket snapshot extension |
</phase_requirements>

---

## Summary

Phase 4 introduces ML inference into a running asyncio bridge service. The entire chain — feature aggregation, ONNX inference, APScheduler-driven scheduling, filesystem hot-reload on model update, and a Svelte 5 UI card — must integrate without disrupting the existing bridge pipeline. The codebase is well-structured: `RuleEngine`, `AlertEngine`, `health_score.py`, and `production_model.py` all produce recommendation dicts and health payloads with clear interfaces that ONNX inference simply replaces or augments under the per-domain toggle.

The ML stack is standard and verified: scikit-learn trains, `skl2onnx` exports to .onnx, `onnxruntime` runs inference. All three are actively maintained (scikit-learn 1.7.2, skl2onnx 1.20.0, onnxruntime 1.23.2 as of research date). `APScheduler 3.11.2` `AsyncIOScheduler` integrates directly into the existing `asyncio.gather()` pattern in `main.py`. The `watchdog 6.0.0` library provides reliable filesystem event detection for hot-reload.

The biggest architectural decision is where the inference service lives: in the bridge process (alongside the existing engines) following the established hub-side computation pattern. All computations today (health scores, rule evaluation, alert evaluation) run in the bridge. ONNX inference follows this pattern, adding a new `hub/inference/` module imported into `bridge/main.py`. The toggle state is persisted in a new `ai_settings` table (or JSON sidecar file) and checked by the bridge before deciding which engine to call.

**Primary recommendation:** Keep inference in the bridge process. Add `hub/inference/` module with `FeatureAggregator`, `InferenceService`, `ModelWatcher` (watchdog), and `InferenceScheduler` (APScheduler). The bridge's `main()` function adds the scheduler to `asyncio.gather()`. The rule engine path remains unchanged; the ONNX path is layered in as a conditional branch.

---

## Standard Stack

### Core (Inference / Training)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| onnxruntime | 1.23.2 | ONNX model inference at runtime | Project requirement (AI-03); CPU-only package is correct for ARM hub hardware; no GPU dependency |
| scikit-learn | 1.7.2 | Model training (random forest, gradient boosting) | Standard tabular ML library; the spike (04-02) selects the final architecture |
| skl2onnx | 1.20.0 | Export scikit-learn models to .onnx format | The official sklearn→ONNX conversion library maintained by onnx.ai |
| numpy | 2.2.6 | Feature array construction and data type handling | Required by onnxruntime and skl2onnx; already a transitive dependency |

### Scheduling / Hot-Reload

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| APScheduler | 3.11.2 | Interval-based inference scheduling in asyncio context | `AsyncIOScheduler` integrates into existing `asyncio.gather()` without a separate thread |
| watchdog | 6.0.0 | Filesystem event detection for .onnx hot-reload | Cross-platform; `PatternMatchingEventHandler` watches `*.onnx` file creation |

### Existing (No New Additions)

| Library | Already Pinned | Phase 4 Usage |
|---------|----------------|---------------|
| asyncpg | 0.31.0 | Feature aggregation queries to TimescaleDB |
| aiohttp | 3.11.16 | Inference settings API proxying (bridge→API pattern) |
| pydantic | 2.12.5 | Inference config and maturity state models |
| FastAPI | 0.135.3 | New `/api/settings/ai` and `/api/model-maturity` endpoints in API process |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| onnxruntime (CPU) | onnxruntime-gpu | No GPU on hub hardware; CPU package is lighter and sufficient |
| skl2onnx | torch + torch.onnx.export | Torch adds ~800MB to the image; skl2onnx is <10MB for tree models |
| watchdog | polling loop (asyncio.sleep) | Polling misses rapid file replacements; watchdog uses OS inotify/FSEvents |
| APScheduler 3.x | APScheduler 4.x | APScheduler 4.x dropped the `AsyncIOScheduler` class in favor of a new API — the 3.x `AsyncIOScheduler` fits our existing `asyncio.gather()` pattern without a rewrite |

**Installation (new packages only — add to `hub/bridge/requirements.txt`):**
```bash
# Add to hub/bridge/requirements.txt:
onnxruntime==1.23.2
scikit-learn==1.7.2
skl2onnx==1.20.0
numpy==2.2.6
APScheduler==3.11.2
watchdog==6.0.0
```

**Version verification:** [VERIFIED: pip3 index versions — 2026-04-15]

---

## Architecture Patterns

### Recommended Project Structure

```
hub/
├── bridge/
│   ├── main.py                     # Add inference service + scheduler to asyncio.gather()
│   ├── rule_engine.py              # Unchanged — remains as fallback
│   ├── alert_engine.py             # Unchanged — receives anomaly signals from ONNX
│   ├── health_score.py             # Unchanged — used when ONNX toggle is off
│   └── inference/                  # New module
│       ├── __init__.py
│       ├── feature_aggregator.py   # 04-01: TimescaleDB sensor window queries
│       ├── inference_service.py    # 04-03/04: Load ONNX session, run inference
│       ├── inference_scheduler.py  # 04-05: APScheduler jobs + event-triggered re-inference
│       ├── model_watcher.py        # 04-05: watchdog hot-reload handler
│       ├── maturity_tracker.py     # 04-05: tracks recommendation count, approval rate
│       ├── training/               # Offline training pipeline (04-03/04)
│       │   ├── train_zone_health.py
│       │   ├── train_irrigation.py
│       │   └── train_flock_anomaly.py
│       └── synthetic/              # 04-01 / D-02
│           └── generate_synthetic_data.py  # Also exposed as scripts/generate_synthetic_data.py
├── models/                         # .onnx model files (D-09)
│   ├── zone_health.onnx
│   ├── zone_health.prev.onnx
│   ├── irrigation.onnx
│   └── flock_anomaly.onnx
└── api/
    ├── main.py                     # Mount new routers
    └── inference_settings_router.py  # PATCH /api/settings/ai, GET /api/model-maturity

hub/dashboard/src/
├── lib/
│   ├── AIStatusCard.svelte         # New — D-12, AI-07
│   ├── DomainMaturityRow.svelte    # New — sub-component (defined in 04-UI-SPEC.md)
│   ├── AISettingsToggle.svelte     # New — D-05, D-06
│   ├── RecommendationCard.svelte   # Modified — add "AI"/"RULES" source badge
│   └── types.ts                    # Extend: ModelMaturityState, AISettingsDelta
└── routes/
    ├── +page.svelte                # Insert AIStatusCard into flock-col
    └── settings/
        └── ai/
            └── +page.svelte        # New route — 3x AISettingsToggle instances

scripts/
└── generate_synthetic_data.py      # D-02 CLI entry point
```

### Pattern 1: Feature Aggregation (04-01)

**What:** Query TimescaleDB for the most recent N hours of GOOD-flagged sensor readings per zone, compute aggregate statistics (mean, min, max, std, rate-of-change) that form the ONNX model input vector.

**When to use:** Called by `InferenceScheduler` on each scheduled run and on threshold-crossing re-inference events.

**Critical:** The GOOD-flag filter is applied in SQL, not in Python. It is not optional.

```python
# Source: hub/bridge/main.py pattern (existing asyncpg usage)
async def aggregate_zone_features(
    db_pool: asyncpg.Pool,
    zone_id: str,
    sensor_types: list[str],
    window_hours: int = 24,
) -> dict[str, float] | None:
    """Aggregate GOOD-flagged sensor readings into feature vector.

    Returns None if insufficient data (< MIN_READINGS threshold).
    AI-06: quality = 'GOOD' filter is mandatory, not optional.
    """
    rows = await db_pool.fetch(
        """
        SELECT sensor_type, value
        FROM sensor_readings
        WHERE zone_id = $1
          AND quality = 'GOOD'
          AND time > NOW() - ($2 || ' hours')::interval
        ORDER BY time DESC
        """,
        zone_id,
        str(window_hours),
    )
    if len(rows) < MIN_READINGS:
        return None  # Not enough GOOD data — fall back to rules
    # Compute mean/min/max/std per sensor_type
    ...
```

### Pattern 2: ONNX Inference Session (03/04)

**What:** Load .onnx file once at startup (and on hot-reload). Run synchronous inference using `onnxruntime.InferenceSession`. Session creation is expensive; inference per call is cheap (~ms for tree models).

**When to use:** Called from `InferenceService.infer()` which the scheduler invokes.

```python
# Source: [CITED: onnxruntime.ai/docs/get-started/with-python.html]
import onnxruntime as ort
import numpy as np

class InferenceService:
    def __init__(self, model_path: str):
        self._session: ort.InferenceSession | None = None
        self._load(model_path)

    def _load(self, model_path: str):
        """Load ONNX session. Called at startup and on hot-reload."""
        self._session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

    def infer(self, feature_vector: list[float]) -> tuple[float, float]:
        """Run inference. Returns (score, confidence).

        Returns (0.0, 0.0) if session is not loaded.
        """
        if self._session is None:
            return 0.0, 0.0
        arr = np.array([feature_vector], dtype=np.float32)
        result = self._session.run(
            [self._output_name],
            {self._input_name: arr},
        )
        return float(result[0][0]), 1.0  # confidence TBD in spike
```

### Pattern 3: skl2onnx Export (Training Pipeline)

**What:** Train scikit-learn model offline, export to .onnx with `convert_sklearn`. This runs on developer machine, not on hub.

```python
# Source: [CITED: onnx.ai/sklearn-onnx/auto_examples/plot_convert_model.html]
from sklearn.ensemble import RandomForestClassifier  # or GradientBoostingClassifier
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import onnx

# N_FEATURES = number of aggregated features in the feature vector
initial_type = [("float_input", FloatTensorType([None, N_FEATURES]))]
onx = convert_sklearn(
    clf,
    initial_types=initial_type,
    target_opset=12,  # 12 is well-tested; max supported is 21
)
# Validate before saving
onnx.checker.check_model(onx)
with open("hub/models/zone_health.onnx", "wb") as f:
    f.write(onx.SerializeToString())
```

### Pattern 4: APScheduler AsyncIOScheduler (04-05)

**What:** Schedule periodic inference jobs within the existing `asyncio.gather()` event loop in `bridge/main.py`. `AsyncIOScheduler` does NOT block the loop — it integrates as a cooperative coroutine scheduler.

**Critical:** APScheduler 4.x changed its API significantly and dropped `AsyncIOScheduler`. Pin to 3.x.

```python
# Source: [CITED: apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html]
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def main():
    db_pool = await asyncpg.create_pool(...)
    inference_svc = InferenceService(...)

    scheduler = AsyncIOScheduler(
        job_defaults={"coalesce": True, "max_instances": 1}
    )
    scheduler.add_job(
        run_zone_health_inference,
        "interval",
        minutes=15,
        args=[db_pool, inference_svc],
        id="zone_health",
    )
    scheduler.add_job(
        run_irrigation_inference,
        "interval",
        hours=1,
        args=[db_pool, inference_svc],
        id="irrigation",
    )
    scheduler.add_job(
        run_flock_anomaly_inference,
        "interval",
        minutes=30,
        args=[db_pool, inference_svc],
        id="flock_anomaly",
    )
    scheduler.start()  # Start BEFORE asyncio.gather()

    await asyncio.gather(
        bridge_loop(db_pool),
        coop_scheduler_loop(notify_callback=notify_api),
        run_internal_server(db_pool),
        periodic_flock_loop(db_pool),
        daily_feed_loop(db_pool),
        # Scheduler runs in the loop; no new coroutine needed here
    )
```

**Note on Python 3.10 + asyncio.get_event_loop():** APScheduler 3.x internally calls `asyncio.get_event_loop()` in some paths. On Python 3.10 this emits a DeprecationWarning when called outside of a running loop. The fix is to call `scheduler.start()` AFTER the event loop is running (inside an async function, not at module level). The pattern above is safe. [CITED: docs.python.org/3.10/library/asyncio-eventloop.html]

### Pattern 5: watchdog Hot-Reload (04-05)

**What:** Watch the `hub/models/` directory for new .onnx files. On creation, validate and atomically swap the loaded ONNX session.

```python
# Source: [CITED: pypi.org/project/watchdog/]
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import threading

class OnnxModelHandler(PatternMatchingEventHandler):
    def __init__(self, inference_service: InferenceService):
        super().__init__(patterns=["*.onnx"], ignore_directories=True)
        self._svc = inference_service

    def on_created(self, event):
        """Called when a new .onnx file appears in models/ directory."""
        # Validate before swap (D-08 regression protection)
        try:
            import onnx
            model = onnx.load(event.src_path)
            onnx.checker.check_model(model)
            self._svc.reload(event.src_path)
        except Exception as e:
            logger.error("Hot-reload rejected: %s — %s", event.src_path, e)

def start_model_watcher(models_dir: str, inference_service: InferenceService):
    handler = OnnxModelHandler(inference_service)
    observer = Observer()
    observer.schedule(handler, path=models_dir, recursive=False)
    observer.start()  # Runs in a daemon thread — compatible with asyncio bridge
    return observer
```

**Note:** `watchdog.Observer` runs in a background thread. It does not conflict with asyncio. The hot-reload swap must be thread-safe: use `threading.Lock` or swap the session reference atomically (CPython GIL provides reference-swap safety for simple attribute assignment).

### Pattern 6: Toggle State Persistence

**What:** AI/Rules toggle state per domain, persisted so the bridge can read it after restart without touching the running dashboard.

**Recommended approach:** A `ai_settings` row in the existing TimescaleDB (or a JSON sidecar file at `hub/models/ai_settings.json`). JSON sidecar is simpler — no DB migration, no asyncpg read on every inference cycle. The bridge reads it once at startup and caches it in memory; the internal HTTP server endpoint updates both file and in-memory cache when the API patches it.

```python
# ai_settings.json schema
{
  "irrigation": "ai",       # "ai" | "rules"
  "zone_health": "ai",
  "flock_anomaly": "rules"
}
```

### Pattern 7: Recommendation Dict Compatibility

**Critical:** ONNX inference must produce recommendation dicts with the same keys as `RuleEngine.evaluate_zone()`. The downstream pipeline (deduplication, back-off, approve/reject, WebSocket broadcast) is key-matched.

```python
# Required output shape — matches existing Recommendation type in types.ts
{
    "recommendation_id": str(uuid.uuid4()),
    "zone_id": zone_id,
    "rec_type": "irrigate" | "zone_health" | "flock_anomaly",
    "action_description": "...",
    "sensor_reading": "...",
    "explanation": "...",
    "source": "ai",  # NEW field — drives "AI"/"RULES" badge in RecommendationCard
}
```

The `source` field must be added to the `Recommendation` TypeScript interface in `types.ts`.

### Pattern 8: Model Maturity Tracking

**What:** A `model_maturity` table (or in-memory dict persisted to JSON) tracks: recommendation count, approved count, rejected count — per domain. Updated by the bridge whenever a recommendation is approved or rejected via the internal endpoint.

```sql
-- Suggested table (simplest option: use existing TimescaleDB)
CREATE TABLE IF NOT EXISTS model_maturity (
    domain TEXT PRIMARY KEY,          -- 'irrigation' | 'zone_health' | 'flock_anomaly'
    recommendation_count INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Anti-Patterns to Avoid

- **Loading the ONNX session on every inference call:** `InferenceSession()` is expensive (reads file, allocates runtime). Load once at startup; reload only on hot-reload event.
- **Running scikit-learn training on the hub during live inference:** Training is CPU-intensive. The roadmap specifies offline training on a development machine. The hub only runs inference and scheduled retraining during low-load hours.
- **Using APScheduler 4.x:** Major API break — `AsyncIOScheduler` was removed. Pin to `3.11.2`.
- **Blocking asyncio event loop during inference:** `onnxruntime` inference is synchronous but fast (< 5ms for tree models on CPU). For the model sizes in this project, calling it directly in an async function without `run_in_executor` is acceptable. If benchmarks in 04-02 show > 50ms, wrap in `loop.run_in_executor(None, ...)`.
- **Global flag filter as an optional parameter:** The `quality = 'GOOD'` filter in feature aggregation must be structural (in the SQL WHERE clause), not a keyword argument that can be omitted by callers.
- **Swapping `health_score.py` output shape:** ONNX zone health must return `{"score": "green"|"yellow"|"red", "contributing_sensors": [...]}` — same shape as `compute_health_score()`. The WebSocket broadcast and `ZoneCard.svelte` are typed against this shape.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sklearn→ONNX model export | Custom serialization / pickle | `skl2onnx.convert_sklearn()` | Handles all tree model variants, opset versioning, input type annotations |
| ONNX model loading and inference | Custom model runner | `onnxruntime.InferenceSession` | Hardware-optimized execution paths, thread safety, memory management |
| Filesystem event detection | `asyncio.sleep()` polling loop | `watchdog` library | Uses OS inotify/FSEvents — reliable for atomic file replacement; polling misses rapid swaps |
| Periodic scheduled inference | `asyncio.sleep()` coroutine loop | `APScheduler AsyncIOScheduler` | Handles missed-fire recovery, coalescing, jitter, graceful shutdown |
| ONNX model validation | Manual byte inspection | `onnx.checker.check_model()` | Validates ONNX IR, catches corrupt exports before hot-reload |

**Key insight:** For tabular sensor data at this scale, the open-source scikit-learn + skl2onnx + onnxruntime chain is the industry standard. Custom model runners add maintenance burden with no benefit.

---

## Common Pitfalls

### Pitfall 1: APScheduler 4.x API Break

**What goes wrong:** Installing `apscheduler` without pinning version picks up 4.x, which removed `AsyncIOScheduler`. Import fails at bridge startup.

**Why it happens:** PyPI latest is 4.x. The 3.x API is the familiar one documented in most tutorials.

**How to avoid:** Pin `APScheduler==3.11.2` in `requirements.txt`. The 3.x `AsyncIOScheduler` is the one that integrates with the existing `asyncio.gather()` pattern in `bridge/main.py`.

**Warning signs:** `ImportError: cannot import name 'AsyncIOScheduler' from 'apscheduler.schedulers.asyncio'`

### Pitfall 2: ONNX Session Reload Thread Safety

**What goes wrong:** watchdog handler (running in OS thread) replaces the session reference while bridge event loop is reading it mid-inference. Results in `None` dereference or stale session use.

**Why it happens:** `watchdog.Observer` runs in a daemon thread outside asyncio.

**How to avoid:** Use `threading.Lock` around session load and inference. OR: post the reload to the asyncio loop using `asyncio.get_event_loop().call_soon_threadsafe(reload_callback)` so it executes between event loop iterations, where inference is not in-flight.

**Warning signs:** Random `AttributeError: 'NoneType' has no attribute 'run'` under concurrent load.

### Pitfall 3: skl2onnx opset Mismatch

**What goes wrong:** Training on developer machine with skl2onnx 1.20.0 exports at opset 21; hub runs onnxruntime 1.23.2 which supports up to opset 21 — this is fine. But if the hub runs an older onnxruntime version, inference fails silently or raises `InvalidGraph`.

**Why it happens:** The opset version in the .onnx file must be supported by the onnxruntime version on the inference host.

**How to avoid:** Pin the same onnxruntime version in both the training environment and `hub/bridge/requirements.txt`. Use `target_opset=12` in `convert_sklearn()` — opset 12 is supported by every onnxruntime release since 1.5 and is well-tested for tree models. [CITED: onnx.ai/sklearn-onnx/auto_tutorial/plot_cbegin_opset.html]

### Pitfall 4: Feature Vector Shape Mismatch at Inference Time

**What goes wrong:** Training uses 20 features; live inference aggregates 18 (two sensor types have no GOOD data in the window). InferenceSession raises `InvalidInput` shape error.

**Why it happens:** Sensor outages or cold-start periods reduce available features.

**How to avoid:** Feature aggregation must always produce a fixed-length vector. Missing sensors get a sentinel value (e.g., `nan` or zone-config midpoint). Define the feature schema once and validate it in the aggregator before calling inference. If the feature vector is invalid (too many `nan` values), return `None` and fall back to rules.

### Pitfall 5: Data Maturity Gate Does Not Account for Time Gaps

**What goes wrong:** A zone has 6 weeks of data but 3 of those weeks had a sensor offline (all BAD). The gate passes because total time > 4 weeks, but the GOOD-flag ratio is below 80%.

**Why it happens:** Gate check counts total time span, not GOOD-quality coverage.

**How to avoid:** The gate check (D-01) must compute the ratio: `COUNT(*) FILTER (WHERE quality = 'GOOD') / COUNT(*)` over the time window, not just check whether the window spans 4 weeks. This is the runtime-enforced check in the inference service. [ASSUMED: specific SQL formulation — verify against actual TimescaleDB query before implementation]

### Pitfall 6: Recommendation source Field Missing from TypeScript Types

**What goes wrong:** ONNX recommendations include `"source": "ai"` but the TypeScript `Recommendation` interface doesn't have this field. The dashboard store discards it; the source badge in RecommendationCard has no data.

**Why it happens:** The existing `Recommendation` interface in `types.ts` was written before Phase 4.

**How to avoid:** Add `source?: 'ai' | 'rules'` to the `Recommendation` interface in `hub/dashboard/src/lib/types.ts` before implementing the RecommendationCard badge. The existing `recommendation_router.py` and `RuleEngine` don't set this field — they'll default to `undefined`, which the badge should treat as `'rules'`.

### Pitfall 7: watchdog Missing Events on macOS

**What goes wrong:** During development on macOS, watchdog's `Observer` uses FSEvents, which may batch events or delay them. A new .onnx file isn't picked up for several seconds.

**Why it happens:** macOS FSEvents has a default latency (0.5–2s). This is benign in production but confusing during testing.

**How to avoid:** Use `watchdog.observers.polling.PollingObserver` in tests for deterministic behavior. In production (Linux Docker container), the default `Observer` uses inotify, which is immediate.

### Pitfall 8: Training Data Leakage into Cold-Start Synthetic Data

**What goes wrong:** The synthetic data generator uses the same seasonal parameters for training and inference validation, inadvertently making the model look better than it is on real data.

**Why it happens:** Synthetic data has unrealistically clean distributions. Real sensor data has calibration drift, stuck sensors, outliers.

**How to avoid:** The synthetic generator (D-03) must inject realistic noise — SUSPECT/BAD readings at ~5-10% of rows, sensor drift, occasional stuck values. The model must be validated on real (even if limited) data from Phase 1/2/3 operation, not purely on synthetic holdout sets.

---

## Code Examples

### Feature Aggregation Query

```python
# Source: pattern derived from existing bridge/main.py asyncpg usage
# GOOD-flag filter is structural (in WHERE) — not optional
FEATURE_QUERY = """
SELECT
    sensor_type,
    AVG(value)       AS mean_val,
    MIN(value)       AS min_val,
    MAX(value)       AS max_val,
    STDDEV(value)    AS std_val,
    COUNT(*)         AS reading_count
FROM sensor_readings
WHERE zone_id = $1
  AND quality = 'GOOD'
  AND time > NOW() - ($2 || ' hours')::interval
GROUP BY sensor_type
"""
```

### Data Maturity Gate Query

```python
# Source: [ASSUMED — verify against actual TimescaleDB schema before implementation]
MATURITY_GATE_QUERY = """
SELECT
    COUNT(*) FILTER (WHERE quality = 'GOOD')::float / NULLIF(COUNT(*), 0) AS good_ratio,
    MIN(time) AS earliest_reading,
    NOW() - MIN(time) AS data_span
FROM sensor_readings
WHERE zone_id = $1
  AND time > NOW() - INTERVAL '4 weeks'
"""
# Returns good_ratio (0.0-1.0), gate passes when good_ratio >= 0.8
# AND data_span >= '4 weeks'::interval
```

### InferenceService.reload() (Thread-Safe Hot-Reload)

```python
# Source: [ASSUMED — based on onnxruntime and threading patterns]
import threading

class InferenceService:
    def __init__(self, model_path: str | None):
        self._lock = threading.Lock()
        self._session: ort.InferenceSession | None = None
        if model_path and os.path.exists(model_path):
            self._load_locked(model_path)

    def _load_locked(self, model_path: str):
        session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        with self._lock:
            self._session = session  # Atomic reference swap under lock

    def reload(self, model_path: str):
        """Called from watchdog handler thread."""
        self._load_locked(model_path)

    def infer(self, features: np.ndarray) -> float | None:
        with self._lock:
            session = self._session
        if session is None:
            return None  # Fallback to rules
        result = session.run(None, {session.get_inputs()[0].name: features})
        return float(result[0][0])
```

### WS Snapshot Extension (model maturity)

```typescript
// Add to DashboardSnapshot in hub/dashboard/src/lib/types.ts
export interface ModelMaturityEntry {
  domain: 'irrigation' | 'zone_health' | 'flock_anomaly';
  mode: 'ai' | 'rules';
  weeks_of_data: number;         // weeks with >= 80% GOOD-flagged data
  good_flag_ratio: number;       // 0.0-1.0 for current zone/domain
  recommendation_count: number;
  approved_count: number;
  rejected_count: number;
  gate_passed: boolean;
}

// Add to DashboardSnapshot:
model_maturity: ModelMaturityEntry[] | null;
```

### RecommendationCard Source Badge (Svelte 5)

```svelte
<!-- Add inside .controls div in RecommendationCard.svelte -->
<!-- Source: HealthBadge.svelte pattern (hub/dashboard/src/lib/HealthBadge.svelte) -->
<span
  class="source-badge"
  class:ai={source === 'ai'}
  class:rules={source !== 'ai'}
  aria-label="Generated by {source === 'ai' ? 'AI model' : 'rule engine'}"
>
  {source === 'ai' ? 'AI' : 'RULES'}
</span>

<style>
  .source-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 3px var(--spacing-sm);
    border-radius: 99px;
  }
  .source-badge.ai {
    background: var(--color-accent);
    color: var(--color-bg);
  }
  .source-badge.rules {
    background: var(--color-border);
    color: var(--color-text-secondary);
  }
</style>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 3.x `AsyncIOScheduler` | APScheduler 4.x new API | APScheduler 4.0 (2024) | We pin to 3.x; 4.x would require a full scheduler rewrite |
| pickle for model serialization | ONNX format | Industry shift 2020-present | ONNX is runtime-agnostic; pickle is Python-only and version-sensitive |
| scikit-learn predict() at runtime | ONNX Runtime inference | Current standard | 3-10x faster inference for tree models; no scikit-learn at runtime |
| `asyncio.get_event_loop()` | `asyncio.get_running_loop()` or `asyncio.run()` | Python 3.10 deprecation | APScheduler 3.x workaround: call `scheduler.start()` inside async context |

**Deprecated/outdated:**
- `APScheduler >= 4.0`: Dropped `AsyncIOScheduler` class. Do NOT upgrade past 3.11.2.
- `onnxruntime-gpu`: Unnecessary for this project; CPU package covers all use cases. Two packages conflict if both installed — install only `onnxruntime`.
- `skl2onnx target_opset > 21`: Exceeds tested range as of skl2onnx 1.20.0. Use opset 12 for maximum compatibility.

---

## Runtime State Inventory

> This is a greenfield addition (new `hub/inference/` module, new `hub/models/` directory, new DB table). No existing runtime state is renamed or migrated.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — inference service is new; model_maturity table is new | Create via migration in Wave 0 |
| Live service config | None — ai_settings.json/table is new | Create in Wave 0 with default `"rules"` for all domains |
| OS-registered state | None | None |
| Secrets/env vars | None new — inference uses existing POSTGRES_* env vars | None |
| Build artifacts | None — hub/models/ directory is new; no stale artifacts | None |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10 | Bridge process | ✓ | 3.10.17 | — |
| pip / PyPI | Package install | ✓ | — | — |
| onnxruntime (pip) | Inference at runtime | ✗ (not yet installed) | 1.23.2 available | No fallback — required |
| scikit-learn (pip) | Model training | ✗ (not yet installed) | 1.7.2 available | No fallback for training; inference-only hub does not need this if models are pre-trained |
| skl2onnx (pip) | Model export | ✗ (not yet installed) | 1.20.0 available | No fallback for export |
| APScheduler (pip) | Inference scheduling | ✗ (not yet installed) | 3.11.2 available | No fallback — required |
| watchdog (pip) | Hot-reload | ✗ (not yet installed) | 6.0.0 available | Polling fallback acceptable in dev |
| numpy (pip) | Feature arrays | ✗ (not yet installed) | 2.2.6 available | No fallback — required by onnxruntime |
| TimescaleDB | Feature aggregation | ✓ (existing) | — | — |

**Missing dependencies with no fallback:**
- `onnxruntime`, `APScheduler`, `numpy` — must be added to `hub/bridge/requirements.txt` before any inference code runs.

**Missing dependencies with fallback:**
- `watchdog` — polling observer can substitute in dev/CI; inotify Observer is preferred in production Docker container.
- `scikit-learn`, `skl2onnx` — training runs on developer machine, not on hub. Hub only needs `onnxruntime` at runtime. Training deps go in a separate `scripts/requirements-training.txt`.

**Note:** `scikit-learn` and `skl2onnx` do NOT need to be in `hub/bridge/requirements.txt` if the training pipeline runs offline. Keeping them off the bridge image saves ~300MB from the Docker layer.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest 8.3.5 + pytest-asyncio 0.25.3 (hub/bridge) |
| JS/TS framework | vitest 3.1.1 + @testing-library/svelte 5.2.6 (hub/dashboard) |
| Python config | hub/bridge/tests/conftest.py (sys.path injection) |
| Python quick run | `cd hub/bridge && python -m pytest tests/ -x -q` |
| Python full suite | `cd hub/bridge && python -m pytest tests/ -v` |
| JS quick run | `cd hub/dashboard && npm test -- --run` |
| JS full suite | `cd hub/dashboard && npm test -- --run --reporter=verbose` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-03 | ONNX inference replaces rule engine when toggle is "ai" | unit | `python -m pytest tests/inference/ -x -q` | ❌ Wave 0 |
| AI-03 | ONNX output dict has same keys as RuleEngine output | unit | `python -m pytest tests/inference/test_inference_service.py -x` | ❌ Wave 0 |
| AI-03 | Rule engine fallback activates when ONNX session is None | unit | `python -m pytest tests/inference/test_inference_service.py::test_fallback -x` | ❌ Wave 0 |
| AI-06 | Feature aggregation query excludes non-GOOD readings | unit | `python -m pytest tests/inference/test_feature_aggregator.py -x` | ❌ Wave 0 |
| AI-06 | Gate check correctly computes good_ratio and data_span | unit | `python -m pytest tests/inference/test_maturity_tracker.py -x` | ❌ Wave 0 |
| AI-07 | AIStatusCard renders cold-start message when gate not passed | unit | `npm test -- --run src/lib/AIStatusCard.test.ts` | ❌ Wave 0 |
| AI-07 | AIStatusCard renders "Mature" + correct approval rate when gate passed | unit | `npm test -- --run src/lib/AIStatusCard.test.ts` | ❌ Wave 0 |
| AI-07 | AISettingsToggle renders disabled when domain not mature | unit | `npm test -- --run src/lib/AISettingsToggle.test.ts` | ❌ Wave 0 |
| AI-07 | RecommendationCard renders AI/RULES source badge | unit | `npm test -- --run src/lib/RecommendationCard.test.ts` | ❌ Wave 0 (extend existing file) |

### Wave 0 Gaps

- [ ] `hub/bridge/tests/inference/` directory — new subdirectory for inference tests
- [ ] `hub/bridge/tests/inference/test_feature_aggregator.py` — covers AI-06 (GOOD-flag filter)
- [ ] `hub/bridge/tests/inference/test_inference_service.py` — covers AI-03 (session load, infer, fallback, reload)
- [ ] `hub/bridge/tests/inference/test_maturity_tracker.py` — covers AI-06 (gate check), AI-07 (count tracking)
- [ ] `hub/dashboard/src/lib/AIStatusCard.test.ts` — covers AI-07 (card states)
- [ ] `hub/dashboard/src/lib/AISettingsToggle.test.ts` — covers AI-07 (toggle states, disabled)
- [ ] `hub/dashboard/src/lib/RecommendationCard.test.ts` — extend existing file to add source badge tests

The bridge conftest.py already handles `sys.path.insert` — new inference test subdirectory needs its own `__init__.py` or be included in the root test collection.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Existing JWT pattern unchanged |
| V3 Session Management | No | Unchanged |
| V4 Access Control | Yes (toggle endpoint) | Existing bearer auth on `/api/settings/ai` — same pattern as other write endpoints |
| V5 Input Validation | Yes | Feature vector bounds checking before inference; reject malformed .onnx uploads |
| V6 Cryptography | No | No new cryptographic operations |

### Known Threat Patterns for ONNX Inference Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed .onnx file injection (model substitution) | Tampering | `onnx.checker.check_model()` before hot-reload; models/ directory writable only by bridge process |
| Inference DoS (very large feature vector) | Denial of Service | Fixed input shape enforced by InferenceSession; feature vector is always `[1, N_FEATURES]` |
| Toggle endpoint exposed without auth | Elevation of Privilege | `/api/settings/ai` requires same auth as other write endpoints (existing bearer JWT pattern) |
| Synthetic data misclassified as real in training | Tampering | Flag synthetic rows with `is_synthetic = TRUE` column; training pipeline filters these out by default |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ai_settings persisted as JSON sidecar (not DB table) is simpler and adequate | Architecture Patterns / Pattern 6 | If DB is preferred, add migration; JSON sidecar has no rollback; low risk |
| A2 | `model_maturity` stored in TimescaleDB table (not JSON) | Code Examples / Pattern 8 | JSON alternative is simpler but harder to query; low risk to change |
| A3 | Training runs offline on dev machine; `scikit-learn`/`skl2onnx` not in bridge Docker image | Environment Availability | If hub needs auto-retraining on-device, these must be in the image (+~300MB); verify with D-07 |
| A4 | Data maturity gate SQL uses `NULLIF(COUNT(*), 0)` for zero-division safety | Code Examples / Pattern 9 | Without NULLIF, gate crashes on empty zones; low risk with guard |
| A5 | opset 12 is sufficient for RandomForestClassifier and GradientBoostingClassifier via skl2onnx 1.20.0 | Standard Stack | If newer operators are needed, raise opset; unlikely to affect tree models |
| A6 | Hub hardware is ARM Linux (Raspberry Pi or similar); `onnxruntime` (CPU) package is the correct package | Standard Stack | If x86, same package works; if GPU, wrong package selected |
| A7 | The weekly retraining job (D-07) runs on the hub itself, not dev machine | Architecture Patterns | If retraining is always offline, the training dependencies can stay off the hub entirely |

**Note on A3 and A7:** D-07 specifies "a background job on the hub (APScheduler or cron) retrains models weekly." This implies scikit-learn and skl2onnx MUST be in the bridge Docker image. Research assumed offline training based on the note that training is CPU-intensive. The planner must resolve this contradiction: either install training deps in the hub image (accepting size cost) or clarify that D-07 means the job triggers an external training run. Until resolved, treat A3 as LOW confidence — include training deps in the image to match D-07.

---

## Open Questions

1. **Training on hub vs offline (D-07 resolution)**
   - What we know: D-07 says "a background job on the hub retrains models weekly" implying hub-side training
   - What's unclear: Hub hardware may not have enough RAM for scikit-learn GradientBoosting on 4+ weeks of sensor data (can be 100K+ rows per zone)
   - Recommendation: Spike (04-02) should benchmark training time AND peak RAM on actual hub hardware. If infeasible, D-07 should be updated to mean "hub triggers an external training job or downloads a pre-trained model."

2. **model_maturity persistence: DB table vs JSON sidecar**
   - What we know: DB table is queryable; JSON is simpler with no migration
   - What's unclear: Whether maturity state needs to survive bridge restarts (it does — recommendation counts accumulate over weeks)
   - Recommendation: Use DB table. Counts need to survive restarts. JSON sidecar would be cleared on container restart if the volume is not mounted correctly.

3. **Feature window sizes per domain**
   - What we know: Zone health and irrigation use soil moisture/pH/temperature; flock anomaly uses egg counts and expected production ratios
   - What's unclear: How many hours of lookback is needed for meaningful irrigation vs zone health patterns
   - Recommendation: 04-02 spike should benchmark with 6h, 12h, 24h windows. Start with 24h for zone health, 6h for flock anomaly (egg counts are daily).

4. **Confidence threshold for fallback-to-rules (Claude's Discretion)**
   - What we know: D-04 specifies "confidence is below threshold, fall back to rules"
   - What's unclear: RandomForest outputs class probabilities; GradientBoosting outputs decision function values. "Confidence" means different things per model type
   - Recommendation: For classification models, use max class probability as confidence. Set initial threshold at 0.65. Expose as `MIN_CONFIDENCE` env var so it can be tuned without a code change.

---

## Sources

### Primary (HIGH confidence)

- `pip3 index versions onnxruntime` — 1.23.2 current as of 2026-04-15
- `pip3 index versions scikit-learn` — 1.7.2 current as of 2026-04-15
- `pip3 index versions skl2onnx` — 1.20.0 current as of 2026-04-15
- `pip3 index versions apscheduler` — 3.11.2 current as of 2026-04-15
- `pip3 index versions watchdog` — 6.0.0 current as of 2026-04-15
- `pip3 index versions numpy` — 2.2.6 current as of 2026-04-15
- [CITED: onnxruntime.ai/docs/get-started/with-python.html] — InferenceSession API, CPUExecutionProvider
- [CITED: onnx.ai/sklearn-onnx/auto_examples/plot_convert_model.html] — convert_sklearn, FloatTensorType, to_onnx pattern
- [CITED: onnx.ai/sklearn-onnx/auto_tutorial/plot_cbegin_opset.html] — opset versioning, max supported opset 21
- [CITED: apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html] — AsyncIOScheduler API
- [CITED: docs.python.org/3.10/library/asyncio-eventloop.html] — get_event_loop deprecation in Python 3.10
- hub/bridge/rule_engine.py — existing recommendation dict shape (verified by direct read)
- hub/bridge/health_score.py — existing health score output shape (verified by direct read)
- hub/bridge/main.py — existing asyncio.gather() pattern and bridge architecture (verified by direct read)
- hub/bridge/models.py — existing Recommendation Pydantic model shape (verified by direct read)
- hub/dashboard/src/lib/types.ts — existing TypeScript Recommendation interface (verified by direct read)
- hub/dashboard/src/lib/ws.svelte.ts — existing WebSocket store pattern (verified by direct read)
- hub/dashboard/src/lib/HealthBadge.svelte — existing 11px badge CSS pattern (verified by direct read)
- hub/dashboard/src/routes/+page.svelte — Home tab layout for AIStatusCard insertion point (verified by direct read)

### Secondary (MEDIUM confidence)

- [CITED: pypi.org/project/watchdog/] — PatternMatchingEventHandler, Observer pattern
- WebSearch: APScheduler asyncio integration — AsyncIOScheduler is cooperative, does not block event loop
- WebSearch: scikit-learn tabular sensor anomaly — GradientBoosting preferred for clean tabular data; RandomForest robust for noisy sensor data

### Tertiary (LOW confidence — marked [ASSUMED])

- Data maturity gate SQL formulation (A4) — derived from TimescaleDB schema, not verified against live DB
- Training on hub vs offline (A3, A7) — contradiction in D-07 vs performance concerns; requires spike resolution

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all package versions verified against PyPI registry on research date
- Architecture: HIGH — derived directly from reading existing bridge/main.py, rule_engine.py, health_score.py, ws.svelte.ts
- ONNX inference patterns: HIGH — verified against official ONNX Runtime and skl2onnx documentation
- APScheduler integration: HIGH — verified against 3.x docs; version pinning is critical
- Pitfalls: HIGH for P1-P6, MEDIUM for P7-P8 (derived from known patterns, not project-specific)
- Synthetic data generator: MEDIUM — implementation details at discretion of implementer

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable ecosystem; main risk is a new APScheduler or onnxruntime release)
