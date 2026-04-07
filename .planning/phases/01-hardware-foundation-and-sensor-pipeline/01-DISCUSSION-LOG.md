# Phase 1: Hardware Foundation and Sensor Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 01-hardware-foundation-and-sensor-pipeline
**Areas discussed:** Sensor hardware selection, Hub hardware selection, Quality flag thresholds, Emergency rule thresholds

---

## Sensor Hardware Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Soil moisture — Capacitive I2C (Seesaw/STEMMA QT) | No ADC needed, daisy-chainable | |
| Soil moisture — Capacitive ADC (ADS1115) | More flexible, common DIY choice | |
| Soil moisture — Resistive ADC | Cheaper, degrades over time | |
| Soil moisture — Haven't decided / need to research | Include research spike in plan | ✓ |

**User's choice:** Research spike — moisture sensor model undecided. Claude to evaluate capacitive I2C vs ADS1115 in plan 01-03.

---

| Option | Description | Selected |
|--------|-------------|----------|
| pH — Analog probe + ADS1115 ADC | Standard approach, affordable | ✓ |
| pH — Atlas Scientific EZO-pH | Higher accuracy, digital, ~$45/board | |
| pH — Haven't decided | Research spike | |

**User's choice:** Analog pH probe + ADS1115 ADC over I2C.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Temperature — DS18B20 1-wire | Waterproof, ±0.5°C, multi-sensor per pin | ✓ |
| Temperature — SHT31/SHT40 I2C | Combined temp+humidity, more expensive | |
| Temperature — Haven't decided | Research spike | |

**User's choice:** DS18B20 1-wire.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Edge node — Pi Zero 2W | Compact, cheap, quad-core ARM64, Wi-Fi | ✓ |
| Edge node — Pi 3B/3B+ | 1GB RAM, more headroom | |
| Edge node — Pi 4B 2GB | Most headroom, overkill for sensor node | |
| Edge node — Haven't decided | Research spike | |

**User's choice:** Raspberry Pi Zero 2W.

---

| Option | Description | Selected |
|--------|-------------|----------|
| 3 sensors per node (moisture + pH + temp) | Standard zone | |
| More than 3 | Needs TCA9548A multiplexer | |
| Let Claude decide based on chosen sensors | Defers multiplexer decision to research | ✓ |

**User's choice:** Let Claude decide based on moisture sensor selection.

---

## Hub Hardware Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Hub — Raspberry Pi 5 8GB | ARM64, lower power, good for Docker | ✓ |
| Hub — x86_64 mini-PC | More compute, higher power draw | |
| Hub — Already have hardware | — | |

**User's choice:** Raspberry Pi 5 8GB.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Storage — SSD (USB3 or NVMe) | Required for TimescaleDB performance | ✓ |
| Storage — SD card | Acceptable risk with high-endurance card | |
| Storage — Built-in NVMe (x86) | Best if using x86 | |

**User's choice:** SSD (USB3 or NVMe).

---

| Option | Description | Selected |
|--------|-------------|----------|
| Static IP — Not yet, include in plan 01-01 | DHCP reservation + NTP (chrony) | ✓ |
| Static IP — Already configured | Skip this from plan 01-01 | |

**User's choice:** Not yet — include static IP reservation and chrony NTP setup in plan 01-01.

---

## Quality Flag Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Range-based per sensor type | Stateless, applies from first reading | ✓ |
| Deviation-based (delta from moving average) | Requires history to bootstrap | |
| Combined range + deviation | Most robust, most complex | |

**User's choice:** Range-based per sensor type.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Claude uses standard defaults, configurable later | Env vars, reasonable defaults | ✓ |
| I want to define them now | User specifies exact ranges | |

**User's choice:** Claude uses standard defaults (moisture 2-98% GOOD, pH 3-10 GOOD, temp 0-60°C GOOD) as configurable env vars.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Stuck = separate display state only, don't downgrade quality | Keeps GOOD data for Phase 4 training | ✓ |
| Downgrade stuck readings to SUSPECT | More conservative, excludes from training | |

**User's choice:** Separate display state only — STUCK and quality flag coexist independently.

---

## Emergency Rule Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Irrigation shutoff at ≥ 95% VWC | Conservative, avoids false positives | ✓ |
| Irrigation shutoff at ≥ 90% VWC | Slightly earlier intervention | |
| User-defined threshold | Custom value | |
| Configurable env var, default 95% | Best for tuning | |

**User's choice:** 95% VWC — stored as `EMERGENCY_MOISTURE_SHUTOFF_VWC` env var, default 95.
**Notes:** This is a local edge node safety backstop. Hub controls normal irrigation. This only fires without hub.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Hard time limit only: force-close past 21:00 | Simplest, hardest guarantee | ✓ |
| Time limit + hub silence (> 2h) | Additional protection for hub failure | |
| Time limit + hub silence + weather | Out of scope for Phase 1 | |

**User's choice:** Hard time limit only — 21:00 force-close.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable env var, default 21:00 | `COOP_HARD_CLOSE_HOUR=21` | ✓ |
| Hardcoded constant | Simpler, requires deploy to change | |

**User's choice:** Configurable via `COOP_HARD_CLOSE_HOUR` env var, default 21.

---

*Discussion completed: 2026-04-07*
*Next step: /gsd-plan-phase 1*
