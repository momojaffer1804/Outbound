"""
outbound/backend/cache/scraper_cache.py

Thread-safe, persistent caching layer for university scraper results.
Uses Python's built-in sqlite3 (zero external dependencies) to store
serialized RawRequirement records per scraper with a configurable TTL
(default: 24 hours).

Key behaviours:
- Cache hit (record is < TTL old): Returns instantly from SQLite (~2ms).
- Cache miss or expired: Invokes scraper_cls().run(), persists result,
  and returns the fresh data.
- Network failure on refresh: If stale cached data exists, returns the
  stale snapshot with a logged warning (stale-while-revalidate pattern)
  rather than crashing the user's request.
- Thread safety: Uses a threading lock around all DB writes since
  sqlite3 in Python's default mode is not fully thread-safe for
  concurrent writers.

Usage from api/main.py:
    from cache.scraper_cache import scraper_cache
    reqs = scraper_cache.get_cached_or_fetch(TUMInformaticsScraper)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Type

# ── Path setup ──────────────────────────────────────────────────────────────
# Import from sibling package using the same sys.path approach the rest of
# the backend uses (running from the backend/ directory).
import sys
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from ingestion.base_scraper import BaseUniversityScraper, RawRequirement

logger = logging.getLogger("outbound.cache")

# ── Constants ───────────────────────────────────────────────────────────────
DEFAULT_TTL_SECONDS = 86_400  # 24 hours
DB_PATH = _BACKEND_DIR / "data" / "cache.db"

# ── SQL ─────────────────────────────────────────────────────────────────────
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS scraper_cache (
    scraper_id   TEXT PRIMARY KEY,
    university   TEXT NOT NULL,
    program      TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    records_json TEXT NOT NULL
);
"""


class ScraperCache:
    """Persistent, thread-safe scraper result cache backed by SQLite."""

    def __init__(self, db_path: Path = DB_PATH, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        # Ensure the data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Internal DB helpers ─────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new connection (one per call, safe for multi-thread)."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(_CREATE_TABLE)
                conn.commit()
            finally:
                conn.close()

    # ── Scraper identity key ────────────────────────────────────────────────

    @staticmethod
    def _scraper_id(scraper_cls: Type[BaseUniversityScraper]) -> str:
        """Stable cache key: 'University::Program' (unique per scraper class)."""
        return f"{scraper_cls.university}::{scraper_cls.program}"

    # ── Serialisation helpers ───────────────────────────────────────────────

    @staticmethod
    def _serialize_requirements(reqs: list[RawRequirement]) -> str:
        """Convert list of RawRequirement dataclass instances to JSON string."""
        return json.dumps([asdict(r) for r in reqs], ensure_ascii=False)

    @staticmethod
    def _deserialize_requirements(json_str: str) -> list[RawRequirement]:
        """Reconstruct RawRequirement objects from JSON string."""
        records = json.loads(json_str)
        result = []
        for rec in records:
            result.append(RawRequirement(
                requirement_type=rec["requirement_type"],
                value=rec["value"],
                source_tier=rec["source_tier"],
                country=rec["country"],
                university=rec["university"],
                program=rec["program"],
                source_url=rec["source_url"],
                retrieved_date=rec["retrieved_date"],
                grading_system=rec.get("grading_system"),
                academic_year=rec.get("academic_year", "unknown_year"),
                notes=rec.get("notes"),
                extraction_method=rec.get("extraction_method", "live_parsed"),
            ))
        return result

    # ── Core public API ─────────────────────────────────────────────────────

    def get_cached_or_fetch(
        self,
        scraper_cls: Type[BaseUniversityScraper],
        force_refresh: bool = False,
    ) -> list[RawRequirement]:
        """
        Return cached requirements if fresh (< TTL), otherwise fetch live,
        persist, and return. On network failure, falls back to stale cache
        if available.
        """
        sid = self._scraper_id(scraper_cls)

        # ── 1. Check cache (unless forced refresh) ──────────────────────────
        if not force_refresh:
            cached = self._read_cache(sid)
            if cached is not None:
                fetched_at_str, records_json = cached
                fetched_at = datetime.fromisoformat(fetched_at_str)
                age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
                if age_seconds < self.ttl_seconds:
                    logger.info(
                        "Cache HIT for %s (age: %.0fs / TTL: %ds)",
                        sid, age_seconds, self.ttl_seconds,
                    )
                    return self._deserialize_requirements(records_json)
                else:
                    logger.info(
                        "Cache EXPIRED for %s (age: %.0fs > TTL: %ds). Refreshing...",
                        sid, age_seconds, self.ttl_seconds,
                    )

        # ── 2. Live fetch ───────────────────────────────────────────────────
        try:
            reqs = scraper_cls().run()
            self._write_cache(sid, scraper_cls, reqs)
            logger.info("Cache REFRESHED for %s (%d records)", sid, len(reqs))
            return reqs

        except Exception as exc:
            logger.warning(
                "Live fetch FAILED for %s: %s. Attempting stale fallback...",
                sid, exc,
            )
            # ── 3. Stale fallback ───────────────────────────────────────────
            stale = self._read_cache(sid)
            if stale is not None:
                _, records_json = stale
                logger.warning(
                    "Returning STALE cache for %s (live fetch failed).", sid,
                )
                return self._deserialize_requirements(records_json)

            # No cache at all — propagate the original error
            logger.error("No cache available for %s and live fetch failed.", sid)
            raise

    # ── Cache read / write ──────────────────────────────────────────────────

    def _read_cache(self, scraper_id: str) -> Optional[tuple[str, str]]:
        """Returns (fetched_at, records_json) or None."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT fetched_at, records_json FROM scraper_cache WHERE scraper_id = ?",
                (scraper_id,),
            ).fetchone()
            if row:
                return (row["fetched_at"], row["records_json"])
            return None
        finally:
            conn.close()

    def _write_cache(
        self,
        scraper_id: str,
        scraper_cls: Type[BaseUniversityScraper],
        reqs: list[RawRequirement],
    ):
        now = datetime.now(timezone.utc).isoformat()
        records_json = self._serialize_requirements(reqs)
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT INTO scraper_cache (scraper_id, university, program, fetched_at, records_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(scraper_id) DO UPDATE SET
                        fetched_at   = excluded.fetched_at,
                        records_json = excluded.records_json
                    """,
                    (scraper_id, scraper_cls.university, scraper_cls.program, now, records_json),
                )
                conn.commit()
            finally:
                conn.close()

    # ── Admin helpers ───────────────────────────────────────────────────────

    def clear_cache(self, scraper_id: Optional[str] = None):
        """Clear a specific scraper's cache or the entire cache."""
        with self._lock:
            conn = self._get_conn()
            try:
                if scraper_id:
                    conn.execute("DELETE FROM scraper_cache WHERE scraper_id = ?", (scraper_id,))
                else:
                    conn.execute("DELETE FROM scraper_cache")
                conn.commit()
            finally:
                conn.close()
        logger.info("Cache cleared: %s", scraper_id or "ALL")

    def get_cache_stats(self) -> list[dict]:
        """Return metadata about every cached entry for the /cache/status endpoint."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT scraper_id, university, program, fetched_at, records_json FROM scraper_cache"
            ).fetchall()
            now = datetime.now(timezone.utc)
            stats = []
            for row in rows:
                fetched_at = datetime.fromisoformat(row["fetched_at"])
                age = (now - fetched_at).total_seconds()
                record_count = len(json.loads(row["records_json"]))
                stats.append({
                    "scraper_id": row["scraper_id"],
                    "university": row["university"],
                    "program": row["program"],
                    "fetched_at": row["fetched_at"],
                    "age_seconds": round(age),
                    "ttl_seconds": self.ttl_seconds,
                    "ttl_remaining_seconds": max(0, round(self.ttl_seconds - age)),
                    "is_fresh": age < self.ttl_seconds,
                    "record_count": record_count,
                })
            return stats
        finally:
            conn.close()

    def warm_up(self, scraper_classes: list[Type[BaseUniversityScraper]]):
        """Pre-populate cache for all scrapers (call on startup)."""
        logger.info("Cache warm-up: populating %d scrapers...", len(scraper_classes))
        for cls in scraper_classes:
            sid = self._scraper_id(cls)
            try:
                self.get_cached_or_fetch(cls)
            except Exception as exc:
                logger.warning("Warm-up failed for %s: %s (will retry on first request)", sid, exc)
        logger.info("Cache warm-up complete.")


# ── Module-level singleton ──────────────────────────────────────────────────
# Import this from anywhere: `from cache.scraper_cache import scraper_cache`
scraper_cache = ScraperCache()
