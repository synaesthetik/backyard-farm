"""Maturity tracker for ONNX recommendation domains (AI-07, D-12, D-13).

Tracks per-domain recommendation counts, approval rates, and rejection rates.
Persists state to the model_maturity TimescaleDB table so counts survive restarts.

Exports: MaturityTracker
"""
from __future__ import annotations

from typing import Optional
import asyncpg


DOMAINS: list[str] = ["irrigation", "zone_health", "flock_anomaly"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS model_maturity (
    domain TEXT PRIMARY KEY,
    recommendation_count INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""

_SELECT_ALL_SQL = "SELECT * FROM model_maturity"

_INSERT_DEFAULT_SQL = """
INSERT INTO model_maturity (domain, recommendation_count, approved_count, rejected_count)
VALUES ($1, 0, 0, 0)
ON CONFLICT (domain) DO NOTHING
"""

_UPSERT_SQL = """
INSERT INTO model_maturity (domain, recommendation_count, approved_count, rejected_count, updated_at)
VALUES ($1, $2, $3, $4, NOW())
ON CONFLICT (domain) DO UPDATE
  SET recommendation_count = EXCLUDED.recommendation_count,
      approved_count        = EXCLUDED.approved_count,
      rejected_count        = EXCLUDED.rejected_count,
      updated_at            = NOW()
"""


class MaturityTracker:
    """Tracks recommendation counts and approval/rejection rates per domain.

    State is stored in memory and persisted to the model_maturity table via
    load_from_db() / persist_to_db(). Call ensure_table() on startup to create
    the table if it does not exist.

    Args:
        db_pool: An asyncpg connection pool.
    """

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool
        # Internal state keyed by domain
        self._state: dict[str, dict[str, int]] = {
            domain: {
                "recommendation_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
            }
            for domain in DOMAINS
        }

    # ------------------------------------------------------------------
    # DB lifecycle
    # ------------------------------------------------------------------

    async def ensure_table(self) -> None:
        """Create the model_maturity table if it does not exist."""
        await self._pool.execute(CREATE_TABLE_SQL)

    async def load_from_db(self) -> None:
        """Load maturity state from the model_maturity table into memory.

        If the table contains no rows, inserts default zero rows for all domains.
        """
        rows = await self._pool.fetch(_SELECT_ALL_SQL)

        if not rows:
            # Seed default rows for all domains
            for domain in DOMAINS:
                await self._pool.execute(_INSERT_DEFAULT_SQL, domain)
            return

        for row in rows:
            domain = row["domain"]
            if domain in self._state:
                self._state[domain] = {
                    "recommendation_count": int(row["recommendation_count"]),
                    "approved_count": int(row["approved_count"]),
                    "rejected_count": int(row["rejected_count"]),
                }

    async def persist_to_db(self) -> None:
        """Write current in-memory state back to the model_maturity table."""
        for domain, counts in self._state.items():
            await self._pool.execute(
                _UPSERT_SQL,
                domain,
                counts["recommendation_count"],
                counts["approved_count"],
                counts["rejected_count"],
            )

    # ------------------------------------------------------------------
    # In-memory mutation methods
    # ------------------------------------------------------------------

    def record_recommendation(self, domain: str, rec_id: str) -> None:
        """Increment recommendation_count for the given domain.

        Args:
            domain: One of DOMAINS.
            rec_id: The recommendation identifier (not stored, just for call signature consistency).
        """
        if domain in self._state:
            self._state[domain]["recommendation_count"] += 1

    def record_approval(self, domain: str) -> None:
        """Increment approved_count for the given domain."""
        if domain in self._state:
            self._state[domain]["approved_count"] += 1

    def record_rejection(self, domain: str) -> None:
        """Increment rejected_count for the given domain."""
        if domain in self._state:
            self._state[domain]["rejected_count"] += 1

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_maturity_state(self, domain: str) -> dict:
        """Return current maturity state for one domain.

        Returns:
            dict with keys: domain, recommendation_count, approved_count,
            rejected_count, approval_rate (float 0.0-1.0).
        """
        counts = self._state.get(domain, {
            "recommendation_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
        })
        rec_count = counts["recommendation_count"]
        approved = counts["approved_count"]
        approval_rate = approved / rec_count if rec_count > 0 else 0.0

        return {
            "domain": domain,
            "recommendation_count": rec_count,
            "approved_count": approved,
            "rejected_count": counts["rejected_count"],
            "approval_rate": approval_rate,
        }

    def get_all_maturity_states(self) -> list[dict]:
        """Return maturity state for all domains.

        Returns:
            List of dicts, one per domain in DOMAINS order.
        """
        return [self.get_maturity_state(domain) for domain in DOMAINS]
