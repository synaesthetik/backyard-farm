"""Training pipeline for the irrigation recommendation model.

Trains a GradientBoostingClassifier to predict whether irrigation is needed
(0=no action, 1=irrigate) from 12 aggregated zone sensor features.

AI-06 compliance: Only GOOD-flagged sensor data is used for training.
D-08 compliance: Regression protection keeps the previous model if the new
                 model's F1-macro score is not better than the current model.
D-08 compliance: Model versioning retains the last 2 versions (.onnx + .prev.onnx).

Feature vector (12 features):
  moisture [mean, min, max, std], ph [mean, min, max, std],
  temperature [mean, min, max, std]

Labels: 1 if zone was irrigated within 2 hours of a reading window, else 0.
        Falls back to VWC threshold logic if no irrigation history exists.

Output: hub/models/irrigation.onnx
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

MODEL_NAME = "irrigation"
N_FEATURES = 12
MIN_SAMPLES = 50

MODELS_DIR = os.getenv(
    "MODELS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"),
)

# VWC threshold fallback (mirrors RuleEngine default logic)
_VWC_LOW_THRESHOLD_DEFAULT = 30.0


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

async def fetch_training_data(db_pool) -> tuple:
    """Fetch and aggregate GOOD-flagged sensor data for irrigation training.

    Labels are derived from historical irrigation events: if a zone was
    irrigated within 2 hours of a reading window, label=1; otherwise label=0.
    Falls back to VWC threshold logic (moisture_mean < 30%) if no irrigation
    history is available.

    Args:
        db_pool: asyncpg connection pool.

    Returns:
        (X: np.ndarray shape [n_samples, 12], y: np.ndarray shape [n_samples])
        Returns (None, None) if insufficient data.
    """
    sql = """
        SELECT
            sr.zone_id,
            time_bucket('1 hour', sr.time) AS bucket,
            -- moisture features
            AVG(sr.value) FILTER (WHERE sr.sensor_type = 'moisture') AS moisture_mean,
            MIN(sr.value) FILTER (WHERE sr.sensor_type = 'moisture') AS moisture_min,
            MAX(sr.value) FILTER (WHERE sr.sensor_type = 'moisture') AS moisture_max,
            STDDEV(sr.value) FILTER (WHERE sr.sensor_type = 'moisture') AS moisture_std,
            -- ph features
            AVG(sr.value) FILTER (WHERE sr.sensor_type = 'ph') AS ph_mean,
            MIN(sr.value) FILTER (WHERE sr.sensor_type = 'ph') AS ph_min,
            MAX(sr.value) FILTER (WHERE sr.sensor_type = 'ph') AS ph_max,
            STDDEV(sr.value) FILTER (WHERE sr.sensor_type = 'ph') AS ph_std,
            -- temperature features
            AVG(sr.value) FILTER (WHERE sr.sensor_type = 'temperature') AS temp_mean,
            MIN(sr.value) FILTER (WHERE sr.sensor_type = 'temperature') AS temp_min,
            MAX(sr.value) FILTER (WHERE sr.sensor_type = 'temperature') AS temp_max,
            STDDEV(sr.value) FILTER (WHERE sr.sensor_type = 'temperature') AS temp_std,
            -- irrigation event within 2 hours of this bucket
            BOOL_OR(
                EXISTS (
                    SELECT 1 FROM actuator_commands ac
                    WHERE ac.zone_id = sr.zone_id
                      AND ac.command_type = 'irrigate'
                      AND ac.action = 'open'
                      AND ac.created_at BETWEEN time_bucket('1 hour', sr.time)
                                             AND time_bucket('1 hour', sr.time) + INTERVAL '2 hours'
                )
            ) AS irrigated
        FROM sensor_readings sr
        WHERE sr.quality = 'GOOD'
          AND sr.sensor_type IN ('moisture', 'ph', 'temperature')
        GROUP BY sr.zone_id, bucket
        ORDER BY sr.zone_id, bucket
    """
    try:
        rows = await db_pool.fetch(sql)
    except Exception as exc:
        # actuator_commands table may not exist in early dev — fall back to simple query
        logger.warning("Irrigation history query failed: %s — falling back to threshold labels", exc)
        rows = await _fetch_threshold_fallback(db_pool)

    X_rows = []
    y_rows = []

    for row in rows:
        features = [
            row["moisture_mean"] or 0.0,
            row["moisture_min"] or 0.0,
            row["moisture_max"] or 0.0,
            row["moisture_std"] or 0.0,
            row["ph_mean"] or 0.0,
            row["ph_min"] or 0.0,
            row["ph_max"] or 0.0,
            row["ph_std"] or 0.0,
            row["temp_mean"] or 0.0,
            row["temp_min"] or 0.0,
            row["temp_max"] or 0.0,
            row["temp_std"] or 0.0,
        ]

        # Prefer irrigation event label; fall back to threshold
        irrigated = row.get("irrigated")
        if irrigated is not None:
            label = 1 if irrigated else 0
        else:
            moisture = row["moisture_mean"]
            label = 1 if (moisture is not None and moisture < _VWC_LOW_THRESHOLD_DEFAULT) else 0

        X_rows.append(features)
        y_rows.append(label)

    if not X_rows:
        return None, None

    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int64)


async def _fetch_threshold_fallback(db_pool):
    """Fallback query when actuator_commands table is unavailable."""
    sql = """
        SELECT
            zone_id,
            time_bucket('1 hour', time) AS bucket,
            AVG(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_mean,
            MIN(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_min,
            MAX(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_max,
            STDDEV(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_std,
            AVG(value) FILTER (WHERE sensor_type = 'ph') AS ph_mean,
            MIN(value) FILTER (WHERE sensor_type = 'ph') AS ph_min,
            MAX(value) FILTER (WHERE sensor_type = 'ph') AS ph_max,
            STDDEV(value) FILTER (WHERE sensor_type = 'ph') AS ph_std,
            AVG(value) FILTER (WHERE sensor_type = 'temperature') AS temp_mean,
            MIN(value) FILTER (WHERE sensor_type = 'temperature') AS temp_min,
            MAX(value) FILTER (WHERE sensor_type = 'temperature') AS temp_max,
            STDDEV(value) FILTER (WHERE sensor_type = 'temperature') AS temp_std
        FROM sensor_readings
        WHERE quality = 'GOOD'
          AND sensor_type IN ('moisture', 'ph', 'temperature')
        GROUP BY zone_id, bucket
        ORDER BY zone_id, bucket
    """
    return await db_pool.fetch(sql)


# ---------------------------------------------------------------------------
# Training and export
# ---------------------------------------------------------------------------

def train_and_export(
    X: np.ndarray,
    y: np.ndarray,
    output_path: str,
    prev_model_path: str | None = None,
) -> bool:
    """Train an irrigation classifier and export to ONNX.

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

    clf = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
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
