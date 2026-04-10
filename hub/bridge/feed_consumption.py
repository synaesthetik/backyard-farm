"""Feed consumption derivation from daily load cell weight delta.

Algorithm (per D-12, D-13, D-14, research Pattern/Pitfall 3):
  - Normal day: consumption = start_weight - end_weight
  - Refill detected: if end_weight > start_weight (feeder was refilled during the day)
    return (None, True) — consumption is indeterminate for refill days.
"""


def compute_daily_feed_consumption(
    start_weight: float,
    end_weight: float,
) -> tuple[float | None, bool]:
    """Compute daily feed consumption from start and end weight readings.

    Refill detection: if end_weight exceeds start_weight, a refill occurred.
    In that case, consumption is unknown (return None).

    Args:
        start_weight: Feed weight (grams) at the start of the day (first reading).
        end_weight: Feed weight (grams) at the end of the day (last reading).

    Returns:
        (consumption_grams, refill_detected):
          - consumption_grams: grams consumed, or None if refill detected.
          - refill_detected: True if feeder was refilled during the day.
    """
    if end_weight > start_weight:
        return None, True

    consumption = start_weight - end_weight
    return consumption, False
