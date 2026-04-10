"""Alert evaluation engine with debounce and hysteresis (NOTF-02).

Alert fires when value crosses threshold.
Alert clears only when value recovers past hysteresis band.
No re-fire while sustained. Hub-side only (D-11).

Hysteresis bands (discretion, per Research recommendations):
  moisture_low: +5% VWC
  ph_low: +0.2 pH
  ph_high: -0.2 pH
  feed_low: +5%
  water_low: +5%
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Hysteresis band values
HYSTERESIS_BANDS = {
    "moisture_low": 5.0,
    "ph_low": 0.2,
    "ph_high": 0.2,
    "feed_low": 5.0,
    "water_low": 5.0,
    "temp_low": 2.0,
    "temp_high": 2.0,
}

# Alert type -> (severity, message_template, deep_link_template)
ALERT_DEFINITIONS = {
    "moisture_low": ("P1", "Low moisture \u2014 {zone_id}", "/zones/{zone_id}"),
    "ph_low": ("P1", "Low pH \u2014 {zone_id}", "/zones/{zone_id}"),
    "ph_high": ("P1", "High pH \u2014 {zone_id}", "/zones/{zone_id}"),
    "temp_low": ("P1", "Low temperature \u2014 {zone_id}", "/zones/{zone_id}"),
    "temp_high": ("P1", "High temperature \u2014 {zone_id}", "/zones/{zone_id}"),
    "feed_low": ("P1", "Low feed level", "/coop"),
    "water_low": ("P1", "Low water level", "/coop"),
    "stuck_door": ("P0", "Coop door stuck", "/coop"),
    "node_offline": ("P0", "Node offline \u2014 {node_id}", "/"),
}


class AlertEngine:
    def __init__(self):
        self._active_alerts: dict[str, dict] = {}  # alert_key -> alert dict

    def evaluate(self, alert_key: str, value: float,
                 fire_threshold: float, clear_above: bool = True) -> tuple[bool, bool]:
        """
        Evaluate whether an alert should fire or clear.

        Args:
            alert_key: unique key, e.g. "moisture_low:zone-01"
            value: current sensor value
            fire_threshold: alert fires when value crosses this
            clear_above: if True, fires when value < threshold, clears when value > threshold + hysteresis
                         if False, fires when value > threshold, clears when value < threshold - hysteresis

        Returns:
            (changed: bool, is_active: bool)
        """
        alert_type = alert_key.split(":")[0]
        hysteresis = HYSTERESIS_BANDS.get(alert_type, 5.0)
        was_active = alert_key in self._active_alerts

        if clear_above:
            # Fire when value < threshold (e.g., low moisture)
            if not was_active and value < fire_threshold:
                self._active_alerts[alert_key] = {
                    "key": alert_key,
                    "fired_at": datetime.now(timezone.utc).isoformat(),
                }
                return True, True
            elif was_active and value > (fire_threshold + hysteresis):
                del self._active_alerts[alert_key]
                return True, False
        else:
            # Fire when value > threshold (e.g., high pH, high temp)
            if not was_active and value > fire_threshold:
                self._active_alerts[alert_key] = {
                    "key": alert_key,
                    "fired_at": datetime.now(timezone.utc).isoformat(),
                }
                return True, True
            elif was_active and value < (fire_threshold - hysteresis):
                del self._active_alerts[alert_key]
                return True, False

        return False, was_active

    def set_alert(self, alert_key: str):
        """Directly set an alert active (for non-threshold alerts like stuck_door)."""
        if alert_key not in self._active_alerts:
            self._active_alerts[alert_key] = {
                "key": alert_key,
                "fired_at": datetime.now(timezone.utc).isoformat(),
            }

    def clear_alert(self, alert_key: str):
        """Directly clear an alert (for manual reset like stuck_door)."""
        self._active_alerts.pop(alert_key, None)

    def get_alert_state(self) -> list[dict]:
        """Return grouped alert list for WebSocket broadcast (D-12).

        Groups alerts by type. If 3 zones have moisture_low, returns one entry
        with count=3 and message "Low moisture - 3 zones".
        """
        # Group by alert_type
        groups: dict[str, list[str]] = {}  # alert_type -> [zone_ids or identifiers]
        for alert_key in self._active_alerts:
            parts = alert_key.split(":")
            alert_type = parts[0]
            identifier = parts[1] if len(parts) > 1 else ""
            if alert_type not in groups:
                groups[alert_type] = []
            groups[alert_type].append(identifier)

        result = []
        for alert_type, identifiers in groups.items():
            defn = ALERT_DEFINITIONS.get(alert_type, ("P1", alert_type, "/"))
            severity, msg_template, link_template = defn
            count = len(identifiers)

            if count == 1:
                message = msg_template.format(
                    zone_id=identifiers[0], node_id=identifiers[0]
                )
                deep_link = link_template.format(
                    zone_id=identifiers[0], node_id=identifiers[0]
                )
            else:
                # Grouped: "Low moisture - 3 zones"
                base_msg = msg_template.split(" \u2014 ")[0] if " \u2014 " in msg_template else msg_template
                message = f"{base_msg} \u2014 {count} zones"
                deep_link = "/"  # Navigate to zones overview for grouped alerts (D-12)

            result.append({
                "key": f"{alert_type}:grouped" if count > 1 else f"{alert_type}:{identifiers[0]}",
                "severity": severity,
                "message": message,
                "deep_link": deep_link,
                "count": count,
            })

        # Sort: P0 first, then P1
        result.sort(key=lambda a: (0 if a["severity"] == "P0" else 1, a["key"]))
        return result
