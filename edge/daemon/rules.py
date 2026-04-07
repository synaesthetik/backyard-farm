"""Local rule engine for emergency-threshold actions (INFRA-04).

Executes on the edge node without hub involvement.
Two rules in Phase 1:
  1. Emergency irrigation shutoff at >= EMERGENCY_MOISTURE_SHUTOFF_VWC (D-13)
  2. Coop door hard-close at or after COOP_HARD_CLOSE_HOUR (D-14)
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RuleAction(Enum):
    IRRIGATION_SHUTOFF = "irrigation_shutoff"
    COOP_HARD_CLOSE = "coop_hard_close"


@dataclass
class RuleResult:
    action: RuleAction
    reason: str
    triggered_value: float | int


class LocalRuleEngine:
    def __init__(
        self,
        node_type: str,  # "zone" or "coop"
        moisture_shutoff_vwc: float = 95.0,
        coop_hard_close_hour: int = 21,
    ):
        self.node_type = node_type
        self.moisture_shutoff_vwc = moisture_shutoff_vwc
        self.coop_hard_close_hour = coop_hard_close_hour

    def evaluate(
        self,
        sensor_readings: dict,
        current_hour: int = None,
    ) -> list:
        """Evaluate all applicable rules against current readings.

        Args:
            sensor_readings: Dict of sensor_type -> value (e.g., {"moisture": 96.0})
            current_hour: Current local hour (0-23). If None, uses system time.

        Returns:
            List of triggered RuleResults (empty if no rules fire).
        """
        results = []

        if current_hour is None:
            current_hour = datetime.now().hour

        # Rule 1: Emergency irrigation shutoff (zone nodes only)
        if self.node_type == "zone":
            moisture = sensor_readings.get("moisture")
            if moisture is not None and moisture >= self.moisture_shutoff_vwc:
                result = RuleResult(
                    action=RuleAction.IRRIGATION_SHUTOFF,
                    reason=f"Moisture {moisture}% >= shutoff threshold {self.moisture_shutoff_vwc}%",
                    triggered_value=moisture,
                )
                results.append(result)
                logger.warning("EMERGENCY SHUTOFF: %s", result.reason)

        # Rule 2: Coop door hard-close (coop nodes only)
        if self.node_type == "coop":
            if current_hour >= self.coop_hard_close_hour:
                result = RuleResult(
                    action=RuleAction.COOP_HARD_CLOSE,
                    reason=f"Current hour {current_hour}:00 >= hard-close hour {self.coop_hard_close_hour}:00",
                    triggered_value=current_hour,
                )
                results.append(result)
                logger.warning("COOP HARD-CLOSE: %s", result.reason)

        return results


def execute_action(action: RuleAction):
    """Execute a rule action via GPIO.

    Phase 1: Log only — actual GPIO control wired in Phase 2
    when relay hardware is confirmed (relay boot-state test required first).
    """
    logger.info("RULE ACTION (Phase 1 stub): %s", action.value)
