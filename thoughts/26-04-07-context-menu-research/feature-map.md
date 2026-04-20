---
last_updated: 2026-04-20 14:18
---

# Context Menu Feature Map

## Scope

Current feature: a shared overlay context menu in `ZenModeOverlay` that triggers an `Elaborate` action. `DigestOverlay` does not use the menu.

## Client Flow

1. `ArticleCard` opens `ZenModeOverlay` when summary state is expanded.
2. `ZenModeOverlay` composes `useOverlayContextMenu(true)`, `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview`.
3. `BaseOverlay` marks the scroll surface with `data-overlay-content` and threads `onContextMenu` into that surface.
4. `useOverlayContextMenu` opens the menu on:
   - desktop right-click in the overlay content surface
   - mobile text selection settled inside `[data-overlay-content]`
5. The hook stores `selectedText` in menu state at open time.
6. `OverlayContextMenu` uses that captured text, clears the window selection, closes the menu, then calls the action handler.
7. `ZenModeOverlay` runs `/api/elaborate`, owns the fetch `AbortController`, and renders `ElaborationPreview`.

## Verified Coupling Points

- `BaseOverlay` → `useOverlayContextMenu`
  - `data-overlay-content` scopes mobile selection detection.
  - `event.defaultPrevented` in `BaseOverlay` lets the menu claim Escape first.
- `useOverlayContextMenu` → `BaseOverlay`
  - capture-phase Escape handler calls `preventDefault()` + `stopImmediatePropagation()`.
  - menu close path clears selection only when the menu opened from selection.
- `OverlayContextMenu` → `ZenModeOverlay`
  - action click uses captured `selectedText`, not live `window.getSelection()`.
  - portal root stops click propagation so the overlay behind it does not receive the click.
- `ElaborationPreview` → overlay stack
  - portal root also stops click propagation.
  - Escape and backdrop close only the preview.
- `ZenModeOverlay` → backend
  - posts `{ url, selected_text, summary_markdown }` to `/api/elaborate`.
  - handles loading, success, error, and abort locally.

## Not Coupled

- `DigestOverlay` does not compose `useOverlayContextMenu`.
- Feed cards do not use this menu.
- No global `contextmenu` interception exists outside overlay content.

## Backend Path

`POST /api/elaborate` → `tldr_app.elaborate_url()` → `tldr_service.elaborate_url_content()` → `summarizer.elaborate_url()`

The backend fetches the article, combines selected text with summary context, and returns `elaboration_markdown`.
