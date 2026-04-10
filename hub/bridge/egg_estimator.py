"""Egg count estimation from nesting box weight sensor.

Algorithm (per D-01, D-02, D-04, research Pattern 3):
  1. Subtract tare_weight_grams from raw weight.
  2. If net weight > hen_weight_threshold_grams, a hen is present;
     subtract hen_weight_threshold_grams from net to get egg-only weight.
  3. Clamp egg-only weight to max(0.0, ...) to prevent negatives.
  4. Divide by egg_weight_grams and round to nearest integer.
  5. Return (max(0, egg_count), hen_present).
"""
from flock_config import FlockConfig


def estimate_egg_count(weight_grams: float, flock_config: FlockConfig) -> tuple[int, bool]:
    """Estimate egg count from nesting box weight reading.

    Args:
        weight_grams: Raw sensor weight in grams.
        flock_config: Current flock configuration.

    Returns:
        (egg_count, hen_present) tuple.
        egg_count is always >= 0.
        hen_present is True when weight (after tare) exceeds hen_weight_threshold_grams.
    """
    # Subtract tare weight first
    net_weight = weight_grams - flock_config.tare_weight_grams

    # Detect hen presence: net weight meets or exceeds hen threshold
    hen_present = net_weight >= flock_config.hen_weight_threshold_grams

    if hen_present:
        # Subtract hen weight to get egg-only contribution
        egg_weight = net_weight - flock_config.hen_weight_threshold_grams
    else:
        egg_weight = net_weight

    # Clamp to prevent negative egg weights from misconfigured tare/threshold
    egg_weight = max(0.0, egg_weight)

    # Guard against division by zero
    if flock_config.egg_weight_grams <= 0:
        return 0, hen_present

    egg_count = round(egg_weight / flock_config.egg_weight_grams)
    return max(0, egg_count), hen_present
