"""Zone health composite score computation (ZONE-06, D-28).

Three tiers:
  green: all sensors within target ranges
  yellow: one sensor outside target but not critically
  red: any sensor critically out of range or BAD quality flag

Computed hub-side and broadcast via WebSocket.
"""
from typing import Optional


def compute_health_score(
    zone_id: str,
    moisture: Optional[dict],
    ph: Optional[dict],
    temperature: Optional[dict],
    zone_config,
) -> dict:
    """Compute composite health score for a zone.

    Args:
        zone_id: zone identifier
        moisture: {"value": float, "quality": str} or None
        ph: {"value": float, "quality": str} or None
        temperature: {"value": float, "quality": str} or None
        zone_config: ZoneConfig with threshold attributes

    Returns:
        {"score": "green"|"yellow"|"red", "contributing_sensors": [...]}
    """
    contributing = []
    has_critical = False

    sensors = [
        ("moisture", moisture, zone_config.vwc_low_threshold, zone_config.vwc_high_threshold),
        ("ph", ph, zone_config.ph_low_threshold, zone_config.ph_high_threshold),
        ("temperature", temperature, zone_config.temp_low_threshold, zone_config.temp_high_threshold),
    ]

    for name, reading, low, high in sensors:
        if reading is None:
            continue

        # BAD quality flag -> red immediately
        if reading.get("quality") == "BAD":
            contributing.append(name)
            has_critical = True
            continue

        value = reading.get("value", 0)

        # Critical: more than 30% of range width outside range
        range_width = high - low
        critical_margin = range_width * 0.3 if range_width > 0 else 5.0

        if value < (low - critical_margin) or value > (high + critical_margin):
            contributing.append(name)
            has_critical = True
        elif value < low or value > high:
            contributing.append(name)

    if has_critical:
        score = "red"
    elif contributing:
        score = "yellow"
    else:
        score = "green"

    return {
        "type": "zone_health_score",
        "zone_id": zone_id,
        "score": score,
        "contributing_sensors": contributing,
    }
