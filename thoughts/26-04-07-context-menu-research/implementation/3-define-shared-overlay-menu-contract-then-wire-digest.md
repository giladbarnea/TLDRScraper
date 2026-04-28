---
name: Abstract: Hoist Overlay Menu Surface Contract Into BaseOverlay
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Hoist Overlay Menu Surface Contract Into BaseOverlay

## Key Changes
- `BaseOverlay` now conditionally mounted (only while open); `expanded` prop deleted.
- `DigestOverlay` now conditionally mounted (only while open).
- `BaseOverlay` accepts an `overlayMenu` contract object.
- Contract includes: `isOpen`, `selectedText`, `menuRef`, `handleContextMenu`, `closeMenu`, `actions`.
- `BaseOverlay` is now the `OverlayContextMenu` render site.
