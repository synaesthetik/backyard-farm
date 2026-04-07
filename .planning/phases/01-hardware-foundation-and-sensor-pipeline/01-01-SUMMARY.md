---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: "01"
subsystem: infra
tags: [docker, docker-compose, timescaledb, mosquitto, fastapi, sveltekit, caddy, arm64, mqtt, postgresql, websocket, pwa]

requires: []
provides:
  - Docker Compose stack: mosquitto 2.1.2, timescaledb 2.26.1-pg17, FastAPI api, SvelteKit dashboard, Caddy HTTPS proxy
  - TimescaleDB schema: sensor_readings hypertable with quality CHECK and stuck BOOLEAN columns
  - FastAPI skeleton with /api/health endpoint
  - SvelteKit dashboard scaffold with adapter-node and custom WebSocket server at /ws/dashboard
  - PWA manifest.webmanifest with dark theme colors and standalone display
  - config/hub.env: hub configuration for all downstream services
affects: [01-02, 01-03, 01-04, 01-05, 01-06]

tech-stack:
  added:
    - eclipse-mosquitto:2.1.2 (ARM64 Docker image)
    - timescale/timescaledb:2.26.1-pg17 (ARM64 Docker image)
    - FastAPI 0.135.3 + uvicorn 0.44.0 + asyncpg 0.31.0
    - SvelteKit ^2.21.0 + Svelte 5 + adapter-node ^5.2.13
    - lucide-svelte ^0.487.0 (icon library)
    - "@fontsource/inter" (self-hosted Inter font, 400 + 600 weights)
    - ws ^8.18.2 (WebSocket server for dashboard)
    - caddy:latest (HTTPS reverse proxy)
    - aiomqtt 2.5.1 (bridge service, placeholder)
  patterns:
    - ARM64 platform targeting for all Docker images (linux/arm64)
    - TimescaleDB localhost-only port binding (127.0.0.1:5432) for security
    - SvelteKit with adapter-node + custom Node server for WebSocket co-location
    - CSS custom properties for design tokens (all colors and spacing from UI-SPEC)
    - Multi-stage Docker build for Node.js services

key-files:
  created:
    - hub/docker-compose.yml
    - hub/Caddyfile
    - hub/api/Dockerfile
    - hub/api/main.py
    - hub/api/requirements.txt
    - hub/bridge/Dockerfile
    - hub/bridge/main.py
    - hub/bridge/requirements.txt
    - hub/init-db.sql
    - hub/mosquitto/.gitkeep
    - config/hub.env
    - hub/dashboard/package.json
    - hub/dashboard/svelte.config.js
    - hub/dashboard/vite.config.ts
    - hub/dashboard/tsconfig.json
    - hub/dashboard/vitest.config.ts
    - hub/dashboard/server.js
    - hub/dashboard/Dockerfile
    - hub/dashboard/src/app.html
    - hub/dashboard/src/app.css
    - hub/dashboard/src/routes/+layout.svelte
    - hub/dashboard/src/routes/+page.svelte
    - hub/dashboard/static/manifest.webmanifest
    - hub/dashboard/static/icons/icon-192.png
    - hub/dashboard/static/icons/icon-512.png
  modified: []

key-decisions:
  - "TimescaleDB bound to 127.0.0.1:5432 only (not 0.0.0.0) per threat model — prevents external network access"
  - "vite.config.ts imports sveltekit from @sveltejs/kit/vite not @sveltejs/vite-plugin-svelte (correct source for SvelteKit builds)"
  - "bridge/main.py is an intentional placeholder stub — full implementation deferred to plan 01-05"
  - "dashboard/static/icons are 1x1 placeholder PNGs — real icons deferred to plan 01-06"

patterns-established:
  - "ARM64 platform: all ARM-native Docker images declare platform: linux/arm64 in docker-compose.yml"
  - "Security binding: database and internal services bind to 127.0.0.1 only, never 0.0.0.0"
  - "SvelteKit WebSocket pattern: custom server.js wraps adapter-node build/handler.js + ws WebSocketServer on noServer upgrade"
  - "CSS design tokens: all UI state colors and spacing declared as :root custom properties in app.css"

requirements-completed: [INFRA-01, INFRA-09, UI-04]

duration: 15min
completed: 2026-04-07
---

# Phase 01 Plan 01: Hub Service Stack Summary

**Docker Compose hub stack with Mosquitto, TimescaleDB hypertable schema, FastAPI skeleton, Caddy HTTPS proxy, and SvelteKit dashboard scaffold with WebSocket-capable custom server**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-07T18:52:00Z
- **Completed:** 2026-04-07T18:56:20Z
- **Tasks:** 2/2
- **Files modified:** 25 created

## Accomplishments

- Full Docker Compose stack (6 services: mosquitto, timescaledb, bridge, api, dashboard, caddy) targeting ARM64, validates clean
- TimescaleDB init SQL: sensor_readings and node_heartbeats hypertables with quality CHECK constraint (GOOD/SUSPECT/BAD), stuck BOOLEAN, calibration_applied columns
- SvelteKit 5 dashboard scaffold builds successfully with adapter-node; custom server.js provides WebSocket endpoint at /ws/dashboard
- PWA manifest.webmanifest and dark theme CSS variables locked to UI-SPEC token values

## Task Commits

1. **Task 1: Create project structure and Docker Compose stack** - `793d781` (feat)
2. **Task 2: Scaffold SvelteKit dashboard with custom WebSocket server and PWA manifest** - `0e3aa51` (feat)

## Files Created/Modified

- `hub/docker-compose.yml` - Six-service stack; mosquitto, timescaledb (ARM64, localhost-only port), bridge, api, dashboard, caddy
- `hub/Caddyfile` - Local HTTPS with tls internal; /api/* and /ws/dashboard reverse proxy rules
- `hub/init-db.sql` - sensor_readings hypertable with quality CHECK, stuck BOOLEAN, calibration_applied; zone_config, calibration_offsets, node_heartbeats tables
- `hub/api/main.py` - FastAPI app with /api/health endpoint
- `hub/api/requirements.txt` - fastapi, uvicorn, asyncpg, pydantic, python-dotenv
- `hub/bridge/main.py` - Placeholder bridge service (full impl in plan 01-05)
- `config/hub.env` - Hub LAN IP, ports, SSD mount path, Postgres credentials
- `hub/dashboard/server.js` - Custom Node HTTP+WebSocket server; routes /ws/dashboard upgrades to WebSocketServer
- `hub/dashboard/src/app.css` - Dark theme CSS custom properties: all colors and spacing tokens from UI-SPEC
- `hub/dashboard/src/app.html` - theme-color meta, viewport-fit=cover, manifest link
- `hub/dashboard/static/manifest.webmanifest` - PWA manifest: standalone display, #0f1117 background, #1c1f2b theme

## Decisions Made

- TimescaleDB bound to `127.0.0.1:5432` (not `0.0.0.0`) per threat model — prevents LAN-external DB access
- `vite.config.ts` imports `sveltekit` from `@sveltejs/kit/vite` (not `@sveltejs/vite-plugin-svelte`) — the vite-plugin-svelte v5 package does not export `sveltekit`; the correct export lives in the kit package
- `bridge/main.py` is an intentional placeholder — full MQTT bridge implementation is plan 01-05 scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed vite.config.ts import path for sveltekit plugin**
- **Found during:** Task 2 (npm run build failed)
- **Issue:** Plan specified `import { sveltekit } from '@sveltejs/vite-plugin-svelte'` but `@sveltejs/vite-plugin-svelte` v5 does not export `sveltekit` — that export is in `@sveltejs/kit/vite`
- **Fix:** Changed import to `from '@sveltejs/kit/vite'`
- **Files modified:** hub/dashboard/vite.config.ts
- **Verification:** `npm run build` exits 0
- **Committed in:** 0e3aa51 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Import path correction required for build to succeed. No scope creep.

## Known Stubs

- `hub/bridge/main.py` — Bridge service is a sleep loop placeholder. No MQTT or DB connection. Full implementation in plan 01-05.
- `hub/dashboard/static/icons/icon-192.png`, `icon-512.png` — 1x1 pixel green PNG placeholders. Real icons deferred to plan 01-06.
- `hub/dashboard/src/routes/+page.svelte` — Bare placeholder page. Dashboard components implemented in plan 01-06.

These stubs do not block this plan's goal (infrastructure stack validation). Each is explicitly tracked for downstream plans.

## Issues Encountered

- `npm run build` failed initially because `@sveltejs/vite-plugin-svelte` v5 does not export `sveltekit` — fixed by correcting the import to `@sveltejs/kit/vite` (see Deviations above)
- `docker compose config` warnings about unset POSTGRES_USER/PASSWORD/DB env vars are expected when run without the env_file loaded — config validates successfully (exit 0)

## User Setup Required

None — no external service configuration required. Hub infrastructure runs locally via Docker Compose on the Raspberry Pi 5.

Note: Before running `docker compose up` on the actual hub hardware:
1. Confirm SSD mount path matches `SSD_MOUNT` in `config/hub.env` (default: `/mnt/ssd/data`)
2. Mosquitto config files (`mosquitto.conf`, `passwd`, `acl`) are created in plan 01-02 before the stack is started

## Next Phase Readiness

- Plan 01-02 (MQTT credentials and ACL) can proceed immediately — mosquitto service definition and directory are ready
- Plan 01-03 (edge node sensor daemon) can proceed — MQTT topic schema depends on 01-02 completing first
- Plan 01-05 (hub bridge) has the DB schema and bridge service skeleton ready; only the MQTT logic needs to be implemented
- Plan 01-06 (dashboard components) has the SvelteKit scaffold, design tokens, and WebSocket server ready

---
*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Completed: 2026-04-07*
