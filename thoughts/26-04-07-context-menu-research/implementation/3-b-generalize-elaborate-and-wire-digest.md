---
name: Abstract: Generalize Elaborate Endpoint And Wire Digest
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Generalize Elaborate Endpoint And Wire Digest

## Key Changes
- `DigestOverlay` wired as a second consumer of the `overlayMenu` contract.
- Extracts Zen's inline elaboration logic into a shared `useElaboration` hook in `client/src/hooks/`.
- Both `ZenModeOverlay` and `DigestOverlay` now pass the `overlayMenu` contract and render an `ElaborationPreview`.
