"""ONNX inference service for zone health, irrigation, and flock anomaly models.

Provides:
  - Model loading from disk (ONNX format)
  - Thread-safe inference with confidence threshold (D-04 fallback)
  - Hot-reload support for watchdog-triggered model swaps (D-09)
  - Output formatting compatible with existing RuleEngine and compute_health_score() shapes

Usage:
    svc = InferenceService("zone_health")
    result = svc.infer(feature_vector)  # Returns (prediction, confidence) or None
"""
import logging
import os
import threading
import uuid
from typing import Optional

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

# Minimum confidence required to trust ONNX prediction. Below this threshold
# the service returns None and the caller falls back to rule-based logic (D-04).
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.65"))

# Directory where .onnx model files are stored. Defaults to hub/models/ relative
# to the inference_service.py location (two levels up = bridge/, then ../models/).
MODELS_DIR = os.getenv(
    "MODELS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "models"),
)

# Score label map for zone health classification (index -> label).
_ZONE_HEALTH_LABELS = {0: "green", 1: "yellow", 2: "red"}


class InferenceService:
    """ONNX Runtime inference wrapper with thread-safe hot-reload.

    One instance per model domain (e.g., zone_health, irrigation, flock_anomaly).
    """

    def __init__(self, model_name: str) -> None:
        """Initialise service for a named model.

        Args:
            model_name: Base name of the model (without .onnx extension).
                        The service looks for MODELS_DIR/{model_name}.onnx.
        """
        self._lock = threading.Lock()
        self._session: Optional[ort.InferenceSession] = None
        self._model_path: Optional[str] = None
        self._input_name: Optional[str] = None
        self._output_names: Optional[list] = None

        model_path = os.path.join(MODELS_DIR, f"{model_name}.onnx")
        if os.path.exists(model_path):
            try:
                self._load(model_path)
                logger.info("Loaded model: %s", model_path)
            except Exception as exc:
                logger.error("Failed to load model %s: %s", model_path, exc)
        else:
            logger.info("No model file at %s — running in rules-fallback mode", model_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, model_path: str) -> None:
        """Load (or hot-swap) an ONNX model from *model_path*.

        Creates a new InferenceSession, then under self._lock atomically
        replaces the stored session reference so that concurrent callers of
        infer() see either the old or new session but never a partial state.
        """
        new_session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        input_name = new_session.get_inputs()[0].name
        output_names = [o.name for o in new_session.get_outputs()]

        with self._lock:
            self._session = new_session
            self._model_path = model_path
            self._input_name = input_name
            self._output_names = output_names

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self, model_path: str) -> None:
        """Hot-reload a new model file (called from watchdog handler thread).

        Loads the new session and atomically swaps it in under self._lock.
        """
        self._load(model_path)
        logger.info("Reloaded model from %s", model_path)

    def infer(self, feature_vector: list) -> Optional[tuple]:
        """Run inference on *feature_vector*.

        Acquires self._lock to snapshot the current session reference, then
        releases the lock before running inference so other threads are not
        blocked during (potentially slow) model evaluation.

        Args:
            feature_vector: List of floats with the correct feature count for
                            the loaded model.

        Returns:
            (predicted_class_index: int, confidence: float) or None.
            Returns None if:
              - No model is loaded.
              - The model's max class probability < MIN_CONFIDENCE (D-04 fallback).
        """
        # Snapshot session under lock, then release before inference.
        with self._lock:
            session = self._session
            input_name = self._input_name

        if session is None:
            return None

        arr = np.array([feature_vector], dtype=np.float32)
        outputs = session.run(None, {input_name: arr})

        # outputs[1] contains per-class probabilities for classifiers exported
        # via skl2onnx (shape: [n_samples, n_classes]).
        if len(outputs) < 2:
            # Regression model or unexpected output shape — return raw output.
            return None

        prob_row = outputs[1][0]  # probabilities for the first (only) sample
        # prob_row is a dict {label: prob} when output is a Sequence[Map]; flatten.
        if isinstance(prob_row, dict):
            prob_values = list(prob_row.values())
        else:
            prob_values = list(prob_row)

        confidence = float(max(prob_values))

        if confidence < MIN_CONFIDENCE:
            return None

        predicted_class = int(prob_values.index(max(prob_values)))
        return (predicted_class, confidence)

    def format_zone_health_result(
        self,
        zone_id: str,
        prediction: int,
        confidence: float,
        feature_names: list,
    ) -> dict:
        """Format a zone health prediction into a dict compatible with compute_health_score().

        Args:
            zone_id: Zone identifier.
            prediction: Class index (0=green, 1=yellow, 2=red).
            confidence: Model confidence for the predicted class.
            feature_names: Names of the input features (used to label contributing sensors).

        Returns:
            Dict with keys: type, zone_id, score, contributing_sensors, source.
        """
        score = _ZONE_HEALTH_LABELS.get(prediction, "red")

        # Identify contributing sensors as those at the extremes of the feature list.
        # For simplicity, if the score is not green, mark all sensor groups with data.
        contributing: list[str] = []
        if score != "green":
            # Include non-empty feature name groups as contributing
            sensor_groups = {name.split("_")[0] for name in feature_names if name}
            contributing = sorted(sensor_groups)

        return {
            "type": "zone_health_score",
            "zone_id": zone_id,
            "score": score,
            "contributing_sensors": contributing,
            "source": "ai",
        }

    def format_recommendation(
        self,
        zone_id: str,
        rec_type: str,
        prediction: int,
        confidence: float,
        sensor_summary: str,
    ) -> Optional[dict]:
        """Format an irrigation/flock recommendation dict compatible with RuleEngine.

        Adds "source": "ai" field to distinguish AI-driven recommendations from
        rule-based ones in the dashboard badge system.

        Args:
            zone_id: Zone identifier.
            rec_type: Recommendation type (e.g., "irrigate", "flock_anomaly").
            prediction: 0 = no action needed; 1 = action needed.
            confidence: Model confidence for the predicted action.
            sensor_summary: Human-readable sensor reading summary.

        Returns:
            Recommendation dict (matching RuleEngine shape) or None if no action needed.
        """
        if prediction == 0:
            # Prediction indicates no action needed.
            return None

        description_map = {
            "irrigate": f"Irrigate {zone_id}",
            "zone_health": f"Check {zone_id}",
            "flock_anomaly": "Inspect flock",
        }
        action_description = description_map.get(rec_type, f"AI: action needed for {zone_id}")

        return {
            "recommendation_id": str(uuid.uuid4()),
            "zone_id": zone_id,
            "rec_type": rec_type,
            "action_description": f"AI: {action_description}",
            "sensor_reading": sensor_summary,
            "explanation": f"AI model confidence: {confidence:.0%}",
            "source": "ai",
        }

    @property
    def is_loaded(self) -> bool:
        """True if an ONNX model is currently loaded and ready for inference."""
        return self._session is not None
