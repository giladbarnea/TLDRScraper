---
name: Hoist Overlay Menu Surface Contract Into BaseOverlay
implements: plans/3-define-shared-overlay-menu-contract-then-wire-digest.plan.md
last_updated: 2026-04-25 20:50
---

# Hoist Overlay Menu Surface Contract Into BaseOverlay

## Summary

Implemented the shared overlay-menu surface contract without wiring Digest as a menu consumer.

## Key changes

- `App.jsx` now mounts `DigestOverlay` only while `digest.expanded` is true, matching Zen's conditional overlay lifecycle.
- `DigestOverlay` no longer accepts or forwards an `expanded` prop.
- `BaseOverlay` no longer accepts `expanded` or `onContentContextMenu`; mounted means open.
- `BaseOverlay` now accepts an optional `overlayMenu` contract and, when present, owns:
  - `data-overlay-content` on the scroll surface
  - the scroll-surface `onContextMenu` handler
  - the `OverlayContextMenu` render site
- `ZenModeOverlay` still owns `useOverlayContextMenu`, its `Elaborate` action, elaboration fetch state, and `ElaborationPreview`, but now passes those menu pieces to `BaseOverlay` through `overlayMenu`.

## Deliberate deferrals

- `DigestOverlay` still does not pass `overlayMenu`.
- `/api/elaborate` is still summary-specific and remains the blocker for giving Digest the same `Elaborate` action.
- Escape arbitration remains the current `defaultPrevented` contract; no focus-stack/BaseUI work landed here.
- Pull-to-close remains disabled for native text selection.

## Verification

- `npm run build` passed.
- `CI=true npm run lint` exited successfully with the existing warning set. Note: this repo's lint script treats `CI=true` as check mode; `CI=1` runs fix mode.
- Search checks confirmed:
  - `ZenModeOverlay.jsx` remains the only `useOverlayContextMenu` consumer.
  - `BaseOverlay.jsx` is now the `OverlayContextMenu` render site.
  - `onContentContextMenu` is removed from client source.
  - `expanded` is removed from `BaseOverlay.jsx` and `DigestOverlay.jsx`.
