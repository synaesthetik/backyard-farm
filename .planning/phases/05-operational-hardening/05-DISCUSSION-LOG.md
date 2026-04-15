# Phase 5: Operational Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 05-operational-hardening
**Areas discussed:** pH calibration workflow, ntfy push notifications, Data retention policies, Calibration management UX

---

## pH Calibration Workflow

### Reminder location

| Option | Description | Selected |
|--------|-------------|----------|
| Alert bar (P1 amber) | Same persistent alert bar as low moisture, stuck door, etc. | ✓ |
| Zone detail page only | Warning badge on zone detail page next to pH reading | |
| Both | Alert bar + zone badge | |

**User's choice:** Alert bar (P1 amber)

### Calibration recording UX

| Option | Description | Selected |
|--------|-------------|----------|
| Button on zone detail page | 'Record Calibration' button on /zones/[id] next to pH row | |
| Dedicated calibration page | New /calibration route listing all sensors | |
| You decide | Claude picks based on existing zone detail page structure | ✓ |

**User's choice:** You decide

---

## ntfy Push Notifications

### Deployment model

| Option | Description | Selected |
|--------|-------------|----------|
| Docker sidecar in compose | Add ntfy container to docker-compose.yml | |
| External ntfy server | Farmer provides ntfy server URL | ✓ |
| Support both | Config accepts any URL, optional compose service | |

**User's choice:** External ntfy server

### Configuration location

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard settings page | New section on /settings/notifications | |
| Environment variables only | NTFY_URL and NTFY_TOPIC in hub.env | |
| Both -- env default, dashboard override | Env vars set default, dashboard overrides at runtime, test button | ✓ |

**User's choice:** Both -- env default, dashboard override

---

## Data Retention Policies

### Visibility to farmer

| Option | Description | Selected |
|--------|-------------|----------|
| System health panel stat | Single line in System Health panel | |
| Dedicated storage section | Settings page with table sizes, policy status, purge button | ✓ |
| Invisible -- just works | No UI, TimescaleDB policies run automatically | |

**User's choice:** Dedicated storage section

---

## Calibration Management UX

### Offset propagation

| Option | Description | Selected |
|--------|-------------|----------|
| MQTT config push | Bridge publishes new offset to edge node via MQTT | |
| Hub-only -- no edge push needed | Hub applies offsets at ingestion, edge sends raw values | ✓ |
| You decide | Claude picks based on architecture | |

**User's choice:** Hub-only -- no edge push needed

---

## Claude's Discretion

- pH calibration recording UX placement
- Calibration management page layout and route
- ntfy HTTP POST format
- Settings page routes
- Continuous aggregate refresh interval
- Storage section layout
- Purge Now confirmation dialog

## Deferred Ideas

None -- discussion stayed within phase scope.
