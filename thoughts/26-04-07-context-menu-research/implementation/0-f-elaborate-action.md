---
name: Context Menu Elaborate Action
follows: implementation/0-e-initial-implementation.md
done: 2026-04-20, d1c2995
implements: plans/0-d-overlay-context-menu.plan.md
reviewed_by: impl-review/0-g-review-1.md
last_updated: 2026-04-20 13:10
---
# Context Menu Implementation Round 2

## Summary

Replaces the "Close reader" / "Mark done" context menu actions with a single "Elaborate" action. Tapping it sends selected text to `/api/elaborate` and renders the response on a liquid-glass preview board (`ElaborationPreview`).

## Key Changes
- **`ZenModeOverlay`**: Owns elaboration state machine (`idle | loading | available | error`) and fetch lifecycle (`AbortController`). Passes `summaryMarkdown` to the endpoint for context.
- **`ElaborationPreview`**: New portal component. `85vw × 60vh` glass board (`bg-white/80 backdrop-blur-2xl`). Three body states: pulsing Sparkles loader, error chip, scrollable markdown prose. Dismiss via backdrop tap, X button, or Escape. `z-[210]`.
- **`OverlayContextMenu`**: Captures `selectedText` at menu-open time (stored in menu state) and passes it via `onSelect(text)`. Fixes mobile race where `touchstart` collapses the selection before `click` fires.
- **`useOverlayContextMenu`**: Stores `selectedText` in menu state on open. Guards `closeMenu()` in `handleSelectionChange` with `!touchActive` to prevent ghost-clicks.

## Bugs Fixed
1. **Nothing happened on tap**: `handleActionClick` read `window.getSelection()` at click time; on mobile it was already empty. Fixed by capturing text at menu-open time.
2. **Overlay closed immediately**: Portal click events bubble through the React tree (not the DOM tree), reaching `ArticleCard`'s `handleCardClick`. Added `onClick={e => e.stopPropagation()}` to `OverlayContextMenu` and `ElaborationPreview` portals — the same guard `BaseOverlay` already used.
