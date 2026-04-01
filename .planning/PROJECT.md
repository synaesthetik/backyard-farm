# Backyard Farm Platform

## What This Is

A self-hosted, local-only platform for managing a medium-scale backyard farm — multiple garden zones and a chicken flock. It uses distributed edge nodes for sensor collection and local AI inference, a central orchestration layer, and a web + mobile dashboard where the farmer monitors everything and approves AI-generated action recommendations.

## Core Value

A single dashboard where you can see every zone's sensor readings, irrigation status, and flock health at a glance — and act on AI recommendations without leaving it.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Platform & Infrastructure**
- [ ] Distributed edge node architecture — one node per zone/area (garden zones, coop), all local-only
- [ ] Central hub aggregates data from all edge nodes and serves the UI
- [ ] All data and AI inference stays on-premises — no cloud dependency
- [ ] Hardware-agnostic sensor layer — pluggable adapters for whatever hardware is chosen

**Garden & Irrigation**
- [ ] Soil sensor support per zone: moisture, pH, temperature, nutrient levels
- [ ] Automated irrigation triggered by sensor thresholds
- [ ] AI recommends irrigation schedule changes — farmer approves before execution
- [ ] Per-zone plant health status derived from sensor readings

**Chicken Flock**
- [ ] Automated coop door — opens at dawn, closes at dusk (configurable schedule)
- [ ] Feed and water level monitoring with alerts when low
- [ ] Daily egg production logging and yield tracking
- [ ] Flock health alerts — behavioral anomalies, unexpected mortality, production drops

**AI & Recommendations**
- [ ] Local AI models run on edge nodes — no external API calls
- [ ] Recommendation engine surfaces suggested actions (water zone X, check bird Y)
- [ ] Recommend-and-confirm flow — AI proposes, farmer approves, system executes
- [ ] AI learns from approval/rejection history to improve future recommendations

**Dashboard & UI**
- [ ] Web dashboard — accessible from any browser on the local network
- [ ] Mobile-friendly / PWA — usable from phone while in the yard
- [ ] Live view: all zones + flock status on one screen
- [ ] Notification/alert surface for time-sensitive actions (low feed, health alert)

### Out of Scope

- Cloud sync or remote access outside home network — local-only is a hard constraint; adds complexity and privacy concerns
- Computer vision / camera-based plant health — sensor-based approach chosen for v1; cameras are a potential future addition
- Fully autonomous execution without approval — recommend-and-confirm is intentional; autonomy can be tuned later per domain
- Commercial-scale features (fleet management, market pricing, yield analytics) — hobby/medium backyard focus

## Context

- Hardware is undecided — a major research deliverable is recommending specific edge node hardware (SBCs, sensor modules, actuators, coop controllers) that fits the local-only, distributed architecture
- Local AI models need to run on constrained edge hardware — model selection (Ollama, TinyML, ONNX, etc.) must account for this
- Multiple garden zones means the system needs zone-aware data modeling from the start
- The farmer is actively involved in decisions — the UX must make approving/rejecting recommendations fast and frictionless

## Constraints

- **Connectivity**: Local-only — no cloud APIs, no external inference endpoints, all AI runs on-device
- **Hardware**: Unknown at project start — hardware selection is part of the research phase; all software must be hardware-agnostic via adapters
- **Scale**: Medium backyard — multiple garden zones, 10-25 chickens; not commercial
- **Autonomy**: Recommend-and-confirm for all actions in v1 — no fully autonomous execution without explicit approval

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-only (no cloud) | Privacy preference, offline reliability, no recurring costs | — Pending |
| Distributed edge nodes per zone | Reduces single point of failure, nodes closer to sensors/actuators | — Pending |
| Recommend-and-confirm (not full autonomy) | Farmer stays in control; autonomy can be layered in later | — Pending |
| Sensor-based plant health (not camera) | Simpler hardware, more actionable data; cameras deferred to v2 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 after initialization*
