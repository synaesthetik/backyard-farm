"""Training pipeline for the zone health classification model.

Trains a GradientBoostingClassifier to predict zone health score
(green=0, yellow=1, red=2) from 12 aggregated sensor features.

AI-06 compliance: Only GOOD-flagged sensor data is used for training.
D-08 compliance: Regression protection keeps the previous model if the new
                 model's F1-macro score is not better than the current model.
D-08 compliance: Model versioning retains the last 2 versions (.onnx + .prev.onnx).

Feature vector (12 features):
  moisture [mean, min, max, std], ph [mean, min, max, std],
  temperature [mean, min, max, std]

Output: hub/models/zone_health.onnx
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

MODEL_NAME = "zone_health"
N_FEATURES = 12
LABELS = {0: "green", 1: "yellow", 2: "red"}
MIN_SAMPLES = 50

MODELS_DIR = os.getenv(
    "MODELS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"),
)


# ---------------------------------------------------------------------------
# Feature derivation thresholds (mirrors health_score.py logic)
# ---------------------------------------------------------------------------

def _label_from_features(moisture_mean, ph_mean, temp_mean):
    """Derive green/yellow/red label from feature means using health_score logic.

    This mirrors compute_health_score() threshold logic to generate training labels
    from historical sensor windows without requiring a live zone_config object.
    Uses broadly typical ranges as defaults (farmers can retrain after calibration).
    """
    # Default typical ranges (same structure as health_score.py)
    VWC_LOW, VWC_HIGH = 30.0, 70.0
    PH_LOW, PH_HIGH = 5.5, 7.5
    TEMP_LOW, TEMP_HIGH = 10.0, 35.0

    has_critical = False
    contributing_count = 0

    sensors = [
        (moisture_mean, VWC_LOW, VWC_HIGH),
        (ph_mean, PH_LOW, PH_HIGH),
        (temp_mean, TEMP_LOW, TEMP_HIGH),
    ]

    for value, low, high in sensors:
        if value is None:
            continue
        range_width = high - low
        critical_margin = range_width * 0.3
        if value < (low - critical_margin) or value > (high + critical_margin):
            has_critical = True
            contributing_count += 1
        elif value < low or value > high:
            contributing_count += 1

    if has_critical:
        return 2  # red
    if contributing_count > 0:
        return 1  # yellow
    return 0  # green


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

async def fetch_training_data(db_pool) -> tuple:
    """Fetch and aggregate GOOD-flagged sensor data for training.

    Queries sensor_readings with quality='GOOD' grouped by zone_id and
    1-hour time buckets. For each bucket, computes aggregate features and
    derives a health label using the threshold logic from health_score.py.

    Args:
        db_pool: asyncpg connection pool.

    Returns:
        (X: np.ndarray shape [n_samples, 12], y: np.ndarray shape [n_samples])
        Returns (None, None) if insufficient data.
    """
    sql = """
        SELECT
            zone_id,
            time_bucket('1 hour', time) AS bucket,
            -- moisture features
            AVG(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_mean,
            MIN(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_min,
            MAX(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_max,
            STDDEV(value) FILTER (WHERE sensor_type = 'moisture') AS moisture_std,
            -- ph features
            AVG(value) FILTER (WHERE sensor_type = 'ph') AS ph_mean,
            MIN(value) FILTER (WHERE sensor_type = 'ph') AS ph_min,
            MAX(value) FILTER (WHERE sensor_type = 'ph') AS ph_max,
            STDDEV(value) FILTER (WHERE sensor_type = 'ph') AS ph_std,
            -- temperature features
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
    rows = await db_pool.fetch(sql)

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

        label = _label_from_features(
            row["moisture_mean"],
            row["ph_mean"],
            row["temp_mean"],
        )

        X_rows.append(features)
        y_rows.append(label)

    if not X_rows:
        return None, None

    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int64)


# ---------------------------------------------------------------------------
# Training and export
# ---------------------------------------------------------------------------

def train_and_export(
    X: np.ndarray,
    y: np.ndarray,
    output_path: str,
    prev_model_path: str | None = None,
) -> bool:
    """Train a GradientBoostingClassifier and export to ONNX.

    Implements:
    - Insufficient-data guard (< 50 samples → skip)
    - Regression protection (D-08): keep previous model if new model is worse
    - Model versioning: previous model saved as .prev.onnx

    Args:
        X: Feature matrix, shape [n_samples, N_FEATURES].
        y: Label vector, shape [n_samples].
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

    # Class distribution
    unique, counts = np.unique(y, return_counts=True)
    logger.info("Class distribution: %s", dict(zip(unique.tolist(), counts.tolist())))

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(unique) > 1 else None
    )

    clf = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
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

    # Version previous model as .prev.onnx before overwriting
    if prev_model_path and os.path.exists(prev_model_path) and prev_model_path == output_path:
        prev_versioned = output_path.replace(".onnx", ".prev.onnx")
        shutil.copy2(output_path, prev_versioned)
        logger.info("Previous model archived as %s", prev_versioned)
    elif os.path.exists(output_path):
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
