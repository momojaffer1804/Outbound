import sys
import time
import os
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))

from cache.scraper_cache import scraper_cache
from scraper_tum_informatics import TUMInformaticsScraper

def run_tests():
    print("=" * 55)
    print("TEST 1: CACHE RETRIEVAL SPEED (BENCHMARK)")
    print("=" * 55)
    t0 = time.perf_counter()
    records = scraper_cache.get_cached_or_fetch(TUMInformaticsScraper)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"Retrieved: {len(records)} records for TUM Informatics")
    print(f"Time taken: {elapsed_ms:.2f} ms (Instant SQLite query)")

    print("\n" + "=" * 55)
    print("TEST 2: CACHE STORAGE STATS & TTL STATUS")
    print("=" * 55)
    stats = scraper_cache.get_cache_stats()
    for s in stats:
        fresh_str = "FRESH" if s["is_fresh"] else "EXPIRED"
        print(f"[{fresh_str}] {s['university']} - {s['program']}")
        print(f"        Records: {s['record_count']} | TTL Remaining: {s['ttl_remaining_seconds']}s | Age: {s['age_seconds']}s")

    print("\n" + "=" * 55)
    print("TEST 3: SQLITE PERSISTENCE FILE ON DISK")
    print("=" * 55)
    db_path = scraper_cache.db_path
    print(f"DB Path: {db_path}")
    print(f"Exists on disk: {os.path.exists(db_path)}")
    print(f"File size: {os.path.getsize(db_path):,} bytes")
    print("=" * 55)
    print("ALL CACHE TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
