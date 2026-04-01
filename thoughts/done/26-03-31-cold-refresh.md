---
last_updated: 2026-04-01 17:39, 516cd45
---
# Cold Refresh Performance: State 2

Decision: Load cached articles sequentially before triggering background scrape. Concurrent fetching was causing backend thread contention, blocking fast cache reads behind slow scrapes. Sequential fetching reduced time-to-first-article from ~5.8s to ~0.7s.
