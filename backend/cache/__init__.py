"""
outbound/backend/cache/

Scraper caching layer. Persists scraped RawRequirement records locally in
SQLite so that only one live HTTP fetch per university is needed per 24-hour
window -- every subsequent request in that window returns instantly from
the local cache.
"""
