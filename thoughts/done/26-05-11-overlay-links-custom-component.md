---
last_updated: 2026-05-11 14:32, 556a66e
---

# Overlay Links as Custom Components

Replaced generated `<a>` links in Zen/Digest readers with `OverlayLink` (a `button` for a11y). Short press → new tab; long press / right-click → custom context menu owned by `BaseOverlay`, reusing `OverlayContextMenu`. `OverlayMarkdown` converts sanitized HTML to React, swapping `<a>` for `OverlayLink`. Extracted shared `createPointPositionReference`. Markdown pipeline, KaTeX, text-selection menu, and `ElaborationPreview` left unchanged.
