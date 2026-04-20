# Milestones

## v1.0 Backyard Farm v1.0 (Shipped: 2026-04-20)

**Phases completed:** 8 phases, 39 plans, 40 tasks

**Key accomplishments:**

- Docker Compose hub stack with Mosquitto, TimescaleDB hypertable schema, FastAPI skeleton, Caddy HTTPS proxy, and SvelteKit dashboard scaffold with WebSocket-capable custom server
- Mosquitto 2.x broker configured with per-node ACL isolation and documented MQTT topic schema serving as the communication contract for edge daemon (01-03) and hub bridge (01-05)
- SQLite store-and-forward edge daemon with DS18B20/ADS1115/moisture-placeholder sensor drivers, MQTT publish with QoS 1, and on-reconnect chronological buffer flush — all backed by 6 unit tests
- LocalRuleEngine with emergency irrigation shutoff (>= 95% VWC) and coop door hard-close (>= 21:00), integrated into daemon polling loop, with 9 passing unit tests — all executing locally without hub involvement
- Complete MQTT bridge pipeline applying calibration offsets, quality flags, and stuck detection at ingestion, writing to TimescaleDB, with FastAPI WebSocket manager for real-time dashboard push
- Svelte 5 dashboard with live sensor readings, quality badges, stale/stuck indicators, and node health panel driven by WebSocket reactive store
- Caddy /ws/dashboard rerouted from SvelteKit stub (empty snapshot) to FastAPI ws_manager (live sensor data), unblocking all 5 real-time dashboard verification truths
- SensorValue.test.ts (8 tests):
- MQTT command/ack flow with asyncio.Event correlation, single-zone 409 invariant, and all Phase 2 Pydantic/TypeScript contracts established as a foundation for the remaining 5 plans
- Four pure-logic hub bridge modules with full TDD coverage — threshold-based recommendations with dedup/backoff/cooldown, hysteresis alert evaluation, composite zone health scoring, and sensor-feedback irrigation monitoring
- Astronomical coop door clock with astral 3.2, P0 stuck-door watchdog, time-bucketed history endpoint, recommendation approve/reject with actual valve open, and full Phase 2 sensor pipeline wired into bridge main loop
- Multi-route SPA shell with bottom tab navigation, persistent alert bar, 5 shared Phase 2 components, and WebSocket store extended for all Phase 2 delta types — the app scaffold that plans 02-05 and 02-06 build upon
- uPlot time-series charts, full zone detail with irrigation controls, CoopPanel with door/feed/water, and RecommendationCard queue — all three feature page stubs replaced with complete implementations
- SvelteKit PWA service worker with versioned app shell cache, all 4 Phase 2 component test suites (45 tests passing), and vitest $lib/$app alias fix enabling the full test suite
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Single-column flock configuration form at /coop/settings with 10 fields, breed-conditional lay rate, tare-from-sensor button, full client-side validation, and 6 Vitest tests — all 58 dashboard tests pass, build clean.
- FastAPI flock router with 4 endpoints (config CRUD, 30-day egg history, immediate refresh-eggs) and WebSocket snapshot extended with egg_count and feed_consumption state for new connections.
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Root layout
- 1. [Rule 2 - Missing Critical Protection] Added `site/` to .gitignore
- One-liner:
- One-liner:

---
