# Outbound

A source-grounded Masters eligibility engine for Indian students applying abroad.
Checks eligibility across universities, resolves conflicting admission requirements
by source authority, and flags outdated/stale requirement data.

## Structure
- `backend/` — FastAPI backend (ingestion, retrieval, eligibility, conflict detection, ECTS mapping)
- `frontend/` — React frontend
- `eval/` — evaluation harness

## Status
In progress — Phase 1 (data ingestion)