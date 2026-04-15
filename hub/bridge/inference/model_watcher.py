"""Filesystem watcher for ONNX model hot-reload (D-09).

Uses watchdog to monitor the models/ directory for new or replaced .onnx files.
When a file appears, it is validated with onnx.checker.check_model() before being
loaded into the running InferenceService instance. Invalid files are logged and
skipped — the currently loaded model continues to serve inference.

The Observer runs in a daemon thread, which is compatible with the asyncio bridge
event loop (it does not interact with asyncio internals directly).

Per 04-RESEARCH.md Pattern 5: PatternMatchingEventHandler with patterns=["*.onnx"],
ignore_patterns=["*.prev.onnx"] to avoid spurious reloads when archiving the
previous model version.

Exports: start_model_watcher
"""
import logging
import os

import onnx
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Map from .onnx filename stem to the inference_services dict key.
# e.g. "zone_health.onnx" -> "zone_health"
_FILENAME_TO_MODEL_NAME = {
    "zone_health.onnx": "zone_health",
    "irrigation.onnx": "irrigation",
    "flock_anomaly.onnx": "flock_anomaly",
}


class OnnxModelHandler(PatternMatchingEventHandler):
    """Watchdog event handler that validates and hot-reloads .onnx files.

    Responds to both file creation and modification events so that the hot-reload
    path works whether the training pipeline creates a new file or overwrites
    an existing one.

    Args:
        inference_services: Dict mapping model_name -> InferenceService instance.
    """

    def __init__(self, inference_services: dict) -> None:
        super().__init__(
            patterns=["*.onnx"],
            ignore_patterns=["*.prev.onnx"],
            ignore_directories=True,
            case_sensitive=False,
        )
        self._inference_services = inference_services

    def _handle_event(self, event_path: str) -> None:
        """Validate and reload the model at *event_path*."""
        filename = os.path.basename(event_path)
        model_name = _FILENAME_TO_MODEL_NAME.get(filename)
        if model_name is None:
            logger.debug("Ignoring unknown model file: %s", filename)
            return

        service = self._inference_services.get(model_name)
        if service is None:
            logger.warning("No InferenceService registered for model: %s", model_name)
            return

        # Validate ONNX before loading into the running service
        try:
            loaded_model = onnx.load(event_path)
            onnx.checker.check_model(loaded_model)
        except Exception as exc:
            logger.error(
                "ONNX validation failed for %s — skipping hot-reload: %s",
                event_path, exc,
            )
            return

        try:
            service.reload(event_path)
            logger.info("Hot-reloaded model %s from %s", model_name, event_path)
        except Exception as exc:
            logger.error("Hot-reload failed for %s: %s", event_path, exc)

    def on_created(self, event) -> None:
        """Called when a new .onnx file appears in the watched directory."""
        self._handle_event(event.src_path)

    def on_modified(self, event) -> None:
        """Called when an existing .onnx file is modified (e.g., overwritten in-place)."""
        self._handle_event(event.src_path)


def start_model_watcher(models_dir: str, inference_services: dict) -> Observer:
    """Start watching *models_dir* for new or updated .onnx files.

    Creates an OnnxModelHandler, schedules it on a non-recursive Observer, and
    starts the Observer daemon thread. The Observer is returned so the caller
    can stop it on shutdown.

    Per 04-RESEARCH.md Pattern 5: Observer runs in a daemon thread and is safe
    to use alongside the asyncio event loop.

    Args:
        models_dir: Absolute path to the directory containing .onnx model files.
        inference_services: Dict mapping model_name -> InferenceService instance.

    Returns:
        The running watchdog Observer instance.
    """
    handler = OnnxModelHandler(inference_services)
    observer = Observer()
    observer.schedule(handler, path=models_dir, recursive=False)
    observer.start()
    logger.info("Model watcher started on %s", models_dir)
    return observer
