---
status: partial
phase: 01-hardware-foundation-and-sensor-pipeline
source: [01-VERIFICATION.md]
started: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. HTTPS Accessibility via LAN Browser
expected: Hub dashboard loads over HTTPS at hub LAN IP. On second visit (after Caddy local CA installed on client), no certificate warning is shown.
result: [pending]

### 2. MQTT Credential Rotation (security)
expected: config/hub.env in git has MQTT_BRIDGE_PASS=CHANGE_ME placeholder (not a real base64 value). Real credential only exists on deployed hub machine. Git history scrubbed so prior credential is not accessible.
result: [pending — placeholder committed 2026-04-09, git history scrub still required]

### 3. IRRIG-03 / COOP-04 Hardware Procurement Documentation
expected: Operator confirms whether ROADMAP hardware checklist satisfies "procurement requirement documented" or a separate docs/hardware-procurement.md is needed listing confirmed models (NC solenoid valves, linear actuator with limit switches).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
