"""REST endpoints for storage stats and manual purge (D-12).

Queries TimescaleDB directly (not proxied to bridge) since these are
read-only DB queries and the API process has its own DB pool.

Endpoints:
  GET  /api/storage/stats  — per-table sizes, retention policy status
  POST /api/storage/purge  — manual drop_chunks for raw data > 90 days

Security (T-05-07): Purge only drops chunks older than 90 days;
cannot delete recent data. LAN-only access.

Exports: router
"""
import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/storage/stats")
async def get_storage_stats():
    """Return per-table sizes and retention policy info from TimescaleDB.

    Queries pg_total_relation_size for accurate on-disk size including
    indexes and TOAST (D-12 — no filesystem walk).
    """
    from main import get_db_pool

    pool = get_db_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool not ready")

    try:
        async with pool.acquire() as conn:
            # Per-table sizes
            table_rows = await conn.fetch(
                """
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size,
                    pg_total_relation_size(schemaname || '.' || tablename) AS size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
                """
            )

            tables = [
                {
                    "schema": row["schemaname"],
                    "table": row["tablename"],
                    "size": row["size"],
                    "size_bytes": row["size_bytes"],
                }
                for row in table_rows
            ]

            total_bytes = sum(t["size_bytes"] for t in tables)

            # Retention policy info from TimescaleDB
            try:
                policy_rows = await conn.fetch(
                    """
                    SELECT
                        hypertable_name,
                        schedule_interval::text,
                        config
                    FROM timescaledb_information.jobs
                    WHERE proc_name = 'policy_retention'
                    """
                )
                retention_policies = [
                    {
                        "hypertable": row["hypertable_name"],
                        "schedule_interval": row["schedule_interval"],
                        "config": dict(row["config"]) if row["config"] else None,
                    }
                    for row in policy_rows
                ]
            except Exception as exc:
                logger.warning("Could not query retention policies: %s", exc)
                retention_policies = []

            # Human-readable total
            size_kb = total_bytes / 1024
            if size_kb < 1024:
                total_size = f"{size_kb:.1f} kB"
            elif size_kb < 1024 * 1024:
                total_size = f"{size_kb / 1024:.1f} MB"
            else:
                total_size = f"{size_kb / (1024 * 1024):.1f} GB"

            return {
                "tables": tables,
                "retention_policies": retention_policies,
                "total_size": total_size,
                "total_bytes": total_bytes,
            }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching storage stats: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/storage/purge")
async def purge_old_data():
    """Manually drop sensor_readings chunks older than 90 days (D-10).

    Executes drop_chunks() directly on TimescaleDB. Only removes chunks
    where all data is older than the 90-day interval — recent data is
    never affected (T-05-07: Tampering mitigation).
    """
    from main import get_db_pool

    pool = get_db_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool not ready")

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "SELECT drop_chunks('sensor_readings', INTERVAL '90 days')"
            )
        logger.info("Manual purge: dropped sensor_readings chunks older than 90 days")
        return {"status": "ok", "message": "Purge complete"}
    except Exception as exc:
        logger.error("Error during manual purge: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
