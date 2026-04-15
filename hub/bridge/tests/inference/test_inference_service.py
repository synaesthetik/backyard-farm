"""Tests for InferenceService ONNX session management, inference, and hot-reload.

Tests requiring .onnx fixtures use pytest.importorskip("sklearn") so they skip
gracefully if scikit-learn is not installed.
"""
import os
import sys
import tempfile
import threading

import pytest

# Ensure bridge source is on path (mirrors conftest.py pattern)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from inference.inference_service import InferenceService  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tiny_onnx(tmp_path, n_features=12, n_classes=3):
    """Create a tiny scikit-learn RandomForestClassifier, train on clearly
    separable synthetic data, export to .onnx via skl2onnx, and return the
    file path.

    Uses perfectly separable data (feature[0] determines class) so that the
    trained model always predicts with high confidence. This ensures tests can
    verify that infer() returns a result above MIN_CONFIDENCE.

    Requires scikit-learn and skl2onnx. Use pytest.importorskip() before
    calling this.
    """
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import onnx

    rng = np.random.default_rng(0)
    n_per_class = 20
    n_samples = n_per_class * n_classes

    # Build clearly separable data: class determined by which band feature[0] falls in
    chunks_X = []
    chunks_y = []
    for cls in range(n_classes):
        # Each class occupies a distinct, non-overlapping band
        low = cls * (1.0 / n_classes) + 0.05
        high = (cls + 1) * (1.0 / n_classes) - 0.05
        x_chunk = rng.uniform(low, high, (n_per_class, n_features)).astype(np.float32)
        chunks_X.append(x_chunk)
        chunks_y.append(np.full(n_per_class, cls, dtype=np.int64))

    X = np.vstack(chunks_X)
    y = np.concatenate(chunks_y)

    clf = RandomForestClassifier(n_estimators=10, max_depth=5, random_state=0)
    clf.fit(X, y)

    initial_type = [("float_input", FloatTensorType([None, n_features]))]
    onx = convert_sklearn(clf, initial_types=initial_type, target_opset=12)
    onnx.checker.check_model(onx)

    model_path = str(tmp_path / "test_model.onnx")
    with open(model_path, "wb") as f:
        f.write(onx.SerializeToString())
    return model_path


# ---------------------------------------------------------------------------
# Test 1: No model path -> infer() returns None (graceful fallback, D-04)
# ---------------------------------------------------------------------------

def test_no_model_returns_none():
    """InferenceService with no loadable model returns None from infer()."""
    svc = InferenceService("nonexistent_model_xyz")
    assert svc.is_loaded is False
    result = svc.infer([0.5] * 12)
    assert result is None


# ---------------------------------------------------------------------------
# Test 2: Valid .onnx file -> loads session; infer() returns (prediction, confidence)
# ---------------------------------------------------------------------------

def test_valid_onnx_loads_and_infers(tmp_path):
    """InferenceService with valid .onnx file loads and infer() returns tuple."""
    sklearn = pytest.importorskip("sklearn")
    model_path = _make_tiny_onnx(tmp_path, n_features=12, n_classes=3)

    svc = InferenceService.__new__(InferenceService)
    svc._lock = threading.Lock()
    svc._session = None
    svc._model_path = None
    svc._input_name = None
    svc._output_names = None
    svc._load(model_path)

    assert svc.is_loaded is True
    result = svc.infer([0.5] * 12)
    assert result is not None
    pred, conf = result
    assert isinstance(pred, (int, float))
    # Allow tiny float32 rounding errors (e.g., 1.0000001)
    assert -0.001 <= conf <= 1.001


# ---------------------------------------------------------------------------
# Test 3: reload() swaps session atomically
# ---------------------------------------------------------------------------

def test_reload_swaps_session(tmp_path):
    """InferenceService.reload() swaps session; old session no longer referenced."""
    pytest.importorskip("sklearn")
    model_path_1 = _make_tiny_onnx(tmp_path, n_features=12, n_classes=3)

    import shutil
    model_path_2 = str(tmp_path / "test_model_v2.onnx")
    shutil.copy(model_path_1, model_path_2)

    svc = InferenceService.__new__(InferenceService)
    svc._lock = threading.Lock()
    svc._session = None
    svc._model_path = None
    svc._input_name = None
    svc._output_names = None
    svc._load(model_path_1)

    session_before = svc._session
    svc.reload(model_path_2)
    session_after = svc._session

    # Sessions should be different objects
    assert session_before is not session_after
    assert svc._model_path == model_path_2


# ---------------------------------------------------------------------------
# Test 4: infer() is thread-safe
# ---------------------------------------------------------------------------

def test_infer_thread_safe(tmp_path):
    """Concurrent infer() calls don't crash under threading.Lock."""
    pytest.importorskip("sklearn")
    model_path = _make_tiny_onnx(tmp_path, n_features=12, n_classes=3)

    svc = InferenceService.__new__(InferenceService)
    svc._lock = threading.Lock()
    svc._session = None
    svc._model_path = None
    svc._input_name = None
    svc._output_names = None
    svc._load(model_path)

    errors = []
    results = []

    def worker():
        try:
            r = svc.infer([0.3] * 12)
            results.append(r)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Thread errors: {errors}"
    assert len(results) == 20


# ---------------------------------------------------------------------------
# Test 5: format_zone_health_result() matches compute_health_score() shape
# ---------------------------------------------------------------------------

def test_format_zone_health_result_shape():
    """format_zone_health_result() returns dict matching compute_health_score() shape."""
    svc = InferenceService("nonexistent_model_xyz")
    result = svc.format_zone_health_result(
        zone_id="zone-01",
        prediction=0,
        confidence=0.85,
        feature_names=["moisture", "ph", "temperature"],
    )
    assert result["type"] == "zone_health_score"
    assert result["zone_id"] == "zone-01"
    assert result["score"] in ("green", "yellow", "red")
    assert "contributing_sensors" in result
    assert result["source"] == "ai"


# ---------------------------------------------------------------------------
# Test 6: format_recommendation() returns dict matching RuleEngine shape + "source": "ai"
# ---------------------------------------------------------------------------

def test_format_recommendation_shape():
    """format_recommendation() returns dict with same keys as RuleEngine plus source."""
    svc = InferenceService("nonexistent_model_xyz")
    result = svc.format_recommendation(
        zone_id="zone-01",
        rec_type="irrigate",
        prediction=1,
        confidence=0.80,
        sensor_summary="Moisture: 22.0% VWC",
    )
    assert result is not None
    assert "recommendation_id" in result
    assert result["zone_id"] == "zone-01"
    assert result["rec_type"] == "irrigate"
    assert "action_description" in result
    assert "sensor_reading" in result
    assert "explanation" in result
    assert result["source"] == "ai"


# ---------------------------------------------------------------------------
# Test 7: infer() returns None when confidence < MIN_CONFIDENCE
# ---------------------------------------------------------------------------

def test_infer_returns_none_on_low_confidence(tmp_path, monkeypatch):
    """infer() returns None when confidence is below MIN_CONFIDENCE threshold."""
    pytest.importorskip("sklearn")
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import onnx

    # Train model on random data so confidence will be uniformly distributed
    rng = np.random.default_rng(42)
    X = rng.random((30, 12)).astype(np.float32)
    y = rng.integers(0, 3, 30)
    clf = RandomForestClassifier(n_estimators=3, max_depth=1, random_state=42)
    clf.fit(X, y)

    initial_type = [("float_input", FloatTensorType([None, 12]))]
    onx = convert_sklearn(clf, initial_types=initial_type, target_opset=12)
    onnx.checker.check_model(onx)
    model_path = str(tmp_path / "low_conf.onnx")
    with open(model_path, "wb") as f:
        f.write(onx.SerializeToString())

    # Force MIN_CONFIDENCE to 1.0 so any confidence fails
    monkeypatch.setattr("inference.inference_service.MIN_CONFIDENCE", 1.0)

    svc = InferenceService.__new__(InferenceService)
    svc._lock = threading.Lock()
    svc._session = None
    svc._model_path = None
    svc._input_name = None
    svc._output_names = None
    svc._load(model_path)

    result = svc.infer([0.5] * 12)
    assert result is None, f"Expected None for low confidence, got {result}"


# ---------------------------------------------------------------------------
# Extra: source field is "ai" in both format methods
# ---------------------------------------------------------------------------

def test_source_field_is_ai_in_both_format_methods():
    """source field must always be 'ai' in format_zone_health_result and format_recommendation."""
    svc = InferenceService("nonexistent_model_xyz")

    health = svc.format_zone_health_result("zone-02", 2, 0.9, ["moisture"])
    assert health["source"] == "ai"

    rec = svc.format_recommendation("zone-02", "irrigate", 1, 0.85, "summary")
    assert rec is not None
    assert rec["source"] == "ai"
