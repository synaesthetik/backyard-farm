# Home / Overview Screen

**Route:** `/`

The home screen is the default landing page and shows a real-time summary of all configured garden zones and the coop. It updates automatically via WebSocket without requiring a page refresh.

## What you see

### Zone Cards
Each configured garden zone appears as a card showing:
- **Zone name** and a **composite health badge** (green = GOOD, yellow = ATTENTION, red = ALERT)
- **Soil moisture (VWC %)** — current reading with quality flag badge (GOOD / SUSPECT / BAD)
- **pH** and **temperature (°C)** with quality flags
- **Freshness timestamp** — turns orange/red if the last reading is older than 5 minutes (STALE)
- **Irrigation status** — open / closed / unknown

Tap a zone card to open the [Zone Detail](zones.md) screen for that zone.

If no zones are configured, the zone area shows an "Add a zone in settings to get started" prompt.

### AI Status Card
Located in the right column (desktop) or top (mobile). Shows AI engine status at a glance:
- Whether the AI engine is enabled or rule-based fallback is active
- Model maturity status for each AI domain (zone health, irrigation, flock anomaly)
- During cold-start: "Model still learning" indicator

### Flock Summary Card
Shows coop status at a glance:
- Coop door state: open / closed / moving / stuck
- Egg count today vs. expected (e.g., "4 / 6 expected")
- Production trend indicator (up / flat / down vs. 30-day model)
- Feed fill percentage
- Water fill percentage

Tap the flock card to open the [Coop Panel](coop.md).

### Alert Bar
Persistent bar at the top of every screen. See [Alerts Configuration](../configuration/alerts.md) for all alert types. P0 alerts appear in red, P1 in yellow. Multiple alerts of the same type across zones are grouped (e.g., "Low moisture — 3 zones").

### System Health Panel
Located at the bottom of the home screen. Shows each connected edge node with:
- Online / offline status
- Last heartbeat timestamp
- Data freshness indicator

A node is considered offline if it misses 3 consecutive 60-second heartbeats (≥3 minutes without contact). See [`node_offline` alert](../configuration/alerts.md#p0-alerts-critical).

## Layout

On mobile, the layout is a single column: AI status card, then flock summary card, then zone cards. On desktop (≥640px), zone cards appear in the left (wider) column and AI status + flock summary appear in a sticky right column.

## Actions available
- Tap a zone card → Zone detail screen
- Tap flock/AI card → Coop panel or AI settings
- Tap an alert bar item → Jumps to the relevant zone or component
