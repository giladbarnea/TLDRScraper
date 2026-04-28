---
name: Abstract: Generalize Elaborate Endpoint And Wire Digest
last_updated: 2026-04-28 15:22
---

# Abstract: Generalize Elaborate Endpoint And Wire Digest

Generalizes backend for multiple URLs and brings Digest up to parity.

## Relevant Context
- Both Zen and Digest define an identical `Elaborate` action and render `<ElaborationPreview>`.
- `ElaborationPreview` Escape/backdrop routing applies identically to both instances.
- No changes to `useOverlayContextMenu` or `BaseOverlay` contract.
