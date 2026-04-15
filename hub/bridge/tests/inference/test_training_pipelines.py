"""Unit tests for training pipeline logic.

Tests focus on:
1. Regression protection (D-08) — new model kept only if it outperforms current
2. Insufficient-data guard — training skipped when fewer than 50 samples
3. ONNX export validation — exported model is valid and accepts correct input shape

Uses pytest.importorskip("sklearn") so tests skip gracefully when scikit-learn
is not installed.

All tests use the zone_health pipeline as the representative implementation.
Separate entry-point import tests confirm irrigation and flock_anomaly scripts
are importable.
"""
import os
import sys
import shutil
import logging

import pytest

# Ensure bridge source is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_separable_data(n_samples=100, n_features=12, n_classes=3, seed=0):
    """Generate clearly separable synthetic data with n_samples >= 50."""
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(seed)
    n_per_class = n_samples // n_classes
    chunks_X, chunks_y = [], []
    for cls in range(n_classes):
        low = cls * (1.0 / n_classes) + 0.02
        high = (cls + 1) * (1.0 / n_classes) - 0.02
        x_chunk = rng.uniform(low, high, (n_per_class, n_features)).astype("float32")
        chunks_X.append(x_chunk)
        chunks_y.append([cls] * n_per_class)
    X = np.vstack(chunks_X)
    y = np.array([item for sub in chunks_y for item in sub], dtype="int64")
    return X, y


def _make_random_data(n_samples=100, n_features=12, n_classes=3, seed=99):
    """Generate random (non-separable) data with n_samples >= 50."""
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(seed)
    X = rng.random((n_samples, n_features)).astype("float32")
    y = rng.integers(0, n_classes, n_samples).astype("int64")
    return X, y


# ---------------------------------------------------------------------------
# Test 1: train_and_export with no prev_model_path trains and saves, returns True
# ---------------------------------------------------------------------------

def test_train_and_export_no_prev_saves_model(tmp_path):
    """train_and_export() with no prev_model_path saves new model and returns True."""
    pytest.importorskip("sklearn")
    from inference.training.train_zone_health import train_and_export

    X, y = _make_separable_data(n_samples=100)
    output_path = str(tmp_path / "zone_health.onnx")

    result = train_and_export(X, y, output_path, prev_model_path=None)

    assert result is True
    assert os.path.exists(output_path), "Model file should have been created"


# ---------------------------------------------------------------------------
# Test 2: Better new model saves and archives previous as .prev.onnx
# ---------------------------------------------------------------------------

def test_train_and_export_better_model_saves_and_archives(tmp_path):
    """train_and_export() with prev_model where new model is BETTER saves new model
    and renames previous to .prev.onnx."""
    pytest.importorskip("sklearn")
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import onnx

    from inference.training.train_zone_health import train_and_export

    # Step 1: create a "worse" previous model trained on random noise
    X_noise, y_noise = _make_random_data(n_samples=100, seed=7)
    noise_clf = GradientBoostingClassifier(n_estimators=5, max_depth=1, random_state=7)
    noise_clf.fit(X_noise, y_noise)
    initial_type = [("float_input", FloatTensorType([None, 12]))]
    onx = convert_sklearn(noise_clf, initial_types=initial_type, target_opset=12)
    onnx.checker.check_model(onx)
    output_path = str(tmp_path / "zone_health.onnx")
    with open(output_path, "wb") as f:
        f.write(onx.SerializeToString())

    # Step 2: train new model on clearly separable data (should be better)
    X_good, y_good = _make_separable_data(n_samples=120)
    result = train_and_export(X_good, y_good, output_path, prev_model_path=output_path)

    assert result is True, "New better model should be saved"
    assert os.path.exists(output_path), "New model file should exist"
    assert os.path.exists(output_path.replace(".onnx", ".prev.onnx")), \
        "Previous model should be archived as .prev.onnx"


# ---------------------------------------------------------------------------
# Test 3: Worse new model triggers regression protection, returns False
# ---------------------------------------------------------------------------

def test_train_and_export_regression_detected_returns_false(tmp_path, caplog):
    """train_and_export() with prev_model where new model is WORSE keeps previous
    model and logs 'Regression detected', returns False.

    Strategy: both the previous and new model are evaluated on the same test split
    from the same separable data. The "new" model is given randomly shuffled labels
    (so it learns nothing useful) while the previous model is trained on the correct
    labels — making the previous model definitively better on the shared test split.
    """
    pytest.importorskip("sklearn")
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import onnx

    from inference.training.train_zone_health import train_and_export

    # Use same base data for both models so the previous model's advantage is
    # measured on the SAME test split that train_and_export will use internally.
    X_base, y_correct = _make_separable_data(n_samples=150)

    # Step 1: train a GOOD previous model on correct labels
    good_clf = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    good_clf.fit(X_base, y_correct)
    initial_type = [("float_input", FloatTensorType([None, 12]))]
    onx = convert_sklearn(good_clf, initial_types=initial_type, target_opset=12)
    onnx.checker.check_model(onx)
    output_path = str(tmp_path / "zone_health.onnx")
    with open(output_path, "wb") as f:
        f.write(onx.SerializeToString())

    # Record original model content for Test 4
    with open(output_path, "rb") as f:
        original_content = f.read()

    # Step 2: attempt "upgrade" with same X but randomised labels — model learns nothing
    rng = np.random.default_rng(999)
    y_shuffled = rng.permutation(y_correct)  # same distribution, random assignment

    with caplog.at_level(logging.WARNING, logger="inference.training.train_zone_health"):
        result = train_and_export(X_base, y_shuffled, output_path, prev_model_path=output_path)

    assert result is False, "Worse model should not be saved"
    assert any("Regression detected" in record.message for record in caplog.records), \
        "Should log 'Regression detected'"

    # Verify original file unchanged (Test 4 requirement combined here)
    with open(output_path, "rb") as f:
        current_content = f.read()
    assert current_content == original_content, \
        "Original .onnx file must be unchanged after regression protection"


# ---------------------------------------------------------------------------
# Test 4: After regression protection, original .onnx is unchanged on disk
# (covered inline in test_train_and_export_regression_detected_returns_false)
# Explicit standalone test for clarity:
# ---------------------------------------------------------------------------

def test_regression_protection_leaves_original_file_unchanged(tmp_path):
    """After regression protection triggers, the original .onnx file is unchanged.

    Uses same base data with shuffled labels so the previous model is definitively
    better on the shared test split (same strategy as test 3).
    """
    pytest.importorskip("sklearn")
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import onnx
    import hashlib

    from inference.training.train_zone_health import train_and_export

    # Create a good previous model on separable data
    X_base, y_correct = _make_separable_data(n_samples=150)
    clf = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=1)
    clf.fit(X_base, y_correct)
    initial_type = [("float_input", FloatTensorType([None, 12]))]
    onx = convert_sklearn(clf, initial_types=initial_type, target_opset=12)
    output_path = str(tmp_path / "zone_health.onnx")
    with open(output_path, "wb") as f:
        f.write(onx.SerializeToString())

    original_hash = hashlib.md5(open(output_path, "rb").read()).hexdigest()

    # Attempt to replace with model trained on same X but randomised labels
    rng = np.random.default_rng(777)
    y_shuffled = rng.permutation(y_correct)
    train_and_export(X_base, y_shuffled, output_path, prev_model_path=output_path)

    new_hash = hashlib.md5(open(output_path, "rb").read()).hexdigest()
    assert original_hash == new_hash, "File must not be modified when regression protection triggers"


# ---------------------------------------------------------------------------
# Test 5: Insufficient-data guard — fewer than 50 samples logs error, returns False
# ---------------------------------------------------------------------------

def test_insufficient_data_guard_returns_false(tmp_path, caplog):
    """train_and_export() with X having fewer than 50 samples logs error and returns False."""
    pytest.importorskip("sklearn")
    import numpy as np

    from inference.training.train_zone_health import train_and_export

    rng = np.random.default_rng(0)
    X = rng.random((49, 12)).astype("float32")  # 49 samples — below threshold
    y = rng.integers(0, 3, 49).astype("int64")

    output_path = str(tmp_path / "zone_health.onnx")

    with caplog.at_level(logging.ERROR, logger="inference.training.train_zone_health"):
        result = train_and_export(X, y, output_path, prev_model_path=None)

    assert result is False, "Should return False for insufficient data"
    assert not os.path.exists(output_path), "Should not create model file"
    assert any("Insufficient training data" in record.message for record in caplog.records), \
        "Should log 'Insufficient training data'"


# ---------------------------------------------------------------------------
# Test 6: Exactly 50 samples proceeds with training (boundary case)
# ---------------------------------------------------------------------------

def test_exactly_50_samples_proceeds(tmp_path):
    """train_and_export() with exactly 50 samples proceeds with training."""
    pytest.importorskip("sklearn")
    import numpy as np

    from inference.training.train_zone_health import train_and_export

    # 50 samples with 3 classes — build enough of each class for stratified split
    rng = np.random.default_rng(0)
    n_per_class = 17  # 17 * 3 = 51... use 50 total with slight imbalance
    X_parts, y_parts = [], []
    for cls in range(3):
        n = 17 if cls < 2 else 16  # 17 + 17 + 16 = 50
        x_part = rng.uniform(
            cls / 3 + 0.05, (cls + 1) / 3 - 0.05, (n, 12)
        ).astype("float32")
        X_parts.append(x_part)
        y_parts.extend([cls] * n)
    X = np.vstack(X_parts)
    y = np.array(y_parts, dtype="int64")
    assert len(X) == 50

    output_path = str(tmp_path / "zone_health.onnx")
    result = train_and_export(X, y, output_path, prev_model_path=None)

    assert result is True, "Should train successfully with exactly 50 samples"
    assert os.path.exists(output_path), "Model file should be created"


# ---------------------------------------------------------------------------
# Test 7: Exported model is valid .onnx (passes onnx.checker.check_model)
# ---------------------------------------------------------------------------

def test_exported_model_passes_onnx_checker(tmp_path):
    """train_and_export() produces a valid .onnx file that passes onnx.checker."""
    pytest.importorskip("sklearn")
    import onnx

    from inference.training.train_zone_health import train_and_export

    X, y = _make_separable_data(n_samples=100)
    output_path = str(tmp_path / "zone_health.onnx")
    result = train_and_export(X, y, output_path)

    assert result is True
    model = onnx.load(output_path)
    onnx.checker.check_model(model)  # Raises if invalid


# ---------------------------------------------------------------------------
# Test 8: Exported model accepts correct input shape per domain
# ---------------------------------------------------------------------------

def test_zone_health_model_accepts_12_features(tmp_path):
    """zone_health model accepts 12 input features."""
    pytest.importorskip("sklearn")
    import numpy as np
    import onnxruntime as ort

    from inference.training.train_zone_health import train_and_export, N_FEATURES

    assert N_FEATURES == 12
    X, y = _make_separable_data(n_samples=100, n_features=12)
    output_path = str(tmp_path / "zone_health.onnx")
    train_and_export(X, y, output_path)

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    test_input = np.array([[0.5] * 12], dtype=np.float32)
    outputs = session.run(None, {input_name: test_input})
    assert outputs is not None and len(outputs) > 0


def test_irrigation_model_accepts_12_features(tmp_path):
    """irrigation model accepts 12 input features."""
    pytest.importorskip("sklearn")
    import numpy as np
    import onnxruntime as ort

    from inference.training.train_irrigation import train_and_export, N_FEATURES

    assert N_FEATURES == 12
    X, y = _make_separable_data(n_samples=100, n_features=12, n_classes=2)
    output_path = str(tmp_path / "irrigation.onnx")
    train_and_export(X, y, output_path)

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    test_input = np.array([[0.5] * 12], dtype=np.float32)
    outputs = session.run(None, {input_name: test_input})
    assert outputs is not None and len(outputs) > 0


def test_flock_anomaly_model_accepts_8_features(tmp_path):
    """flock_anomaly model accepts 8 input features."""
    pytest.importorskip("sklearn")
    import numpy as np
    import onnxruntime as ort

    from inference.training.train_flock_anomaly import train_and_export, N_FEATURES

    assert N_FEATURES == 8
    X, y = _make_separable_data(n_samples=100, n_features=8, n_classes=2)
    output_path = str(tmp_path / "flock_anomaly.onnx")
    train_and_export(X, y, output_path)

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    test_input = np.array([[0.5] * 8], dtype=np.float32)
    outputs = session.run(None, {input_name: test_input})
    assert outputs is not None and len(outputs) > 0


# ---------------------------------------------------------------------------
# Entry-point import tests for irrigation and flock_anomaly
# ---------------------------------------------------------------------------

def test_irrigation_train_and_export_callable():
    """train_irrigation.train_and_export is importable and callable."""
    pytest.importorskip("sklearn")
    from inference.training.train_irrigation import train_and_export
    assert callable(train_and_export)


def test_flock_anomaly_train_and_export_callable():
    """train_flock_anomaly.train_and_export is importable and callable."""
    pytest.importorskip("sklearn")
    from inference.training.train_flock_anomaly import train_and_export
    assert callable(train_and_export)
