---
status: implemented
last_updated: 2026-02-20 18:35
---
# Frontend implementation notes

## Group B scope completed

1. Added digest trigger UI in header with `DigestButton`, visible only in select mode.
2. Added `useDigest` hook to manage digest request lifecycle, markdown/html conversion, and shared zen overlay lock integration.
3. Added `DigestOverlay` and extracted shared `ZenOverlayShell` so article summaries and digest overlay share structure.
4. Added pure utility `extractSelectedArticles(selectedIds, payloads)` and API helper `fetchDigest`.
5. Wired `App.jsx` to build selected article descriptors, call digest generation, clear selection on success, and keep selection on failure.
