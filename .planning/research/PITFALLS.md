# Domain Pitfalls: Backyard Farm Edge IoT Platform

**Domain:** Distributed edge IoT — soil sensing, irrigation automation, coop automation, local AI inference
**Researched:** 2026-04-01
**Confidence:** MEDIUM — WebSearch unavailable; based on embedded systems engineering knowledge, agricultural IoT community patterns, and Raspberry Pi/ESP32 operational experience through training cutoff. Flags below note where live verification would strengthen claims.
**Note:** No external search tools available during this research pass. Findings draw on well-established hardware failure modes, community-documented patterns (r/homeautomation, r/raspberry_pi, Home Assistant community, agricultural IoT literature), and embedded systems engineering practice. Confidence is MEDIUM rather than HIGH because specific product version gotchas and 2025-era firmware changes could not be verified.

---

## Architectural Decision Flags

These pitfalls are severe enough to drive architecture — they are surfaced first.

### FLAG-1: Coop door failure mode requires hardware-level failsafe
**Severity:** CRITICAL
**Decision required:** The coop door controller must have a hardware-enforced safe state independent of software. A software-only door controller can trap birds outside at dusk (predator kill) or leave the door open at dawn (predator entry after birds emerge). This is not recoverable — it is a single-night mortality event. The door actuator must fail to a defined safe state (closed) via a physical limit switch or motor driver with no-power default, not just software logic.

### FLAG-2: Runaway irrigation requires physical failsafe, not just software interlock
**Severity:** HIGH
**Decision required:** A software bug, corrupted sensor value, or node crash during an open-valve command leaves a valve stuck open until someone notices. For a self-hosted system with a single operator who may be away, this is a serious flood risk. Each irrigation zone valve must be a normally-closed (NC) solenoid valve — safe state is closed when power is removed. The software interlock (max duration per zone, simultaneous zone limit) is a second layer, not the primary.

### FLAG-3: SD card corruption kills a Pi node silently
**Severity:** HIGH
**Decision required:** Raspberry Pi nodes running off SD cards will eventually experience card corruption under write-heavy logging workloads — especially when powered off mid-write during outages. The architecture must treat each edge node as ephemeral and stateless: no critical state lives only on an edge node's SD card. All configuration, calibration offsets, and historical data must be pushed to the central hub immediately.

### FLAG-4: Time sync across nodes is not guaranteed without special handling
**Severity:** MEDIUM
**Decision required:** Local-only systems have no NTP unless the central hub runs an NTP server or all nodes sync to one source. Nodes that drift in time produce sensor data with wrong timestamps, which corrupts time-series analysis and AI training. The hub must be the authoritative time source and all nodes must sync from it at boot and periodically.

---

## Critical Pitfalls

Mistakes in this category cause animal death, hardware loss, or data corruption that requires full rebuild.

### Pitfall C-1: Coop Door Traps Birds or Leaves Entry Open

**Category:** Chicken coop automation
**Build-time vs. operational:** Build-time (must be designed in from the start)
**Likelihood:** HIGH (every coop automation community thread has examples of this)
**Severity:** CRITICAL

**What goes wrong:**
- Node crashes mid-close, door stops at partial position — predator-accessible gap.
- Clock drift or DST/timezone bug causes door to trigger 1 hour late — birds roost outside.
- Sensor-based close (light level) triggers early on a cloudy afternoon — birds locked out before roosting.
- Power interruption during close cycle leaves door stopped mid-travel.
- Software update restarts the coop node at dusk — door command never executes.

**Why it happens:**
Single-point software control with no physical position feedback and no independent watchdog.

**Consequences:**
One predator incursion at night kills an entire flock. A single trapped night in cold/wet weather kills birds. These events are irreversible.

**Prevention (required, not optional):**
1. Use a linear actuator or motor with physical limit switches at fully-open and fully-closed positions. The controller must read these switches to confirm the door reached its target state, not just assume the command succeeded.
2. Motor driver must cut power when limit switch is hit — prevents motor burnout from driving against a hard stop.
3. Default/no-power state must be closed. If the actuator is spring-loaded or gravity-assisted to closed, a power failure is safe.
4. Implement a watchdog: after issuing close command, poll the closed limit switch for up to 60 seconds. If not confirmed closed, trigger an alert and retry. If still not confirmed, alert loudly and continuously.
5. Use schedule-only (not light-sensor-only) as primary close trigger — light sensors fail (dirty lens, spider web). Schedule is predictable; light level is not. Light sensor can be a secondary confirmation check.
6. Log every door open/close event with confirmation status. Alert if any event is unconfirmed.

**Detection:**
Door close confirmation alert not received by hub within expected window. Implement a daily "door status at 30 minutes past sunset" check in the hub.

**Architecture implication:** See FLAG-1 above. Physical limit switches and hardware failsafe are non-negotiable.

---

### Pitfall C-2: Irrigation Runaway from Bad Sensor Read

**Category:** Irrigation automation
**Build-time vs. operational:** Build-time
**Likelihood:** MEDIUM (any moisture sensor can fail open/short)
**Severity:** HIGH

**What goes wrong:**
- Moisture sensor fails low (reads "bone dry") while soil is saturated — system waters indefinitely.
- Sensor wire corrodes, reads 0% moisture constantly — continuous watering.
- Software crash during open-valve command: valve stays open, no close command is ever sent.
- Node reboots with a valve open — relay defaults to open on cold boot if relay logic is not verified.

**Prevention:**
1. Normally-closed solenoid valves everywhere (see FLAG-2). Power-off = valve closed.
2. Maximum per-zone runtime hardcoded in firmware, independent of software: a watchdog timer in the edge node firmware cuts power to the relay after N minutes regardless of what the software says. N should be 2-3x the longest legitimate irrigation run (e.g., 30 minutes maximum if longest zone is 10 minutes).
3. Validate sensor readings before acting: a moisture reading of exactly 0 or exactly 100 from a digital sensor is highly suspicious — treat as a sensor error, not a valid reading. Require 3 consecutive anomalous readings before triggering any action.
4. Rate-limit irrigation events per zone per day. Flag unusual frequency for human review before executing.
5. Cross-check: if soil moisture reads 0% one hour after watering completed, that is suspicious — raise an alert rather than immediately watering again.
6. On relay boards with active-low control (common on Pi relay HATs), the relay is ENERGIZED (valve open) when GPIO is LOW. Pi GPIO defaults to input/floating on cold boot, which can momentarily pull the relay closed before software initializes. Test this explicitly during hardware bring-up and add a pull-up or explicit GPIO initialization sequence.

**Detection:**
Abnormally high water usage (if you have a flow meter — worth adding), zone runtime exceeding expected maximum, moisture reading not increasing after a completed watering cycle.

---

### Pitfall C-3: SD Card Corruption Kills Pi Node

**Category:** Hardware reliability / self-hosted maintenance
**Build-time vs. operational:** Build-time (architecture), Operational (ongoing)
**Likelihood:** HIGH (SD cards under continuous write load in uncontrolled power environments fail — this is a near-certainty over 1-2 years, not a possibility)
**Severity:** HIGH

**What goes wrong:**
- Power outage interrupts a write to the SD card filesystem — ext4 journal may not recover fully.
- Continuous sensor logging at 1Hz to a SQLite or flat file wears out SD card write cycles (consumer SD cards: ~10,000 P/E cycles on MLC NAND).
- Node comes back up in read-only filesystem mode after corruption — logs silently stop being written, but the node appears operational.
- Calibration data stored only on the node is lost — sensor readings become inaccurate until manually recalibrated.

**Prevention:**
1. Never store authoritative data on the edge node SD card. Edge nodes are data collectors and actuators, not data stores. All readings must be forwarded to the hub within seconds and acknowledged before the local copy can be discarded.
2. Use a read-only root filesystem on edge nodes. Mount `/tmp` and log directories as tmpfs. All persistent data goes to the hub via the local network. This eliminates filesystem corruption from power loss.
3. If read-only rootfs is too complex initially, at minimum: use a high-endurance SD card (Samsung Pro Endurance, SanDisk Max Endurance — rated 100x more P/E cycles than standard cards), and use log rotation with a small ring buffer on the node.
4. Use a UPS or supercapacitor power supply on the hub (which is the critical node). Edge nodes failing is acceptable — the hub losing power should trigger a graceful shutdown.
5. Implement periodic node health checks from the hub: if a node goes silent, alert within 5 minutes.
6. Design for fast node recovery: the node must be able to re-image and reconfigure itself from the hub with no manual steps beyond physical re-insertion. Store all node configuration on the hub.

**Detection:**
Node stops sending data, filesystem mounts as read-only (check `/proc/mounts`), systemd journal shows I/O errors.

---

### Pitfall C-4: Relay Behavior on Active-Low Boards During Boot

**Category:** Hardware reliability
**Build-time vs. operational:** Build-time
**Likelihood:** HIGH (extremely common on Pi relay HAT designs)
**Severity:** HIGH

**What goes wrong:**
Many Pi relay HATs (especially cheap ones from Amazon/AliExpress) use active-low logic: the relay triggers when the GPIO is LOW. GPIO pins default to INPUT (high-impedance) on Pi boot. A floating or pulled-low GPIO during the ~2-5 seconds before the application initializes the GPIO direction can energize the relay — opening valves or triggering actuators momentarily at every boot.

**Prevention:**
1. Test every relay board before deployment: what state does each relay default to at power-on, before any GPIO configuration? Document it.
2. Prefer relay boards with explicit enable pins or that default to OFF (normally-open, deactivated) at cold boot.
3. Add a GPIO initialization service that runs very early in the boot sequence (before the main application) and explicitly drives all relay pins HIGH (deactivated) with the correct direction set.
4. For irrigation valves, the NC solenoid valve mitigation covers this — even if the relay momentarily activates, a normally-closed valve requires sustained power to stay open.

---

## High Severity Pitfalls

### Pitfall H-1: Soil pH Sensor Calibration Drift

**Category:** Soil sensor accuracy
**Build-time vs. operational:** Primarily operational
**Likelihood:** HIGH (all analog pH sensors drift; digital ones with glass electrodes also drift)
**Severity:** HIGH (bad pH reads → wrong AI recommendations → wrong amendments applied → damaged plants)

**What goes wrong:**
- Glass-membrane pH electrodes drift ~0.1-0.3 pH/month under soil conditions, faster in fluctuating temperatures.
- Reference junction clogs with soil particles, causing sluggish or stuck readings.
- Storage in dry air desiccates the glass membrane — a pH probe stored dry even briefly may read incorrectly for hours or permanently.
- Cheaper analog pH probes (common in hobby kits) degrade to ±1.0 pH accuracy within a few months, making them unsuitable for precision soil management.
- Temperature affects pH readings: a 10°C temperature change shifts reading by ~0.05 pH per pH unit from 7.0. Without temperature compensation, readings are meaningless for soil that has large temperature swings.

**Prevention:**
1. Use pH probes with ATC (Automatic Temperature Compensation) built in, or pair every pH sensor with a soil temperature sensor and apply temperature compensation in software.
2. Calibrate on a schedule: two-point calibration (pH 4.0 and pH 7.0 buffer solutions) at least monthly, more frequently in the first month of deployment. Log calibration offsets with timestamps.
3. Store probes in storage solution (KCl 3M) or pH 7.0 buffer between measurements if doing point-in-time readings rather than continuous monitoring.
4. Consider whether continuous in-soil pH monitoring is actually necessary. For a backyard garden, weekly or bi-weekly point measurements with a handheld probe may be more accurate and lower maintenance than a deployed sensor that drifts. The AI recommendation system can work well with less-frequent but high-quality pH data.
5. Validate readings: pH outside 3.0-9.5 is almost certainly a sensor fault, not a real soil reading. Flag and discard.
6. Industrial-grade solid-state pH sensors (e.g., ISFET-based) drift less and survive soil deployment better but cost significantly more (~$50-150 vs. $10-30 for glass electrode types).

**Architecture implication:** The data ingestion pipeline must have a validation layer that flags pH readings as "calibration required" when drift exceeds a threshold (compare reading against running baseline — a 0.3 pH jump in 24 hours with no amendments is a sensor event, not a soil event).

---

### Pitfall H-2: Capacitive Soil Moisture Sensor Variance

**Category:** Soil sensor accuracy
**Build-time vs. operational:** Build-time + operational
**Likelihood:** HIGH (affects all capacitive sensors — the dominant type for hobby use)
**Severity:** MEDIUM-HIGH

**What goes wrong:**
- Capacitive moisture sensors read the dielectric constant of the surrounding soil, which varies not just with water content but with soil type, temperature, compaction, and salt concentration. A reading of "450" on one sensor in clay soil is not the same as "450" on another sensor in sandy loam.
- Factory calibration is meaningless for any specific soil. Each sensor must be calibrated in-situ: dry calibration (oven-dry soil sample) and wet calibration (saturated soil sample) for each deployment location.
- Different sensor batches from the same manufacturer can have different raw output ranges — a batch of "v1.2" sensors is not interchangeable with "v2.0" without recalibration.
- Sensor exposed to air reads differently than sensor in soil — calibration in a cup of water is wrong.
- Temperature affects dielectric constant of water: readings drift with soil temperature even at constant moisture.

**Prevention:**
1. Store per-sensor calibration coefficients (dry_value, wet_value, temperature_coefficient) keyed to sensor_id and zone_id. Never use raw ADC values — always convert to volumetric water content percentage using per-sensor calibration.
2. Calibrate in the actual soil of each zone. Mark the location. Do not move a calibrated sensor.
3. Use soil temperature readings to apply temperature correction to moisture readings.
4. Treat moisture readings as a trend signal, not an absolute value. "Moisture is dropping" is reliable. "Moisture is exactly 32%" is not. Design AI recommendations around trend and threshold rather than absolute targets.
5. Cross-check moisture sensor readings against precipitation data (even a simple rain gauge or rain sensor) and irrigation history. A moisture reading that doesn't increase after a known irrigation cycle indicates a sensor problem.

---

### Pitfall H-3: AI Model Inference Latency vs. Real-Time Sensor Needs

**Category:** AI on constrained hardware
**Build-time vs. operational:** Build-time
**Likelihood:** MEDIUM (depends heavily on model size choices)
**Severity:** MEDIUM-HIGH

**What goes wrong:**
- LLM-style inference (even small models like Llama 3.2 1B) on a Pi 4 takes 10-60 seconds per query depending on model size and quantization. This is fine for batch recommendations but incompatible with real-time sensor response loops.
- A model loaded into RAM for continuous inference competes with the OS, sensor collection daemons, and other processes — memory pressure causes swap, which thrashes the SD card and causes both the AI and the sensor collection to degrade simultaneously.
- ONNX or TinyML inference for a simple classification model can run in <100ms on a Pi 4, but requires model selection and quantization decisions at build time that are hard to change later.
- Running inference on every sensor reading at 1Hz is computationally wasteful and will thermal-throttle a Pi 4 in an outdoor enclosure within minutes.

**Prevention:**
1. Separate inference from sensor collection: sensor nodes collect and forward data continuously; inference runs on the central hub (not on zone edge nodes) on a scheduled basis (every 15-30 minutes for recommendations, not per reading).
2. Sensor-triggered alerts (moisture below threshold, door not closed) must be evaluated by simple rule-based logic in the sensor collection service, not by the AI model. The AI is for recommendations; the rules are for alerts. Never let an alert depend on AI inference completing.
3. Choose model architecture for the job: time-series anomaly detection and irrigation recommendations do not require an LLM. A small ONNX model (random forest, gradient boosted trees, or a tiny neural network) running via ONNX Runtime will be 100-1000x faster than an LLM for structured sensor data.
4. If an LLM is used for natural-language recommendation summaries, run it in a low-priority background queue. It must never block sensor collection or alert evaluation.
5. Profile inference time on the actual target hardware before committing to a model. A model that takes 2 seconds on a developer's M2 MacBook may take 45 seconds on a Pi 4 in a hot outdoor enclosure.

---

### Pitfall H-4: Thermal Throttling of Edge Nodes in Outdoor Enclosures

**Category:** AI on constrained hardware / Hardware reliability
**Build-time vs. operational:** Build-time (enclosure design)
**Likelihood:** HIGH (extremely common oversight in outdoor Pi deployments)
**Severity:** HIGH

**What goes wrong:**
- Raspberry Pi 4 throttles CPU at 80°C, hard-shuts down at 85°C. Ambient summer temperatures in a sealed weatherproof enclosure can reach 60-70°C in direct sun — the Pi reaches shutdown temperature within an hour.
- Throttling degrades AI inference performance dramatically (can be 4-8x slower at 60% throttle vs. full speed).
- Thermal cycling (cool night / hot day) stresses solder joints and accelerates connector corrosion.
- CPU-intensive tasks (inference, compression, firmware update processing) spike heat at times that may coincide with critical sensor collection windows.

**Prevention:**
1. Never put a Pi in a sealed waterproof box in direct sun without active thermal management. Options in order of preference: shade the enclosure, use a ventilated enclosure with IP-rated louvered vents, add a small heatsink + fan inside the enclosure.
2. Use an aluminum enclosure rather than plastic — it acts as a heatsink.
3. Mount enclosures on north-facing walls or in permanent shade where possible.
4. Monitor CPU temperature continuously on all Pi nodes (`/sys/class/thermal/thermal_zone0/temp`). Alert before throttling starts (e.g., alert at 70°C on a Pi 4).
5. Schedule compute-intensive tasks (inference batch runs, log compression, OTA updates) during cooler overnight hours.
6. ESP32 handles heat better (operating range up to 85°C ambient) and is a better choice for sensor collection nodes that don't need inference — reserve Pi hardware for the hub.

---

### Pitfall H-5: Power Outage Leaves System in Undefined State

**Category:** Hardware reliability
**Build-time vs. operational:** Build-time
**Likelihood:** MEDIUM (depends on location power reliability)
**Severity:** HIGH

**What goes wrong:**
- Power goes out at dusk — coop door command never fires, birds are outside all night.
- Power goes out mid-irrigation cycle — valve state unknown on recovery.
- Hub loses power — no data aggregation, no alerting during outage.
- Nodes come back in different orders after power restore — race conditions in initialization cause incorrect initial state.

**Prevention:**
1. Hub should have a UPS (uninterruptible power supply). Even a small 600VA UPS provides 30-60 minutes of runtime for a Pi-based hub — enough to ride out most short outages and execute a clean shutdown.
2. On power restore, every node must report its current actuator state before the hub resumes automated control. Implement a "check-in and report state" boot sequence on every node.
3. The coop door node specifically: on power restore, read the limit switches immediately. If door is in unknown/partial state, treat as an emergency — alert immediately, do not attempt autonomous correction, require human confirmation.
4. For irrigation: on power restore, all valves must confirm closed state before any new irrigation commands are issued.
5. Track "last known safe state" in hub persistent storage. On outage recovery, compare current reported state to last known safe state and flag discrepancies.

---

### Pitfall H-6: Node Fails Silently — No Data Is Not Obviously Wrong

**Category:** Data quality / Self-hosted maintenance
**Build-time vs. operational:** Build-time
**Likelihood:** HIGH (without explicit monitoring, silent failures are invisible)
**Severity:** HIGH

**What goes wrong:**
- A node's network interface hangs — it appears to be running but sends no data. The hub's last reading is hours stale.
- A sensor is physically damaged (wire chewed by an animal, connector corroded) but returns a plausible-looking constant value, not an obvious error.
- An irrigation valve relay board fails with relay stuck open (welded contacts from inrush current on a failed solenoid) — software thinks the valve closed, it hasn't.
- All of these are invisible unless the system explicitly monitors for "no data is suspicious."

**Prevention:**
1. Implement heartbeat monitoring: every node sends a heartbeat message every 60 seconds. Hub alerts if any node misses 3 consecutive heartbeats (~3 minutes of silence).
2. Implement data freshness checks in the UI: every sensor value displayed must show its timestamp. A reading older than 5 minutes should be visually flagged as stale, not shown as current.
3. Implement static reading detection: if a sensor returns the same value (to 2 decimal places) for more than 30 consecutive readings, flag as "sensor may be stuck." True soil moisture and temperature have natural variation; a perfectly static reading is suspicious.
4. For irrigation valves specifically: use normally-closed solenoids (fail safe) and consider adding a low-cost flow sensor on the main water line to detect flow when all valves should be closed (stuck open detection) or no flow when a valve should be open (stuck closed detection).
5. Make silent failures loud: "Zone 3 sensor has not reported in 10 minutes" is more actionable than no alert at all.

---

## Moderate Pitfalls

### Pitfall M-1: NTP / Time Sync Across Offline Nodes

**Category:** Data quality
**Build-time vs. operational:** Build-time
**Likelihood:** HIGH (all Linux systems on isolated LAN without NTP drift)
**Severity:** MEDIUM

**What goes wrong:**
Without an NTP source, each Pi's system clock drifts independently. After a week, nodes may differ by minutes. After a month, by tens of minutes. Time-series data from different nodes stitched together in the hub has timestamps that don't align — AI training and anomaly detection across zones is corrupted.

**Prevention:**
1. Run `chrony` or `ntpd` on the hub configured as an NTP server for the LAN. All edge nodes sync from the hub.
2. If the hub has internet access (even intermittently), configure the hub to sync from a public NTP pool upstream and serve local time to nodes.
3. On each node, enable `systemd-timesyncd` pointing to the hub's IP. Ensure it starts before any data collection service.
4. Store timestamps in UTC everywhere. Handle timezone display only in the UI layer. This eliminates DST transition bugs in door schedules and log queries.
5. For the coop door specifically: the door schedule must tolerate ±5 minutes of time uncertainty without being dangerous. Build in a grace window on the open/close schedule to accommodate a node that has drifted slightly before syncing.

---

### Pitfall M-2: EC/Nutrient Probe Maintenance Neglect

**Category:** Soil sensor accuracy
**Build-time vs. operational:** Operational
**Likelihood:** HIGH (neglected EC probes are universal)
**Severity:** MEDIUM

**What goes wrong:**
Electrical conductivity (EC) probes measure soil salinity/nutrient concentration by passing current between two electrodes. Over weeks in soil:
- Electrodes corrode or acquire mineral deposits (scale), increasing apparent resistance, causing low-biased EC readings.
- Soil particles compact between electrodes, creating a persistent conductive or insulating bridge.
- Exposed metal electrodes oxidize in moist soil — graphite or stainless electrodes last longer but not indefinitely.

**Prevention:**
1. Use probes with graphite or platinum electrodes rather than bare copper/steel for in-soil continuous deployment.
2. Schedule quarterly probe cleaning: remove from soil, clean with dilute acid (vinegar) or probe cleaner, rinse, re-calibrate with standard EC solutions.
3. Log calibration dates and alert when a probe has not been calibrated in >90 days.
4. Validate EC readings: EC in productive garden soil is typically 0.5-3.0 mS/cm. A reading outside 0.1-5.0 mS/cm is likely a sensor fault.
5. Like pH, consider whether continuous deployment is necessary vs. periodic point measurement — the maintenance burden is lower for a probe you insert when needed rather than one buried for months.

---

### Pitfall M-3: Simultaneous Zone Watering Overloads Supply Pressure

**Category:** Irrigation automation
**Build-time vs. operational:** Build-time
**Likelihood:** MEDIUM (depends on supply line sizing)
**Severity:** MEDIUM

**What goes wrong:**
If two or more irrigation zones fire simultaneously (software bug, race condition in zone scheduling, or manual trigger while automated trigger fires), the combined flow may exceed the water supply's capacity — pressure drops enough that none of the zones water effectively, or the pressure drop activates a pressure relief valve or damages drip emitters.

**Prevention:**
1. Enforce a single-zone-active invariant in the hub's irrigation controller. This is a state machine concern: the hub tracks the global valve state and rejects any open-valve command that would result in more than one zone active simultaneously (or whatever the safe maximum is for the specific supply line).
2. The invariant must be enforced even if the command arrives from the local UI and an automated schedule simultaneously. Use a mutex or serialized command queue, not concurrent command processing.
3. Optionally: add a flow sensor on the main line to detect unexpectedly high flow and automatically trigger an emergency close-all command.

---

### Pitfall M-4: Coop Environment Kills Sensors Fast

**Category:** Chicken coop automation
**Build-time vs. operational:** Build-time + operational
**Likelihood:** HIGH (chicken coops are extremely harsh sensor environments)
**Severity:** MEDIUM

**What goes wrong:**
Chicken coops combine: ammonia from manure (corrodes copper, attacks sensor plastics), fine particulate dust (clogs sensors, coats optical sensors), high humidity (condenses on electronics), and frequent temperature swings. Sensors that work for months in a garden will fail in weeks in a coop.

**Prevention:**
1. Use conformal-coated PCBs for any electronics inside the coop enclosure. Apply conformal coating spray after assembly to any custom boards.
2. For the humidity/temperature sensor, use an IP65+ rated probe with the sensor element behind a sintered filter — the filter keeps dust out while allowing air exchange.
3. Enclose all electronics in an IP65 box inside the coop. Run only sensor probes and wiring outside the box.
4. Use optical beam sensors for feed/water level detection rather than contact sensors — less surface area exposed to the environment.
5. Plan for quarterly sensor cleaning and annual sensor replacement in the coop as routine maintenance, not exceptional events. Budget for it.
6. Avoid any sensor that uses an exposed metal contact (resistance-based water level sensors, bare EC probes) inside the coop — ammonia attacks them aggressively.

---

### Pitfall M-5: AI Training Data Poisoned by Outliers

**Category:** Data quality / AI on constrained hardware
**Build-time vs. operational:** Build-time (pipeline design)
**Likelihood:** MEDIUM
**Severity:** MEDIUM

**What goes wrong:**
Sensor faults, calibration events, and network gaps produce readings that are statistically real (stored in the database) but physically wrong. If these are fed into AI model training without filtering, the model learns incorrect patterns — e.g., it learns that "pH 1.5 for 10 minutes" is a normal soil state and weights recommendations accordingly.

**Prevention:**
1. Never train on raw sensor data. Always train on a validated dataset view that has had outliers flagged and removed. The outlier flagging pipeline (physiologically plausible range checks, inter-reading rate-of-change limits, cross-sensor consistency checks) must exist before any AI training begins.
2. Tag every sensor reading with a quality flag at ingestion time: `GOOD`, `SUSPECT` (outside expected range but not impossible), `BAD` (physically impossible or from a sensor in fault state). AI training uses only `GOOD` readings.
3. When a calibration event occurs (probe recalibrated, sensor replaced), mark all readings from that sensor in the preceding 48 hours as `SUSPECT` — the probe may have been drifting before the fault was detected.
4. Retain raw readings (never discard them) but train only on quality-flagged subsets. This allows reprocessing with better quality filters later.

---

### Pitfall M-6: System Updates Break Working Configuration

**Category:** Self-hosted maintenance
**Build-time vs. operational:** Operational
**Likelihood:** HIGH (every self-hosted system that auto-updates eventually breaks)
**Severity:** MEDIUM

**What goes wrong:**
- A Node.js/Python package update breaks a sensor driver module — nodes stop reporting silently.
- A kernel update changes GPIO device naming — actuator control breaks.
- A Docker update changes networking behavior — nodes can no longer reach the hub.
- OS security patches break I2C or SPI device tree configuration — sensor bus communication fails.

**Prevention:**
1. Pin all dependency versions explicitly. Do not use `latest` tags for any container or `*` for any package version.
2. Use separate package.json/requirements.txt lockfiles and commit them. Never run `npm update` or `pip install --upgrade` without a test pass.
3. Test updates in a development environment (another Pi with the same sensor setup, or even a Pi on a bench with mock sensors) before applying to production nodes.
4. Implement a staged rollout: update one non-critical sensor node first, observe for 24 hours, then update remaining nodes. Never update all nodes simultaneously.
5. Keep a known-good SD card image for each node type (hub, garden node, coop node). When a node is broken by an update, re-imaging from the known-good image is the recovery path, not trying to debug a broken system remotely.
6. Disable automatic OS updates on production nodes. Run updates manually, intentionally, and only when you are home and can observe the outcome.

---

### Pitfall M-7: Local Network Discovery Brittleness

**Category:** Self-hosted maintenance
**Build-time vs. operational:** Build-time
**Likelihood:** MEDIUM
**Severity:** MEDIUM

**What goes wrong:**
Edge nodes discover the hub via mDNS/Avahi hostname, or the hub discovers nodes by scanning the LAN. Router reboots, DHCP lease renewals, or network hardware changes cause node IPs to change — nodes can no longer find the hub, hub can no longer find nodes.

**Prevention:**
1. Assign static IP addresses (DHCP reservations by MAC address) to every node and the hub in the router configuration. Document these assignments.
2. Use a stable hostname for the hub (e.g., `farmhub.local` via mDNS) as the primary identifier rather than IP — but fall back to static IP as a secondary lookup.
3. Each edge node should store the hub's static IP as a fallback in its configuration, in case mDNS is not working at boot time.
4. Prefer MQTT for node-to-hub communication with a broker on the hub — nodes publish to the broker, the hub subscribes. Nodes do not need to know the hub's current IP if the MQTT broker hostname is stable.

---

## Minor Pitfalls

### Pitfall L-1: Wiring and Connector Failures Outdoors

**What goes wrong:** Outdoor wire runs fail at connectors — not mid-wire. Screw terminals loosen from thermal cycling, IDC connectors wick moisture via capillary action, JST connectors corrode in weeks in outdoor conditions.
**Prevention:** Use gel-filled waterproof wire nuts or purpose-made outdoor splice connectors for all outdoor connections. Apply dielectric grease to every connector exposed to weather. Strain-relief all wiring entries to enclosures. Run a monthly visual inspection as part of routine maintenance.

---

### Pitfall L-2: Sensor Wire Runs Create Ground Loops

**What goes wrong:** Long sensor wire runs (>5m) between a sensor and a Pi create ground potential differences, especially if the Pi and the sensor are powered from different outlets/circuits. This causes oscillating or biased analog readings.
**Prevention:** Power all sensors from the same power supply rail as the Pi they connect to. For long runs, use differential-signal sensors (I2C over long runs needs buffers, or use RS-485 sensors). Keep power distribution to a single supply per node.

---

### Pitfall L-3: Cron / Systemd Timer Drift Accumulates

**What goes wrong:** Using `cron` or naive `setInterval`-based scheduling for time-critical events (coop door) means the actual execution time can drift forward significantly over days — each job fires a few seconds late, these accumulate. After a week, door close fires 10 minutes late.
**Prevention:** Use absolute time scheduling (systemd timers with `OnCalendar=` directives, or a dedicated scheduler library that calculates next-fire time from the clock at each invocation, not by adding an interval). Never derive the next event time by adding a fixed delta to the last event time.

---

### Pitfall L-4: Daylight Saving Time Causes Double-Fire or Skip

**What goes wrong:** A door schedule fires at "7:30 PM" local time. On DST change nights, this either fires twice (clocks fall back, the 7:30 PM time occurs twice) or not at all (clocks spring forward, 7:30 PM is skipped). For a coop door, a skip means birds are outside all night.
**Prevention:** Store all scheduled times in UTC internally. Convert to local time for display only. Use a scheduling library that correctly handles DST. Test DST transitions explicitly.

---

### Pitfall L-5: Mobile PWA Caching Hides Stale Data

**What goes wrong:** The PWA service worker aggressively caches API responses. A user checking sensor readings on their phone in the yard sees stale data from the last network connection and acts on it — without realizing it is stale.
**Prevention:** Display data freshness prominently: every reading shows its age ("3 min ago"). Service worker caching strategy for API routes must use network-first with a short cache fallback, not cache-first. Implement a "last sync" indicator in the PWA header that turns red if the device has not reached the hub within the last N minutes.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Hardware selection | Choosing Pi 4 for all nodes rather than ESP32 for leaf sensors | ESP32 for sensor-only nodes reduces cost, power, and SD card risk |
| Initial sensor bring-up | Trusting raw sensor values without per-sensor calibration | Build calibration storage and in-situ calibration workflow before any AI training |
| Coop door first implementation | Software-only door control "for now" | Hardware limit switches and NC/power-fail-close behavior must be in v1, not deferred |
| Irrigation first implementation | Active-low relay default-open behavior | Test relay power-on state before connecting to any valve |
| AI inference integration | Running inference on sensor collection nodes | Inference on hub only; sensor nodes are data collectors, not inference engines |
| MQTT/messaging bring-up | Dynamic IP / mDNS unreliability | Static IPs and MQTT broker hostname configured before any sensor nodes deployed |
| Data pipeline | Writing raw sensor data directly into AI training dataset | Implement quality-flag pipeline before any model training |
| System updates | Updating all nodes at once | Staged rollout policy established before first system-wide update |

---

## Sources

This document draws on training knowledge through mid-2025 covering the following domains. No external URL verification was possible during this research pass — confidence is MEDIUM, not HIGH, as a result.

| Claim Area | Confidence | Notes |
|------------|------------|-------|
| SD card failure patterns on Pi | HIGH | Extremely well-documented in Raspberry Pi community; consistent across many sources |
| Active-low relay behavior at boot | HIGH | GPIO hardware behavior; consistent across Pi relay HAT documentation |
| pH probe drift characteristics | HIGH | Well-established electrochemistry; consistent across soil science literature |
| Coop door failure modes | MEDIUM | Based on community patterns from homesteading/automation forums; specific product behaviors not verified |
| AI inference latency on Pi 4 | MEDIUM | Based on benchmarks through mid-2025; specific model/quantization combinations vary widely |
| Thermal throttling thresholds | HIGH | Pi 4 throttle/shutdown temperatures are documented hardware specs |
| Moisture sensor calibration requirements | HIGH | Fundamental property of capacitive sensing technology |
| DST handling in cron | HIGH | Well-documented POSIX/Linux scheduling behavior |
| Relay contact welding from inrush | MEDIUM | Common failure mode but probability varies with relay and solenoid specs |

**Recommended verification targets for Phase 1:**
- Test actual relay board cold-boot behavior before connecting any actuator
- Benchmark chosen AI model inference time on actual hub hardware at operating temperature
- Verify pH sensor ATC behavior with chosen sensor model's datasheet
- Verify solenoid valve NC behavior (not just assumed) for any valve model purchased
