# Feature Landscape

**Domain:** Backyard farm management — garden IoT + chicken flock
**Researched:** 2026-04-01
**Confidence note:** Web access unavailable during research. All findings are from training knowledge (cutoff August 2025). Platform-specific claims are MEDIUM confidence; sensor threshold and algorithm details are HIGH confidence from published research/standards. Verify against current platform docs before finalizing stack choices.

---

## Existing Platform Landscape

### FarmBot
**What it is:** CNC-style precision farming robot on a raised bed. Hardware-centric — the robot arm does physical planting, watering, and soil sensing.

**What it does well:**
- Visual sequence programming (drag-and-drop schedules)
- Per-plant grow data from the OpenFarm database (species, spacing, days to harvest)
- Soil moisture sensing at specific XY coordinates
- Scheduled watering with volume tracking
- Web app with satellite-style map view of the bed
- Open-source software stack (Rails API + React frontend)
- Lua scripting for custom automation sequences

**What it lacks / gaps:**
- Designed for one rectangular raised bed, not multi-zone irregular gardens
- No pH or nutrient sensor integration
- No AI-driven recommendations — schedules are static or threshold-triggered
- No flock management of any kind
- Cloud-dependent by default (FarmBot Cloud); self-hosted is possible but poorly documented
- No mobile PWA — web app is not well-optimized for phone in the field
- No cross-zone aggregation or zone-level health scoring

**Confidence:** MEDIUM (training data through 2025; FarmBot Web App is actively developed)

---

### Home Assistant (garden/irrigation integrations)
**What it is:** General home automation platform with irrigation and plant sensor integrations via community add-ons.

**What it does well:**
- Excellent hardware abstraction (Zigbee, Z-Wave, MQTT, WiFi sensors all first-class)
- Rachio, RainBird, OpenSprinkler integrations for irrigation scheduling
- Miflora / Xiaomi plant sensors (moisture, temperature, conductivity, illuminance)
- Automation engine (trigger: sensor threshold → action: turn on valve)
- Local-first by default; no required cloud
- Mobile app (Companion) with push notifications
- Dashboard (Lovelace) — highly customizable but requires manual config

**What it lacks / gaps:**
- No semantic plant knowledge — HA knows "soil moisture is 30%" but not "this plant needs 40-60%"
- No AI recommendation layer — automations are rules you write, not suggestions the system generates
- No flock management integrations exist (no chicken-specific entities or patterns)
- Dashboard requires significant config to look like a farm overview vs. a generic smart home
- No approve-before-execute workflow for actions — automations fire automatically
- No yield tracking or production logging
- Sensor history is there but trend analysis requires custom templates or external tools

**Confidence:** HIGH (HA is well-documented and stable; gaps are structural design choices)

---

### OpenFarm
**What it is:** Open-source crowdsourced plant grow guide database. Not an automation platform — a data source.

**What it provides:**
- ~10,000+ crop guides with structured data: watering frequency, soil pH range, temperature range, spacing, companion plants, pest/disease associations
- REST API (free, open)
- Growing stages with duration estimates
- Community-contributed tips per crop

**What it lacks / gaps:**
- No sensor integration — it's read-only reference data
- Grow guides are community-sourced and vary in quality; not always zone/climate-specific
- No API rate limits documented but service reliability is inconsistent for production use
- Data is not updated for specific cultivar variants (heirloom tomato vs. cherry tomato have same guide)

**Confidence:** MEDIUM (OpenFarm is actively maintained but quality varies by crop)

---

### Chickadee / BackyardChickens Community Tools
**What they are:** Hobbyist spreadsheet templates, forum tracking threads, simple mobile apps (CluckAR, Hentracker) for egg logging.

**What they do well:**
- Egg count logging per hen (when hens are individually tracked)
- Seasonal production pattern awareness (day-length driven)
- Feed cost tracking

**What they lack / gaps:**
- No sensor integration
- No automated health alerting — all manual observation
- No behavioral pattern analysis
- No integration with coop door automation
- Mobile apps are mostly standalone with no home-network API

**Confidence:** MEDIUM (based on community-tool landscape as of mid-2025)

---

### Coop Boss / Automatic Chicken Door controllers
**What they are:** Dedicated hardware/firmware for automatic coop doors (light-sensor or timer-based open/close).

**What they do well:**
- Reliable dawn/dusk triggering via ambient light or astronomical clock
- Manual override via app or button
- Safety sensors (detect obstruction before closing)

**What they lack / gaps:**
- Standalone devices with no API for external orchestration
- No feed/water integration
- No health alerting or egg tracking
- Status not surfaced to any dashboard

**Confidence:** MEDIUM

---

## Summary: Gaps in Existing Tools (Your Opportunities)

| Gap | Why It Matters | Difficulty |
|-----|---------------|------------|
| Multi-zone garden with per-zone plant-aware health scoring | FarmBot is single-bed; HA doesn't know plant requirements | Medium |
| Unified farm dashboard (garden + flock in one view) | No existing tool spans both domains | Medium |
| AI recommend-and-confirm workflow | No tool does suggestion + human approval before execution | High |
| Sensor-informed AI recommendations (not static rules) | All existing tools use static thresholds; ML models can adapt to plant stage, season, history | High |
| Local-only inference — no cloud dependency | FarmBot is cloud-first; HA can be local but AI add-ons usually require cloud APIs | High |
| Flock behavioral anomaly alerting | No automated behavioral baseline tracking exists in any hobbyist tool | Medium-High |
| Cross-domain alerts in one place | "Feed is low AND zone 3 needs water" in a single prioritized queue | Low-Medium |

---

## Table Stakes

Features users expect. Missing = product feels incomplete or unreliable.

### Garden / Irrigation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live sensor readings per zone (moisture, temp, pH) | Core data surface — without this it's just a timer | Low | Well-solved with standard MQTT/polling |
| Historical sensor graphs (7-day, 30-day) | Needed to spot trends and validate irrigation efficacy | Low | Standard time-series; use a lightweight TSDB |
| Threshold-based irrigation trigger | Foundational safety net even if AI is primary | Low | Must coexist with AI recommendations |
| Per-zone plant assignment | Required for any plant-aware logic | Low | Data model decision; must be in v1 |
| Irrigation on/off manual control from dashboard | "I need to water now" override | Low | Trivial valve actuator command |
| Irrigation history log (when ran, how long, zone) | Needed for debugging and AI training | Low | Append-only log table |
| Zone-level health status indicator | Summary view — is this zone OK, warn, or critical? | Medium | Derived from sensor composite score |
| Scheduled irrigation (time-of-day baseline) | Fallback when sensors fail or are offline | Low | Cron-like schedule |
| Sensor alert: moisture below threshold | Prevent crop death from missed irrigation | Low | Simple threshold alert |
| Sensor alert: temperature extreme (frost / heat stress) | Critical crop protection | Low | Simple threshold alert |

### Chicken Flock

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Coop door status (open/closed) with manual override | Safety visibility — are birds locked in/out? | Low | Binary sensor + actuator |
| Automated coop door (dawn/dusk or schedule) | Core automation everyone expects | Low | Astronomical clock well-solved |
| Daily egg count entry | Even manual entry is expected | Low | Simple form input |
| Egg production trend (weekly/monthly chart) | Is production normal for season? | Low | Chart over the log table |
| Feed level indicator + low alert | Actionable alert prevents birds going hungry | Medium | Depends on sensor choice (weight, float, ultrasonic) |
| Water level indicator + low alert | Same as feed — critical welfare | Medium | Same sensor challenge |
| Flock headcount (expected vs. observed) | Mortality detection requires knowing target count | Low | Manual input, checked against alerts |
| Alert: unexpected mortality | Urgent — bird death detected by headcount change or movement sensors | Medium | Requires some detection method |

### Cross-Domain / Dashboard

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single overview screen — all zones + flock | Core value prop of the whole platform | Medium | Layout design challenge more than engineering |
| Notification surface for urgent alerts | Low feed, health anomaly, frost warning — needs to surface loudly | Low-Medium | In-app + push via PWA |
| AI recommendation queue with approve/reject | Unique to this platform; core mechanic | High | See AI section below |
| Settings per zone (plant type, thresholds, schedule) | Required to configure the system | Low | Admin UI |
| System health status (which nodes are online) | Essential for a distributed system — "is my sensor even working?" | Medium | Heartbeat/watchdog per edge node |

---

## Differentiators

Features that set this platform apart. Not expected by default, but high value.

| Feature | Value Proposition | Complexity | V1 or Defer? |
|---------|-------------------|------------|--------------|
| AI irrigation recommendations driven by sensor trends + plant stage | "Zone 3 tomatoes are in week 4 of fruiting — reduce watering frequency 20%" | High | V1 (core differentiator) |
| Seasonal production model for egg yield | "Your flock of 15 hens should produce 8-10 eggs/day in April — you're at 4, investigate" | Medium | V1 |
| Recommend-and-confirm approval workflow | Fast approve/reject from dashboard or phone; AI learns from rejections | High | V1 (intentional design) |
| Per-rejection feedback loop ("why did you reject?") | Trains the model faster; adds transparency | Medium | Defer to V2 |
| Zone-to-zone comparison | "Zone 2 uses 30% more water than Zone 3 for similar plants — possible leak?" | Medium | Defer |
| Nutrient trend analysis (N/P/K over time) | Tells you when to add fertilizer based on depletion rate | High | Defer (nutrient sensors are expensive/unreliable) |
| Behavioral baseline for flock (movement patterns) | "Hens less active than usual in the morning — possible illness" | High | Defer (requires motion sensors or camera, V2) |
| Plant companion guidance at zone assignment | "You assigned basil next to tomatoes — good companion" | Low | Defer (OpenFarm data, nice-to-have) |
| Feed consumption rate tracking | Detect illness early ("feed consumption dropped 20%") | Medium | V1 if using weight-based sensor |
| Frost prediction alert with pre-emptive action suggestion | "Frost tonight — cover zone 2 or run frost protection" | Medium | Defer (requires weather integration or on-site temp forecasting) |
| Offline-first PWA with sync-on-reconnect | Works when home WiFi is spotty in the yard | Medium | V1 (essential for mobile in the field) |

---

## Anti-Features

Features to explicitly NOT build in V1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Fully autonomous irrigation execution | Undermines farmer trust; hard to debug | Recommend-and-confirm; autonomy tunable later |
| Cloud backup or remote access | Violates local-only constraint; adds infrastructure and privacy burden | Local network only; VPN is user's responsibility if desired |
| Computer vision / camera health detection | Complexity explosion; out of scope per PROJECT.md | Sensor-based approach; cameras deferred |
| Per-hen individual tracking with RFID | 10-25 hens tracked individually adds significant hardware cost/complexity | Flock-level tracking with anomaly detection |
| Market/yield financial analytics | Commercial-scale complexity; not the target user | Simple egg count log; no monetization layer |
| Push notifications via external service (Firebase, APNs) | Requires cloud account, violates local-only | Use Web Push via local service worker; or in-app alerts only |
| Real-time video streaming | Bandwidth, storage, and complexity; better served by a dedicated NVR | Planned as future V2 addition |
| Social / sharing features | Wrong product category | None |

---

## Sensor Thresholds and Alert Logic

Based on published soil science, agricultural extension guidelines (HIGH confidence), and common IoT garden implementations (MEDIUM confidence).

### Soil Moisture Thresholds

Most sensors report volumetric water content (VWC) as a percentage.

| Status | VWC Range | Action |
|--------|-----------|--------|
| Saturated (overwatered risk) | > 60% | Alert: possible overwatering or drainage issue |
| Field capacity (ideal) | 40-60% | No action |
| Adequate | 25-40% | Monitor; irrigation candidate |
| Stress threshold | 15-25% | Trigger irrigation recommendation |
| Wilting point (critical) | < 15% | Urgent alert; immediate irrigation |

**Implementation note:** These thresholds are plant-species-dependent. Sandy soils need a lower VWC target than clay soils. The AI layer needs soil type as a parameter, not just VWC. Per-zone soil type is a required configuration field.

### Soil pH Thresholds

| Status | pH Range | Action |
|--------|----------|--------|
| Highly acidic | < 5.5 | Alert; most vegetables struggle below 6.0 |
| Ideal for most vegetables | 6.0-7.0 | No action |
| Slightly alkaline | 7.0-7.5 | Monitor; nutrient lockout risk for some crops |
| Alkaline (problem) | > 7.5 | Alert; recommend soil amendment |

**Implementation note:** pH sensors in soil drift significantly over time (weeks). Calibration reminders are table stakes for a pH-aware system. Electrochemical pH sensors require calibration every 2-4 weeks minimum.

### Soil Temperature Thresholds

| Status | Temp (°C) | Action |
|--------|-----------|--------|
| Cold (germination blocked) | < 10°C | Alert: delay planting; germination unlikely |
| Cool (slow growth) | 10-15°C | Advisory: growth will be slow |
| Optimal (most crops) | 15-25°C | No action |
| Warm (heat-lovers fine) | 25-30°C | OK for peppers, tomatoes; alert for lettuce |
| Heat stress | > 30°C | Alert: shade cloth, increased watering |

### Alert Logic Patterns (IoT Best Practices)

**Debounce alerts (HIGH confidence):** A single sensor reading below threshold should not trigger an alert. Use a debounce window — e.g., 3 consecutive readings below threshold over 15 minutes. Prevents false alerts from sensor noise.

**Alert suppression after action (HIGH confidence):** Once an alert fires and an irrigation action is approved, suppress the moisture alert for a cool-down period (e.g., 4 hours) to prevent alert storm as water soaks in.

**Hysteresis bands (HIGH confidence):** Don't trigger irrigation at 24% VWC and stop at 25%. Use a band: trigger at 25%, stop at 45%. Without hysteresis, a system near threshold oscillates rapidly.

**Alert fatigue prevention (HIGH confidence):** Rank alerts by urgency. Combine: "Zone 2 and Zone 4 both need water" into one grouped notification, not two. Single-user farm dashboards especially suffer when the notification stream becomes noise.

**Dead sensor detection (HIGH confidence):** If a sensor reports the exact same value for N consecutive readings, flag it as potentially stuck/dead. Soil moisture should fluctuate at least slightly over hours.

---

## Irrigation Scheduling Algorithms

### 1. Fixed Threshold (Reactive)
**How it works:** If VWC < X, irrigate for Y minutes.
**Pros:** Simple, predictable, hardware-only viable.
**Cons:** Does not account for weather, plant stage, season, or actual evapotranspiration. Can overwater in cool weather.
**Use in this project:** As a fallback/safety net when AI is unavailable or edge node is offline.
**Confidence:** HIGH

### 2. Evapotranspiration (ET) Model
**How it works:** Calculate water lost to evaporation + plant transpiration using the Penman-Monteith equation. Irrigate to replace ET deficit. Requires: air temperature, humidity, wind speed, solar radiation, and crop coefficient (Kc) for each plant species at its current growth stage.
**Pros:** Scientifically grounded; used by USDA, commercial agriculture, Rachio smart sprinkler.
**Cons:** Requires weather station data (or local sensors for all 5 variables) and crop coefficient table per plant species. Complex to implement correctly.
**Use in this project:** Strong candidate for the AI recommendation layer if the hardware includes a weather station (temp, humidity, solar sensors). The crop coefficient table can come from OpenFarm + USDA extension data.
**Confidence:** HIGH (well-published; Penman-Monteith is the FAO-56 standard)

### 3. Sensor-Feedback (Closed-Loop)
**How it works:** Irrigate until VWC reaches target, not for a fixed duration. Uses real-time feedback during irrigation.
**Pros:** Adapts to actual soil conditions; prevents over/under watering.
**Cons:** Requires sensor readings during irrigation (some sensors drift when waterlogged). Irrigation must run until target reached, which can mean variable durations.
**Use in this project:** Viable for the recommend-and-confirm flow — the AI recommends "irrigate zone 3 to 50% VWC" and the system runs until that target is hit.
**Confidence:** HIGH

### 4. ML-Predicted (Predictive)
**How it works:** Train a model on historical sensor data (VWC over time), irrigation events, weather patterns. Predict when VWC will reach stress threshold and pre-emptively irrigate before it happens.
**Pros:** Proactive not reactive; can learn plant-specific patterns.
**Cons:** Requires sufficient historical data (typically 2-4 weeks of readings) before model is meaningful. Needs retraining when plant stage changes. Cold start problem.
**Use in this project:** Phase 2+ feature. Use threshold/ET in v1, collect data, train ML model once 4+ weeks of readings exist. LSTM or simple gradient-boosted regressor on time-series features.
**Confidence:** MEDIUM (pattern is well-known; specific model choice needs experimentation)

### Recommendation for V1
Use sensor-feedback (closed-loop) as primary with fixed-threshold fallback. Build the data collection infrastructure from day one so the ML model can be added in phase 2 with real data.

---

## Chicken Flock Management

### What Good Flock Management Software Tracks

**Production metrics (HIGH confidence — established poultry science):**
- Daily egg count (total, not per hen unless RFID tracked)
- Lay rate (eggs per day / hens in production) as a percentage
- Expected vs. actual production based on:
  - Flock size
  - Breed-specific peak lay rate (e.g., Leghorns ~300 eggs/year; dual-purpose breeds ~200/year)
  - Hen age (peak at 18-24 months; natural decline after year 2)
  - Day length (lay rate drops below 12-14 hours of daylight; supplemental lighting affects this)
  - Seasonal adjustment (spring peak, late-fall/winter trough)
- Cumulative yield (weekly, monthly, yearly totals)
- Days-since-last-significant-drop (alert trigger)

**Health indicators (MEDIUM confidence — from poultry veterinary literature):**
- Production drop > 20% from rolling 7-day average: investigate
- Complete cessation for 2+ days (individual hen): broody, ill, or injured
- Feed consumption drop (if weight-sensing available): early illness indicator
- Water consumption increase (may indicate heat stress or respiratory illness)
- Behavioral: reduced activity during normal active hours (if motion sensing available — V2)

**Egg production model — implementation approach:**
```
expected_daily_eggs = flock_size
                    * breed_lay_rate_pct     # config per flock
                    * age_factor             # polynomial decline after 24 months
                    * daylight_factor        # linear interpolation based on hours of light
                    * seasonal_coefficient   # learned from historical data or fixed table

alert if actual < expected * 0.75 for 3 consecutive days
```

**Confidence:** MEDIUM-HIGH. The model factors are well-established in poultry science; the specific implementation thresholds (0.75, 3 days) are reasonable starting points needing validation.

### Feed and Water Monitoring

| Sensor Type | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| Load cell (weight) | Continuous fill-level, consumption rate calculable | Requires waterproofing, tare drift | Best for feed; enables consumption tracking |
| Float switch | Dead-simple for water level | Binary (full/empty); no consumption rate | OK for water level alert only |
| Ultrasonic distance | No contact with material; measures volume | Interference from dust/feed dust | OK for large hoppers |
| Conductive probe | Cheap for water | Corrodes; binary levels only | Avoid |

**Recommendation:** Load cell under feed hopper (enables consumption rate, best health signal). Float switch or ultrasonic for water (binary low-alert is sufficient for V1).

**Confidence:** MEDIUM (sensor choice depends on hardware research; this is a reasonable starting point)

### Coop Door Logic

**Astronomical clock approach (HIGH confidence — used by most commercial coop doors):**
- Calculate sunrise/sunset for configured lat/long using a published algorithm (e.g., NOAA solar calculator — straightforward trigonometry, runs locally)
- Configurable offset: "open 30 minutes after sunrise", "close 45 minutes after sunset"
- Safety interlock: if door position sensor doesn't confirm open/closed within 30 seconds of command, alert
- Manual override from dashboard always takes precedence
- "Late night lockdown" check: if door is still open at configurable late hour (e.g., 10 PM), alert regardless of sunset calculation

**Edge case to handle:** DST transitions — use UTC internally, display local time in UI.

---

## AI and Recommendation Engine

### What "Local AI" Means for This Domain

This is not GPT-style language model inference. The AI layer for plant health and irrigation recommendations is primarily:

1. **Rule-based expert system** — encoded agronomic knowledge: "if tomato VWC < 30% AND soil temp > 25C AND plant is in fruiting stage, recommend irrigation"
2. **Statistical regression** — predict water need from recent VWC trend, ET estimate, plant stage
3. **Anomaly detection** — detect when sensor readings or flock production deviate from established baseline

Full LLM inference for recommendations is overkill and would struggle on edge hardware. A small ONNX model or even a well-tuned rule engine is more appropriate and explainable.

**Confidence:** HIGH (this matches current IoT/agricultural ML literature)

### Recommend-and-Confirm UX Requirements

This is the core interaction pattern — getting it right is more important than the ML sophistication.

**What makes it work (from smart home / industrial automation UX research — MEDIUM confidence):**
- Recommendation card shows: what action, which zone/area, why (sensor values that triggered it), and confidence level
- One-tap approve from the dashboard summary view — should not require navigation
- One-tap reject with optional reason (or no reason required)
- Pending recommendations expire: if not approved within a window (configurable, e.g., 2 hours), system re-evaluates and may re-issue
- Show history of past recommendations + outcomes — builds trust over time
- Batch approve: "approve all low-priority irrigation recommendations" — useful when you have 4 zones all needing water

**What kills the UX:**
- Too many recommendations (alert fatigue) — throttle to max 3 open recommendations at once
- Recommendations without explanation ("water zone 3" vs. "zone 3 VWC at 18%, below 25% threshold")
- No easy way to dismiss false positives — builds distrust in the system
- Slow approve → execute path — approval should trigger action within 5 seconds

### AI Learning from Feedback

**Minimum viable feedback loop (V1):**
- Log every recommendation with: sensor values at time of recommendation, recommendation type, user action (approved/rejected), timestamp
- Use rejection rate per recommendation type as a signal to tune thresholds
- After 50+ data points per recommendation type, offer threshold adjustment suggestions

**Deferred (V2+):**
- Reinforcement learning from approval patterns
- Natural language feedback on rejections
- Cross-user collaborative filtering (not applicable for single-user, but relevant if platform scales)

**Confidence:** MEDIUM (the feedback loop design is opinionated but grounded in common ML pipeline patterns)

---

## Notification and Alert Patterns

### Priority Tiers (HIGH confidence — standard alerting design)

| Tier | Type | Example | Delivery | Expiry |
|------|------|---------|---------|--------|
| P0 — Urgent | Safety/welfare | Coop door stuck, bird mortality detected, frost imminent | Full-screen banner + PWA push | Never auto-dismiss |
| P1 — Action required | Actionable degradation | Feed critically low, VWC at wilting point | Dashboard alert badge + push | Dismiss on action |
| P2 — Advisory | Monitoring needed | Feed getting low (not critical yet), mild pH drift | Dashboard notification list | Auto-dismiss after 24h |
| P3 — Informational | Status update | Irrigation completed, coop door opened successfully | Activity log only | Auto-expire 7 days |

### Single-User Farm Dashboard Alert Design

**Key insight:** A single-user system should optimize for glanceability, not volume. The dashboard should answer "is everything OK?" in under 3 seconds.

**Patterns that work:**
- Zone status grid: each zone shows a single color (green/yellow/red) plus the most critical metric
- Top-of-screen alert bar: only P0 and P1 alerts surfaced here; no more than 3 visible at once
- Alert grouping: "3 zones need water" not 3 separate water alerts
- Time-sensitive context: "Feed has been low for 6 hours" is more alarming than just "feed is low"
- Silence/snooze: some alerts (especially P2) need a "remind me in 2 hours" option

**Patterns that fail:**
- Notification list that grows unbounded — users stop reading it
- Alerts that fire multiple times for the same condition — immediately builds distrust
- Alerts with no suggested action — "what do I do about this?"

### PWA Push Notification Constraint

Since the platform is local-only, standard cloud-based push (Firebase Cloud Messaging, Apple APNs) is unavailable without a cloud intermediary. Options:

1. **In-app only** — alerts only visible when browser is open. Simple, but misses the point.
2. **Local Web Push** — browser supports Web Push API; can work over LAN if service worker is registered. Requires the browser to be open at least once and for service worker to be installed. Works for Android Chrome; iOS PWA push support has improved significantly (iOS 16.4+, full in iOS 17+).
3. **Home Assistant webhook** — if user already runs HA, send alerts there and let HA handle push. Optional integration.
4. **Gotify / ntfy** — self-hosted notification servers that work with PWA or phone apps. Good fit for local-only constraint.

**Recommendation:** Build in-app alerts first (V1). Integrate ntfy as optional self-hosted push backend (V1 or early V2). This avoids cloud dependency while providing real push.

**Confidence:** MEDIUM (iOS PWA push support has been evolving; ntfy recommendation is solid as of 2025)

---

## Feature Dependencies

```
Zone data model (plant type, soil type, zone config)
    → Threshold-based alerts
    → ET-based irrigation scheduling
    → AI plant health scoring

Sensor collection pipeline (MQTT / polling → TSDB)
    → Historical sensor graphs
    → Trend analysis
    → ML training data
    → Dead sensor detection

Irrigation actuator control
    → Manual override
    → Threshold-triggered irrigation
    → AI-recommended irrigation (requires actuator + approval flow)

Flock config (breed, age, flock size)
    → Expected egg production model
    → Production deviation alerts

Feed/water sensors
    → Feed/water level display
    → Low-level alerts
    → Consumption rate (if load cell)
    → Health inference from consumption drop

Recommendation queue (approve/reject UI)
    → All AI-driven actions
    → Feedback loop for model improvement

Edge node heartbeat / health check
    → All of the above (if nodes are offline, alerts about it)
```

---

## MVP Recommendation (V1 Scope)

### Must ship in V1

**Garden:**
1. Zone configuration with plant type and soil type
2. Live sensor readings (moisture, pH, temp) per zone
3. 7-day/30-day sensor history graphs
4. Threshold-based alerts (moisture, pH, temperature extremes)
5. Manual irrigation control from dashboard
6. Sensor-feedback irrigation (irrigate to target VWC) with AI recommendation + approval
7. Zone health status (composite green/yellow/red score)
8. pH calibration reminder

**Flock:**
9. Coop door control (automated dawn/dusk + manual override)
10. Coop door status with safety alert (door stuck)
11. Feed and water level monitoring with low alerts
12. Daily egg count entry form
13. Egg production chart (actual vs. expected)
14. Production drop alert (3-day rolling average deviation)

**Dashboard / Cross-domain:**
15. Single overview screen (all zones + flock)
16. P0/P1 alert bar with grouping
17. Recommendation queue (approve/reject with explanation)
18. System/node health status (which edge nodes are online)
19. Offline-capable PWA (service worker, works on phone in yard)

### Defer to V2

| Feature | Reason to Defer |
|---------|----------------|
| ML-predicted irrigation scheduling | Needs 4+ weeks of training data; build data pipeline first |
| Nutrient sensor integration | Sensors are unreliable and expensive; validate need first |
| Per-rejection feedback (reason tagging) | Adds friction; log implicit signal first |
| Behavioral anomaly detection (flock movement) | Requires additional hardware (motion sensors) |
| Zone-to-zone comparison analytics | Nice to have; not actionable until multi-zone data accumulates |
| Frost prediction with pre-emptive alerts | Requires weather integration or accurate local temp forecasting |
| Companion planting guidance | Low priority; OpenFarm integration is straightforward but not core |
| ntfy / push notification integration | In-app alerts sufficient for V1; add when pain is felt |
| Feed consumption rate trend (illness signal) | Requires 1+ week of baseline data; show rate in V1, alert in V2 |

---

## Features That Are Harder Than They Look

### 1. pH Sensor Reliability
**Issue:** Electrochemical pH probes in soil drift constantly. They need calibration every 2-4 weeks. A system that reports pH without managing calibration state will produce misleading data and false alerts within weeks.
**Mitigation:** Build calibration workflow into V1. Track last-calibration date. Alert when calibration is due. Allow manual pH entry as fallback.

### 2. ET-Based Irrigation at Hobby Scale
**Issue:** The Penman-Monteith equation requires 5 weather variables. Getting all of them accurately requires a real weather station (not just soil sensors). Most hobbyist setups only have temperature. Using simplified ET formulas (Hargreaves) with just min/max temp is possible but introduces error.
**Mitigation:** Use sensor-feedback as primary in V1. Collect weather variables if hardware allows; use ET as an enhancement to the recommendation rather than the primary signal.

### 3. Local Web Push on iOS
**Issue:** iOS PWA push notifications work as of iOS 16.4+ but require the PWA to be added to the home screen. Browser tab push doesn't work. Safari is the only engine on iOS.
**Mitigation:** In-app alerts are always available. Document the "add to home screen" requirement. Test on iOS early.

### 4. Astronomical Clock at High Latitudes
**Issue:** Above ~60° latitude or during summer, sunrise/sunset calculations can produce extreme values (sun doesn't set). Coop door logic breaks.
**Mitigation:** Add configurable hard limits: "never open before 5 AM, never close before 4 PM" regardless of astronomical calculation.

### 5. AI Learning Without Enough Data
**Issue:** If you advertise "AI learns from your approvals", users will expect improvement after 5 rejections. In reality, meaningful patterns need 50-100 data points per recommendation type. Cold start frustration is real.
**Mitigation:** Be transparent in the UI about model maturity ("Recommendations based on 12 approvals so far — learning in progress"). Use rule-based recommendations initially; flag when ML model is ready to take over.

### 6. Multi-Zone Valve Control Conflicts
**Issue:** If zones share a water pressure source (common in small gardens), running two zones simultaneously can reduce pressure enough that neither waters effectively.
**Mitigation:** Track valve open/closed state; enforce single-zone at a time unless user explicitly configures parallel zones as safe. AI must respect this constraint when batching recommendations.

### 7. Feed Sensor Tare Drift
**Issue:** Load cells under feeders drift over time (temperature, moisture, mechanical stress). Without periodic re-taring, the displayed feed level slowly becomes inaccurate.
**Mitigation:** Scheduled auto-tare reminder (or automatic tare at coop open time when feeder is presumably full). Alert when sensor reads negative.

---

## Sources and Confidence Summary

**HIGH confidence (published standards, well-established practices):**
- Soil VWC thresholds: USDA NRCS soil moisture guides, FAO Irrigation and Drainage Paper 56
- pH thresholds: University extension plant nutrition guides (Cornell, UC Davis, Penn State)
- Penman-Monteith ET calculation: FAO-56 (Food and Agriculture Organization standard)
- Alert debounce and hysteresis patterns: Standard IoT and SCADA engineering practice
- Poultry production decline thresholds: University of Georgia and Penn State Poultry Extension publications
- Coop door astronomical clock: NOAA Solar Calculator algorithm (public domain)

**MEDIUM confidence (training data as of August 2025; verify against current state):**
- FarmBot feature set: farm.bot, FarmBot GitHub (open source)
- Home Assistant garden integrations: home-assistant.io integration catalog
- OpenFarm data quality and API: openfarm.cc
- iOS PWA push notification support: Apple WebKit release notes
- ntfy as self-hosted push: ntfy.sh documentation
- Chicken management app landscape (CluckAR, Hentracker, etc.): App store research

**LOW confidence (flag for validation):**
- Specific ML model choices for irrigation prediction (LSTM vs. gradient boosting) — needs experimentation
- Nutrient sensor reliability — market has been evolving; verify current sensor options before committing
- FarmBot self-hosting status and documentation quality — actively changing project
