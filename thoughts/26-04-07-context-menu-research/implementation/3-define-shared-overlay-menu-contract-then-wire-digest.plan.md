---
name: Abstract: Hoist Overlay Menu Surface Contract Into BaseOverlay
last_updated: 2026-04-28 15:22
---

# Abstract: Hoist Overlay Menu Surface Contract Into BaseOverlay

Defines the `overlayMenu` contract.

## Relevant Context
- Contract shape includes `isOpen`, `anchorX`/`anchorY`, `selectedText`, `menuRef`, `handleContextMenu`, and `closeMenu`.
- `BaseOverlay` mounts `OverlayContextMenu` when the contract is present.
- `BaseOverlay` Escape logic remains conditionally bypassed by checking `event.defaultPrevented` from capture-phase listeners in child menus/dialogs.
- `DigestOverlay` mounts only while open (`expanded` prop deleted).
