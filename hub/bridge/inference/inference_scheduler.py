"""APScheduler-based inference scheduler for ONNX models (AI-03, D-07).

Runs three domain inference jobs on periodic intervals:
  - zone_health:    every 15 minutes
  - irrigation:     every 1 hour
  - flock_anomaly:  every 30 minutes

Runs three weekly retraining cron jobs (D-07 — automated, no farmer intervention):
  - retrain_zone_health:   Sunday 02:00 UTC
  - retrain_irrigation:    Sunday 02:20 UTC  (staggered by 20min to avoid CPU contention)
  - retrain_flock_anomaly: Sunday 02:40 UTC

Threshold-crossing re-inference: trigger_zone_reinference() can be called from
the bridge's sensor delta handler to immediately re-run zone health and irrigation
inference for a specific zone after a threshold crossing.

All inference methods check:
  1. ai_settings.get_mode(domain) — skip if "rules" (D-06 runtime toggle)
  2. inference_services[domain].is_loaded — skip if no model loaded (D-04)
  3. feature_aggregator.check_data_maturity(zone_id) — skip if gate not passed (D-01)

Exports: InferenceScheduler
"""
import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

MODELS_DIR = os.getenv(
    "MODELS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "models"),
)

# Zone-level sensor types used for feature aggregation
_ZONE_SENSOR_TYPES = ["moisture", "ph", "temperature"]
# Flock-level sensor types
_FLOCK_SENSOR_TYPES = ["feed_weight", "nesting_box_weight", "water_level"]


class InferenceScheduler:
    """APScheduler-based orchestrator for periodic ONNX inference and weekly retraining.

    Args:
        db_pool: asyncpg connection pool (passed to training pipelines).
        feature_aggregator: FeatureAggregator instance for live feature queries.
        inference_services: Dict mapping model_name -> InferenceService.
        maturity_tracker: MaturityTracker instance for recording recommendations.
        ai_settings: AISettings instance (checked before every inference cycle).
        zone_config_store: ZoneConfigStore instance (iterable, provides zone_ids).
        notify_callback: Async callable that accepts a delta dict and broadcasts it.
    """

    def __init__(
        self,
        db_pool,
        feature_aggregator,
        inference_services: dict,
        maturity_tracker,
        ai_settings,
        zone_config_store,
        notify_callback,
    ) -> None:
        self._db_pool = db_pool
        self._feature_aggregator = feature_aggregator
        self._inference_services = inference_services
        self._maturity_tracker = maturity_tracker
        self._ai_settings = ai_settings
        self._zone_config_store = zone_config_store
        self._notify_callback = notify_callback

        # APScheduler 3.x AsyncIOScheduler — runs cooperatively in the asyncio event loop.
        # coalesce=True: if a job is still running when the next fire time arrives, skip
        #                the pending fire rather than stacking executions.
        # max_instances=1: never run more than one concurrent execution of the same job.
        self._scheduler = AsyncIOScheduler(
            job_defaults={"coalesce": True, "max_instances": 1}
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Register all inference interval jobs and weekly retraining cron jobs, then start.

        Per 04-RESEARCH.md Pattern 4: start() must be called inside an async context
        so that AsyncIOScheduler can attach to the running event loop.
        """
        # ---- Periodic inference jobs ----
        self._scheduler.add_job(
            self.run_zone_health_inference,
            "interval",
            minutes=15,
            id="zone_health_inference",
        )
        self._scheduler.add_job(
            self.run_irrigation_inference,
            "interval",
            hours=1,
            id="irrigation_inference",
        )
        self._scheduler.add_job(
            self.run_flock_anomaly_inference,
            "interval",
            minutes=30,
            id="flock_anomaly_inference",
        )

        # ---- Weekly retraining cron jobs (D-07) ----
        # Staggered by 20 minutes to avoid concurrent CPU load on hub hardware.
        self._scheduler.add_job(
            self.run_retrain_zone_health,
            "cron",
            day_of_week="sun",
            hour=2,
            minute=0,
            id="retrain_zone_health",
        )
        self._scheduler.add_job(
            self.run_retrain_irrigation,
            "cron",
            day_of_week="sun",
            hour=2,
            minute=20,
            id="retrain_irrigation",
        )
        self._scheduler.add_job(
            self.run_retrain_flock_anomaly,
            "cron",
            day_of_week="sun",
            hour=2,
            minute=40,
            id="retrain_flock_anomaly",
        )

        self._scheduler.start()
        logger.info(
            "InferenceScheduler started: 3 inference jobs (15m/1h/30m) + 3 weekly retraining jobs"
        )

    def stop(self) -> None:
        """Shut down the APScheduler without waiting for running jobs."""
        self._scheduler.shutdown(wait=False)
        logger.info("InferenceScheduler stopped")

    # ------------------------------------------------------------------
    # Weekly retraining (D-07)
    # ------------------------------------------------------------------

    async def run_retrain_zone_health(self) -> None:
        """Weekly cron: retrain zone_health model from latest GOOD-flagged data.

        The model watcher (watchdog) will automatically detect the new .onnx file
        and hot-reload it into InferenceService — no manual reload call needed here.
        """
        logger.info("Weekly retraining: zone_health")
        try:
            from inference.training import train_zone_health
            X, y = await train_zone_health.fetch_training_data(self._db_pool)
            if X is None or len(X) < 50:
                logger.warning("Insufficient data for zone_health retraining (got %s samples)", len(X) if X is not None else 0)
                return
            output_path = os.path.join(MODELS_DIR, "zone_health.onnx")
            prev_path = output_path if os.path.exists(output_path) else None
            success = train_zone_health.train_and_export(X, y, output_path, prev_model_path=prev_path)
            logger.info(
                "Weekly retrain zone_health: %s",
                "updated" if success else "kept previous (regression protection)",
            )
        except Exception as exc:
            logger.error("Weekly retraining zone_health failed: %s", exc)

    async def run_retrain_irrigation(self) -> None:
        """Weekly cron: retrain irrigation model from latest GOOD-flagged data."""
        logger.info("Weekly retraining: irrigation")
        try:
            from inference.training import train_irrigation
            X, y = await train_irrigation.fetch_training_data(self._db_pool)
            if X is None or len(X) < 50:
                logger.warning("Insufficient data for irrigation retraining (got %s samples)", len(X) if X is not None else 0)
                return
            output_path = os.path.join(MODELS_DIR, "irrigation.onnx")
            prev_path = output_path if os.path.exists(output_path) else None
            success = train_irrigation.train_and_export(X, y, output_path, prev_model_path=prev_path)
            logger.info(
                "Weekly retrain irrigation: %s",
                "updated" if success else "kept previous (regression protection)",
            )
        except Exception as exc:
            logger.error("Weekly retraining irrigation failed: %s", exc)

    async def run_retrain_flock_anomaly(self) -> None:
        """Weekly cron: retrain flock_anomaly model from latest GOOD-flagged data."""
        logger.info("Weekly retraining: flock_anomaly")
        try:
            from inference.training import train_flock_anomaly
            X, y = await train_flock_anomaly.fetch_training_data(self._db_pool)
            if X is None or len(X) < 50:
                logger.warning("Insufficient data for flock_anomaly retraining (got %s samples)", len(X) if X is not None else 0)
                return
            output_path = os.path.join(MODELS_DIR, "flock_anomaly.onnx")
            prev_path = output_path if os.path.exists(output_path) else None
            success = train_flock_anomaly.train_and_export(X, y, output_path, prev_model_path=prev_path)
            logger.info(
                "Weekly retrain flock_anomaly: %s",
                "updated" if success else "kept previous (regression protection)",
            )
        except Exception as exc:
            logger.error("Weekly retraining flock_anomaly failed: %s", exc)

    # ------------------------------------------------------------------
    # Periodic inference jobs
    # ------------------------------------------------------------------

    async def run_zone_health_inference(self) -> None:
        """Run zone health inference for all zones (interval: 15 minutes)."""
        if self._ai_settings.get_mode("zone_health") != "ai":
            return
        if not self._inference_services["zone_health"].is_loaded:
            logger.debug("zone_health model not loaded — skipping inference cycle")
            return

        for zone_id in self._zone_config_store:
            await self._infer_zone_health(zone_id)

    async def run_irrigation_inference(self) -> None:
        """Run irrigation inference for all zones (interval: 1 hour)."""
        if self._ai_settings.get_mode("irrigation") != "ai":
            return
        if not self._inference_services["irrigation"].is_loaded:
            logger.debug("irrigation model not loaded — skipping inference cycle")
            return

        for zone_id in self._zone_config_store:
            await self._infer_irrigation(zone_id)

    async def run_flock_anomaly_inference(self) -> None:
        """Run flock anomaly inference (interval: 30 minutes)."""
        if self._ai_settings.get_mode("flock_anomaly") != "ai":
            return
        if not self._inference_services["flock_anomaly"].is_loaded:
            logger.debug("flock_anomaly model not loaded — skipping inference cycle")
            return

        # Flock uses the coop zone with a 7-day window
        zone_id = "coop"
        try:
            maturity = await self._feature_aggregator.check_data_maturity(zone_id)
            if not maturity["gate_passed"]:
                logger.debug("Data maturity gate not passed for %s — skipping flock_anomaly inference", zone_id)
                return

            features = await self._feature_aggregator.aggregate_zone_features(
                zone_id, _FLOCK_SENSOR_TYPES, window_hours=168  # 7 days
            )
            if features is None:
                logger.debug("Insufficient flock features for %s — skipping", zone_id)
                return

            vector = self._feature_aggregator.build_feature_vector(features, _FLOCK_SENSOR_TYPES)
            result = self._inference_services["flock_anomaly"].infer(vector)
            if result is None:
                logger.debug("flock_anomaly inference below confidence threshold — rule engine handles it")
                return

            prediction, confidence = result
            sensor_summary = (
                f"Feed: {features.get('feed_weight', {}).get('mean_val', 0):.0f}g, "
                f"Water: {features.get('water_level', {}).get('mean_val', 0):.0f}%"
            )
            rec_dict = self._inference_services["flock_anomaly"].format_recommendation(
                zone_id, "flock_anomaly", prediction, confidence, sensor_summary
            )
            if rec_dict is not None:
                self._maturity_tracker.record_recommendation("flock_anomaly", rec_dict["recommendation_id"])
                await self._notify_callback({
                    "type": "recommendation_queue",
                    "recommendations": [rec_dict],
                })
        except Exception as exc:
            logger.error("flock_anomaly inference error for %s: %s", zone_id, exc)

    # ------------------------------------------------------------------
    # Triggered re-inference (threshold crossing)
    # ------------------------------------------------------------------

    async def trigger_zone_reinference(self, zone_id: str) -> None:
        """Immediately re-run zone health and irrigation inference for *zone_id*.

        Called from the bridge's threshold-crossing handler so AI recommendations
        are produced immediately rather than waiting for the next scheduled cycle.
        Each domain check still respects the AI/Rules toggle and maturity gate.

        Args:
            zone_id: The zone that crossed a sensor threshold.
        """
        logger.debug("Triggered re-inference for zone %s", zone_id)
        await self._infer_zone_health(zone_id)
        await self._infer_irrigation(zone_id)

    # ------------------------------------------------------------------
    # Internal per-zone inference helpers
    # ------------------------------------------------------------------

    async def _infer_zone_health(self, zone_id: str) -> None:
        """Run zone health inference for a single zone."""
        if self._ai_settings.get_mode("zone_health") != "ai":
            return
        if not self._inference_services["zone_health"].is_loaded:
            return

        try:
            maturity = await self._feature_aggregator.check_data_maturity(zone_id)
            if not maturity["gate_passed"]:
                return

            features = await self._feature_aggregator.aggregate_zone_features(
                zone_id, _ZONE_SENSOR_TYPES, window_hours=24
            )
            if features is None:
                return

            vector = self._feature_aggregator.build_feature_vector(features, _ZONE_SENSOR_TYPES)
            result = self._inference_services["zone_health"].infer(vector)
            if result is None:
                return

            prediction, confidence = result
            health_dict = self._inference_services["zone_health"].format_zone_health_result(
                zone_id, prediction, confidence, _ZONE_SENSOR_TYPES
            )
            await self._notify_callback(health_dict)
        except Exception as exc:
            logger.error("zone_health inference error for %s: %s", zone_id, exc)

    async def _infer_irrigation(self, zone_id: str) -> None:
        """Run irrigation inference for a single zone."""
        if self._ai_settings.get_mode("irrigation") != "ai":
            return
        if not self._inference_services["irrigation"].is_loaded:
            return

        try:
            maturity = await self._feature_aggregator.check_data_maturity(zone_id)
            if not maturity["gate_passed"]:
                return

            features = await self._feature_aggregator.aggregate_zone_features(
                zone_id, _ZONE_SENSOR_TYPES, window_hours=24
            )
            if features is None:
                return

            vector = self._feature_aggregator.build_feature_vector(features, _ZONE_SENSOR_TYPES)
            result = self._inference_services["irrigation"].infer(vector)
            if result is None:
                return

            prediction, confidence = result
            sensor_summary = (
                f"Moisture: {features.get('moisture', {}).get('mean_val', 0):.1f}% VWC"
            )
            rec_dict = self._inference_services["irrigation"].format_recommendation(
                zone_id, "irrigate", prediction, confidence, sensor_summary
            )
            if rec_dict is not None:
                self._maturity_tracker.record_recommendation("irrigation", rec_dict["recommendation_id"])
                await self._notify_callback({
                    "type": "recommendation_queue",
                    "recommendations": [rec_dict],
                })
        except Exception as exc:
            logger.error("irrigation inference error for %s: %s", zone_id, exc)
