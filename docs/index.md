# Backyard Farm Platform

A self-hosted farm monitoring and automation dashboard. Sensor data flows from Raspberry Pi edge nodes to a central hub running on your LAN. Monitor soil moisture, pH, and temperature for every garden zone; automate irrigation and coop door schedules; track flock health — all from a mobile-friendly dashboard accessible from any browser on your network.

## What's here

- **[Getting Started](getting-started.md)** — First boot, Docker Compose setup, initial zone configuration
- **[Dashboard](dashboard/overview.md)** — Every screen and what it shows
- **[Configuration](configuration/zones.md)** — All settings options with descriptions and defaults
- **[Troubleshooting](troubleshooting/index.md)** — 20 common failure modes with diagnostic steps
- **[Hardware](hardware/README.md)** — Shopping list, wiring diagrams, smoke test procedures

## Key features

| Feature | Description |
|---------|-------------|
| Sensor monitoring | Soil moisture (VWC), pH, temperature — with quality flags (GOOD / SUSPECT / BAD) and stale detection |
| Irrigation control | Manual valve control and threshold-based recommendations with approve/reject workflow |
| Coop automation | Sunrise/sunset door scheduling with limit switch safety confirmation |
| Flock tracking | Egg production model, feed consumption rate, production drop alerts |
| AI recommendations | ONNX-backed zone health scoring and irrigation schedule optimization |
| Push notifications | In-app alerts + optional self-hosted ntfy push to iOS/Android |
