---
status: completed
last_updated: 2026-01-25 15:07, 2a45cc4
---
# Improve Fetch Range Speed

Audited date-range scraping and identified main latency sources: per-date Supabase cache reads, fully sequential per-source scraping, and a fixed 0.2s sleep after network hits. Proposed a three-phase plan: (1) parallelize per-date source scraping with deterministic merges and a feature flag, (2) batch cache reads via `get_daily_payloads_range` with a date-keyed map, and (3) move or gate throttling so only necessary adapters sleep. Phase 1 was implemented with thread-pool workers, deterministic merges, and env toggles; Phase 2/3 remained as planned follow-ups.
