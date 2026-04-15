# Phase 4: ONNX AI Layer and Recommendation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 04-onnx-ai-layer-and-recommendation-engine
**Areas discussed:** Data maturity gate strategy, Model transition strategy, Training workflow, Cold start experience

---

## Data Maturity Gate Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic data generator | Build a script that generates realistic 6+ weeks of sensor data and seeds TimescaleDB | |
| Build assuming data exists | Skip gate enforcement in code, test with fixture datasets | |
| Gate check + synthetic fallback | Implement real gate check in code; if gate fails, offer CLI to generate synthetic seed data | ✓ |

**User's choice:** Gate check + synthetic fallback
**Notes:** None

### Follow-up: Synthetic data realism

| Option | Description | Selected |
|--------|-------------|----------|
| Realistic seasonal patterns | Seasonal VWC curves, temperature swings, pH drift, realistic noise, daylight variation | ✓ |
| Plausible but simple | Gaussian noise around targets, some random BAD flags, basic diurnal cycle | |
| You decide | Claude picks based on what ONNX models need | |

**User's choice:** Realistic seasonal patterns
**Notes:** None

---

## Model Transition Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Shadow mode then cutover | Both run in parallel, ONNX logged but rule engine drives, flip config to switch | |
| ONNX with rule-based fallback | ONNX primary, fall back to rules if confidence low or toggled off | ✓ |
| Hard cutover | Rule engine fully replaced when ONNX is ready, no parallel running | |

**User's choice:** ONNX with rule-based fallback
**Notes:** "I like the idea of being able to toggle back and forth. I want to be able to cut back over to a simple(r) rules engine if the ONNX things feel flaky"

### Follow-up: Toggle location

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard settings page | Toggle on UI settings page, per-domain toggles, flip from the yard | ✓ |
| Environment variable | Env var per domain, requires container restart | |
| Both -- env default, dashboard override | Env var sets boot default, dashboard overrides at runtime | |

**User's choice:** Dashboard settings page
**Notes:** None

---

## Training Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| CLI script on hub | Python CLI command on hub, queries TimescaleDB, trains and exports | |
| Export data, train elsewhere | Export data to CSV, train on more powerful machine, copy .onnx back | |
| Automated on hub with schedule | Background job retrains weekly, fully automated, farmer never thinks about it | ✓ |

**User's choice:** Automated on hub with schedule
**Notes:** None

### Follow-up: Regression protection

| Option | Description | Selected |
|--------|-------------|----------|
| Keep previous model as fallback | Validation check after retraining; if worse, keep previous .onnx; retain last 2-3 versions | ✓ |
| Always deploy latest | New model always replaces old; farmer notices via maturity indicator or flips toggle | |
| You decide | Claude picks based on what's practical for ONNX lifecycle on constrained hardware | |

**User's choice:** Keep previous model as fallback
**Notes:** None

---

## Cold Start Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Rules active + learning banner | Rule engine drives; subtle banner shows "AI is learning" until maturity threshold | |
| Maturity progress indicator | Visible progress bar/percentage showing data collection progress per domain | ✓ |
| Silent transition | Rule engine runs; models silently take over when ready; no UI indication | |

**User's choice:** Maturity progress indicator
**Notes:** None

### Follow-up: Indicator location

| Option | Description | Selected |
|--------|-------------|----------|
| AI settings page | On same settings page as ONNX/rules toggle; go look when curious | |
| Home tab card | Dedicated AI Status card on Home overview; visible on every open; minimizes once mature | ✓ |
| System health panel | Add to existing system health panel alongside node status | |

**User's choice:** Home tab card
**Notes:** None

---

## Claude's Discretion

- ONNX model architecture selection (determined by 04-02 spike)
- Feature window sizes per domain
- APScheduler configuration details
- Validation metric selection for regression protection
- Synthetic data generator implementation details
- Model file naming and versioning
- Confidence threshold for rule-based fallback
- AI Status card visual design

## Deferred Ideas

None -- discussion stayed within phase scope.
