---
last_updated: 2026-01-25 15:05, 712f4ca
---
# Speed Up App Refresh

Decision: keep `useSupabaseStorage` in the feed but seed its cache with the `/api/scrape` payload. This removes redundant per-day `/api/storage/daily/<date>` fetches and the "Syncing..." flash while preserving pub/sub reactivity and storage persistence for read/removed/TLDR state. Implemented in `client/src/hooks/useSupabaseStorage.js`.
