"""Training pipeline for the flock production anomaly detection model.

Trains a GradientBoostingClassifier to predict flock production anomaly
(0=normal, 1=anomaly) from 8 flock-derived features.

AI-06 compliance: Only GOOD-flagged sensor data is used for training.
D-08 compliance: Regression protection keeps the previous model if the new
                 model's F1-macro score is not better than the current model.
D-08 compliance: Model versioning retains the last 2 versions (.onnx + .prev.onnx).

Feature vector (8 features):
  egg_count_rolling_3d_avg, expected_production, production_ratio,
  feed_consumption_rolling_3d_avg, feed_consumption_rolling_7d_avg,
  daylight_hours, age_factor, flock_size

Labels: 1 if production_ratio < 0.75 for 3+ consecutive days, else 0.

Output: hub/models/flock_anomaly.onnx
"""
import asyncio
import logging
import os
import shutil

import numpy as np
import onnx
import onnxruntime as ort
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

logger = logging.getLogger(__name__)

MODEL_NAME = "flock_anomaly"
N_FEATURES = 8
MIN_SAMPLES = 50

# Anomaly threshold: production below 75% of expected for 3+ consecutive days
ANOMALY_RATIO_THRESHOLD = 0.75
ANOMALY_CONSECUTIVE_DAYS = 3

MODELS_DIR = os.getenv(
    "MODELS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"),
)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

async def fetch_training_data(db_pool) -> tuple:
    """Fetch flock production data and compute anomaly labels.

    Queries egg_counts, feed_daily_consumption, and flock_config to build
    the 8-feature vector for each day. Uses only GOOD-flagged underlying data
    (the egg_counts table is populated from GOOD-quality nesting_box_weight
    readings per the bridge pipeline).

    Labels:
      - Compute production_ratio = rolling_3d_avg / expected_production
      - If ratio < 0.75 for 3+ consecutive days, label that day and the
        preceding consecutive days as anomaly (1); otherwise normal (0).

    Args:
        db_pool: asyncpg connection pool.

    Returns:
        (X: np.ndarray shape [n_samples, 8], y: np.ndarray shape [n_samples])
        Returns (None, None) if insufficient data.
    """
    # Query egg counts (derived from GOOD nesting_box_weight readings)
    egg_sql = """
        SELECT
            ec.count_date,
            ec.estimated_count,
            COALESCE(
                AVG(ec2.estimated_count),
                ec.estimated_count::float
            ) AS rolling_3d_avg
        FROM egg_counts ec
        LEFT JOIN egg_counts ec2
          ON ec2.count_date BETWEEN ec.count_date - INTERVAL '2 days' AND ec.count_date
        GROUP BY ec.count_date, ec.estimated_count
        ORDER BY ec.count_date
    """

    # Query feed consumption (derived from GOOD feed_weight readings)
    feed_sql = """
        SELECT
            fdc.consumption_date,
            fdc.consumption_grams,
            AVG(fdc2.consumption_grams) FILTER (WHERE fdc2.consumption_grams IS NOT NULL)
              OVER (
                ORDER BY fdc.consumption_date
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
              ) AS rolling_3d_avg,
            AVG(fdc2.consumption_grams) FILTER (WHERE fdc2.consumption_grams IS NOT NULL)
              OVER (
                ORDER BY fdc.consumption_date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
              ) AS rolling_7d_avg
        FROM feed_daily_consumption fdc
        LEFT JOIN feed_daily_consumption fdc2 ON fdc2.consumption_date <= fdc.consumption_date
        WHERE fdc.refill_detected = FALSE
        GROUP BY fdc.consumption_date, fdc.consumption_grams
        ORDER BY fdc.consumption_date
    """

    flock_sql = """
        SELECT flock_size, breed, hatch_date, latitude, longitude,
               supplemental_lighting, lay_rate_override
        FROM flock_config
        ORDER BY id DESC
        LIMIT 1
    """

    try:
        egg_rows = await db_pool.fetch(egg_sql)
        flock_row = await db_pool.fetchrow(flock_sql)
    except Exception as exc:
        logger.error("Failed to fetch flock training data: %s", exc)
        return None, None

    if not egg_rows or not flock_row:
        return None, None

    try:
        feed_rows = await db_pool.fetch(feed_sql)
    except Exception:
        feed_rows = []

    # Build feed lookup by date
    feed_by_date = {}
    for row in feed_rows:
        feed_by_date[row["consumption_date"]] = {
            "rolling_3d": row.get("rolling_3d_avg") or 0.0,
            "rolling_7d": row.get("rolling_7d_avg") or 0.0,
        }

    from production_model import (
        compute_age_factor,
        compute_daylight_factor,
        compute_expected_production,
        BREED_LAY_RATES,
    )

    flock_size = flock_row["flock_size"]
    breed = flock_row["breed"]
    hatch_date = flock_row["hatch_date"]
    lat = float(flock_row["latitude"])
    lon = float(flock_row["longitude"])
    supplemental = bool(flock_row["supplemental_lighting"])
    lay_rate_override = flock_row["lay_rate_override"]

    lay_rate = (
        float(lay_rate_override)
        if lay_rate_override is not None
        else BREED_LAY_RATES.get(breed, 0.75) or 0.75
    )

    X_rows = []
    ratios_by_date = {}

    for row in egg_rows:
        count_date = row["count_date"]
        egg_count = float(row["estimated_count"] or 0)
        rolling_3d = float(row["rolling_3d_avg"] or egg_count)

        age_factor = compute_age_factor(hatch_date, today=count_date)
        daylight_factor = compute_daylight_factor(lat, lon, count_date, supplemental)
        expected = compute_expected_production(flock_size, lay_rate, age_factor, daylight_factor)

        production_ratio = (rolling_3d / expected) if expected > 0 else 0.0
        ratios_by_date[count_date] = production_ratio

        feed = feed_by_date.get(count_date, {"rolling_3d": 0.0, "rolling_7d": 0.0})

        # daylight_hours from factor (factor = hours/17)
        daylight_hours = daylight_factor * 17.0

        features = [
            rolling_3d,
            expected,
            production_ratio,
            feed["rolling_3d"],
            feed["rolling_7d"],
            daylight_hours,
            age_factor,
            float(flock_size),
        ]
        X_rows.append((count_date, features))

    if not X_rows:
        return None, None

    # Compute anomaly labels: ratio < threshold for 3+ consecutive days
    sorted_dates = [d for d, _ in X_rows]
    labels = {}
    consecutive = 0
    below_threshold_streak = []

    for count_date in sorted_dates:
        ratio = ratios_by_date.get(count_date, 1.0)
        if ratio < ANOMALY_RATIO_THRESHOLD:
            consecutive += 1
            below_threshold_streak.append(count_date)
        else:
            # If streak reached threshold, mark streak days as anomaly
            if consecutive >= ANOMALY_CONSECUTIVE_DAYS:
                for d in below_threshold_streak:
                    labels[d] = 1
            consecutive = 0
            below_threshold_streak = []
            labels[count_date] = 0

    # Handle trailing streak
    if consecutive >= ANOMALY_CONSECUTIVE_DAYS:
        for d in below_threshold_streak:
            labels[d] = 1

    X_out = []
    y_out = []
    for count_date, features in X_rows:
        X_out.append(features)
        y_out.append(labels.get(count_date, 0))

    return np.array(X_out, dtype=np.float32), np.array(y_out, dtype=np.int64)


# ---------------------------------------------------------------------------
# Training and export
# ---------------------------------------------------------------------------

def train_and_export(
    X: np.ndarray,
    y: np.ndarray,
    output_path: str,
    prev_model_path: str | None = None,
) -> bool:
    """Train a flock anomaly classifier and export to ONNX.

    Implements:
    - Insufficient-data guard (< 50 samples → skip)
    - Regression protection (D-08): keep previous model if new model is worse
    - Model versioning: previous model saved as .prev.onnx

    Args:
        X: Feature matrix, shape [n_samples, N_FEATURES].
        y: Label vector, shape [n_samples] with values 0 or 1.
        output_path: Path to write the new .onnx file.
        prev_model_path: Path to the current best model for regression comparison.

    Returns:
        True if new model was saved, False otherwise.
    """
    n_samples = len(X)

    # Insufficient-data guard
    if n_samples < MIN_SAMPLES:
        logger.error(
            "Insufficient training data for %s: %d samples (minimum %d)",
            MODEL_NAME, n_samples, MIN_SAMPLES,
        )
        return False

    logger.info("Training %s model on %d samples", MODEL_NAME, n_samples)

    unique, counts = np.unique(y, return_counts=True)
    logger.info("Class distribution: %s", dict(zip(unique.tolist(), counts.tolist())))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(unique) > 1 else None
    )

    clf = GradientBoostingClassifier(n_estimators=80, max_depth=3, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    new_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    new_acc = clf.score(X_test, y_test)
    logger.info("New model — accuracy: %.3f, F1-macro: %.3f", new_acc, new_f1)

    # Regression protection (D-08)
    if prev_model_path and os.path.exists(prev_model_path):
        try:
            prev_session = ort.InferenceSession(
                prev_model_path, providers=["CPUExecutionProvider"]
            )
            input_name = prev_session.get_inputs()[0].name
            prev_preds_raw = prev_session.run(None, {input_name: X_test.astype(np.float32)})
            prev_preds = prev_preds_raw[0]
            prev_f1 = f1_score(y_test, prev_preds, average="macro", zero_division=0)
            logger.info("Previous model — F1-macro: %.3f", prev_f1)

            if new_f1 <= prev_f1:
                logger.warning(
                    "Regression detected — keeping previous model "
                    "(new F1-macro %.3f <= previous %.3f)",
                    new_f1, prev_f1,
                )
                return False
        except Exception as exc:
            logger.warning("Could not evaluate previous model: %s — proceeding with new model", exc)

    # Export to ONNX
    initial_type = [("float_input", FloatTensorType([None, N_FEATURES]))]
    onx = convert_sklearn(clf, initial_types=initial_type, target_opset=12)
    onnx.checker.check_model(onx)

    # Archive previous model as .prev.onnx
    if os.path.exists(output_path):
        prev_versioned = output_path.replace(".onnx", ".prev.onnx")
        shutil.copy2(output_path, prev_versioned)
        logger.info("Previous model archived as %s", prev_versioned)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(onx.SerializeToString())

    logger.info("Saved new model to %s", output_path)
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    import asyncpg
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://farm:farm_local_dev@localhost:5432/farmdb",
    )
    db_pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=3)

    try:
        X, y = await fetch_training_data(db_pool)
        if X is None:
            logger.error("No training data returned — aborting")
            return

        output_path = os.path.join(MODELS_DIR, f"{MODEL_NAME}.onnx")
        train_and_export(X, y, output_path, prev_model_path=output_path)
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
