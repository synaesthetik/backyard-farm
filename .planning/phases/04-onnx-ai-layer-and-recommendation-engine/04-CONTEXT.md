# Phase 4: ONNX AI Layer and Recommendation Engine - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

ML-backed ONNX models replace the rule-based recommendation engine for zone health scoring, irrigation schedule optimization, and flock production anomaly detection -- behind the exact same recommend-and-confirm UX delivered in Phase 2. A model maturity indicator manages farmer expectations during the cold-start period.

This phase delivers:
- Feature aggregation service (assembles sensor windows from TimescaleDB, GOOD-flag filter enforced)
- ONNX model selection spike (benchmark architectures on actual hub hardware)
- Zone health and irrigation ONNX models (training pipeline, export, hot-reload)
- Flock production anomaly ONNX model (training pipeline, export, integration)
- Inference scheduler (APScheduler) with event-triggered re-inference
- Model maturity indicator UI component on Home tab
- Synthetic data generator for bootstrapping the data maturity gate
- Dashboard settings toggle for ONNX/rules per domain
- Automated retraining with regression protection

Phase 4 does NOT deliver: pH calibration workflows or ntfy push notifications (Phase 5), hardware shopping list (Phase 6), or user tutorial (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Data Maturity Gate (AI-06)

- **D-01: Gate check is enforced in code.** The inference service queries TimescaleDB for the GOOD-flag ratio per zone. If any zone is below 80% GOOD-flagged readings over 4+ weeks, that zone's ONNX model is not activated. The gate is real and runtime-enforced.
- **D-02: Synthetic data fallback via CLI command.** A CLI script (e.g., `python scripts/generate_synthetic_data.py`) generates 6+ weeks of realistic sensor data and seeds TimescaleDB. This allows bootstrapping the gate in development or after a database reset.
- **D-03: Synthetic data must be realistic.** Seasonal VWC curves, temperature swings with diurnal cycles, pH drift, realistic sensor noise, occasional SUSPECT/BAD readings, daylight variation affecting egg production. The data must be good enough for ONNX models to learn meaningful patterns.

### Model Transition Strategy (AI-03)

- **D-04: ONNX is primary with rule-based fallback.** When ONNX models are loaded and the data maturity gate passes, ONNX drives recommendations. If the model is not loaded, confidence is below threshold, or the farmer toggles it off, the existing `RuleEngine` takes over automatically. No code removal -- both engines coexist.
- **D-05: Per-domain toggle on a dashboard settings page.** Three independent toggles: irrigation recommendations, zone health scoring, flock anomaly detection. Each can be set to "AI" or "Rules" independently. The farmer can flip back to rules from the yard if something feels off.
- **D-06: Toggle is runtime, no restart required.** The bridge reads toggle state from the hub (persisted in a config table or JSON file). Changing the toggle in the dashboard takes effect on the next inference cycle.

### Training Workflow

- **D-07: Automated retraining on a weekly schedule.** A background job on the hub (APScheduler or cron) retrains models weekly. Queries the latest GOOD-flagged sensor data from TimescaleDB, trains, exports to .onnx format. The farmer never manually triggers training.
- **D-08: Regression protection -- keep previous model as fallback.** After retraining, a validation check runs against a holdout set. If the new model scores worse than the current model, the previous .onnx file is kept. The models/ directory retains the last 2-3 versions. The farmer never sees a regression.
- **D-09: Hot-reload via filesystem watch.** The inference service watches the models/ directory. When a new .onnx file appears (and passes validation), it's loaded without restarting the bridge service.
- **D-10: Training uses only GOOD-quality-flagged data (AI-06 -- non-negotiable).** SUSPECT and BAD readings are excluded from both training datasets and live inference feature windows. This is enforced in the feature aggregation service, not as an optional filter.

### Cold Start Experience (AI-07)

- **D-11: Rule engine drives all recommendations during cold start.** Until models pass the maturity threshold, the existing threshold-based rule engine handles everything. The farmer's experience is unchanged from Phase 2/3.
- **D-12: AI Status card on the Home tab.** A dedicated card showing maturity progress per domain: irrigation, zone health, flock anomaly. Displays data collection progress (e.g., "3 weeks / 4 weeks needed"), recommendation count, and approval/rejection rate per type. The card is prominent during cold start and minimizes (or becomes less prominent) once all models are mature.
- **D-13: Model maturity indicator shows approval/rejection rate.** Per AI-07, the card displays how many recommendations have been generated and what percentage were approved vs rejected. This helps the farmer gauge whether the AI is learning their preferences.

### Claude's Discretion

- ONNX model architecture selection (random forest, gradient boosted, small neural net) -- the spike (04-02) determines this based on hub hardware benchmarks
- Feature window sizes for each domain (how many hours/days of sensor data per inference input)
- APScheduler configuration details (inference intervals: zone health 15min, irrigation 1hr, flock 30min per roadmap)
- Validation metric selection for regression protection (accuracy, F1, MAE depending on domain)
- Synthetic data generator implementation details (distributions, seasonal parameters)
- Model file naming convention and versioning scheme
- Threshold for "model confidence too low, fall back to rules"
- AI Status card visual design (progress bar style, layout within Home tab)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 Core
- `.planning/ROADMAP.md` -- Phase 4 goal, success criteria, 5 pre-defined plan slugs (04-01 through 04-05), DATA MATURITY GATE details, AI stack confirmation
- `.planning/REQUIREMENTS.md` -- Full requirement text for AI-03, AI-06, AI-07

### Prior Phase Decisions (carry forward)
- `.planning/phases/02-actuator-control-alerts-and-dashboard-v1/02-CONTEXT.md` -- Recommendation card UX (D-05 to D-08), alert engine patterns (D-09 to D-13), uPlot chart setup (D-31)
- `.planning/phases/03-flock-management-and-unified-dashboard/03-CONTEXT.md` -- Production model (D-06), feed consumption (D-12 to D-14), Home tab layout (D-15 to D-19)

### Existing Code (must read before planning)
- `hub/bridge/rule_engine.py` -- Threshold-based recommendation engine; ONNX must produce compatible output (recommendation dicts with same structure)
- `hub/bridge/alert_engine.py` -- Hysteresis-based alert engine; ONNX anomaly signals feed into this
- `hub/bridge/health_score.py` -- Zone health composite score; ONNX replaces this computation
- `hub/bridge/production_model.py` -- Expected egg production model; ONNX flock model augments/replaces anomaly detection
- `hub/bridge/models.py` -- Pydantic models for sensor payloads; feature aggregation builds on these
- `hub/bridge/main.py` -- Bridge pipeline; inference service integrates here
- `hub/api/recommendation_router.py` -- Recommendation approve/reject endpoints; no changes needed (same UX)
- `hub/dashboard/src/routes/+page.svelte` -- Home tab; AI Status card added here
- `hub/dashboard/src/lib/ws.svelte.ts` -- WebSocket store; extend for model maturity state

### Project Context
- `.planning/STATE.md` -- Current blockers, phase 4 data maturity gate notes
- `.planning/PROJECT.md` -- AI stack confirmation (ONNX Runtime, not Ollama)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RuleEngine` -- Stays as the fallback engine. ONNX inference service produces recommendation dicts in the same format so the downstream pipeline (deduplication, back-off, approve/reject) works unchanged.
- `AlertEngine` -- Extend to accept anomaly signals from ONNX models (same threshold-crossing + hysteresis pattern).
- `health_score.py` -- `compute_health_score()` is the function ONNX replaces for zone health. The ONNX model must return a compatible output shape (score + contributing_sensors).
- `production_model.py` -- Expected production calculation stays; ONNX adds anomaly detection on top of the existing model's output.
- `ws.svelte.ts` -- WebSocket store; extend with model maturity state fields for the AI Status card.
- `ZoneCard.svelte`, `FlockSummaryCard.svelte` -- No changes needed; they render whatever the backend sends.

### Established Patterns
- Hub-side computation: health scores, rule evaluation, alert evaluation all happen in the bridge process. ONNX inference follows the same pattern.
- Bridge internal HTTP server: the API process proxies to the bridge. Inference toggle state could flow through the same mechanism.
- APScheduler: not currently used but the roadmap specifies it for inference scheduling.
- Config via env vars: existing pattern for thresholds and timeouts. Toggle state adds a runtime-mutable config layer (dashboard settings).

### Integration Points
- `hub/bridge/main.py` -- Add inference service call in the evaluation pipeline (after rule engine, or instead of rule engine depending on toggle state)
- `hub/api/main.py` -- Mount new router for inference settings (toggle state, model maturity endpoint)
- `hub/dashboard/src/routes/+page.svelte` -- Add AI Status card to Home tab
- New `hub/inference/` directory -- ONNX model loading, inference runner, feature aggregation, training pipeline
- New `hub/models/` directory -- .onnx model files, versioned
- New `scripts/generate_synthetic_data.py` -- Synthetic data generator CLI

</code_context>

<specifics>
## Specific Ideas

- The farmer wants to feel in control of the AI -- the per-domain toggle is the key UX element. "Cut back to rules if ONNX feels flaky" is the core expectation.
- AI Status card on Home tab should feel informative, not intimidating. Progress toward maturity, not a wall of ML metrics.
- Synthetic data generator is a development tool but also useful for demos and testing after database resets.
- Automated weekly retraining means the system gets smarter over time without farmer intervention -- "set and forget" once models are mature.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 04-onnx-ai-layer-and-recommendation-engine*
*Context gathered: 2026-04-15*
