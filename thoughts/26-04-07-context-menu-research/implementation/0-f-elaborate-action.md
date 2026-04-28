---
name: Abstract: Context Menu Elaborate Action
last_updated: 2026-04-28 15:23, 7bf2b9f
---

# Abstract: Context Menu Elaborate Action

Replaces quick actions with a single "Elaborate" action.

## Key Changes
- **`ZenModeOverlay`**: Owns elaboration state machine and fetch lifecycle.
- **`ElaborationPreview`**: New portal component. Dismisses via backdrop tap, X button, or Escape (also using capture-phase `keydown`).
- **`OverlayContextMenu`**: Captures `selectedText` at menu-open time. Portal click events guarded with `onClick={e => e.stopPropagation()}` so they don't bubble to `ArticleCard`.
