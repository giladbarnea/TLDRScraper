---
name: Context Menu Feature Map
originates_from: research/0-a-description.md
last_updated: 2026-04-27 21:21, b387f55
---

# Context Menu Feature Map

## Scope

Current feature: a shared overlay context menu surface contract owned by `BaseOverlay`, consumed by **both** `ZenModeOverlay` and `DigestOverlay`, with one `Elaborate` action wired identically in each. The shared `useElaboration` hook owns the per-action lifecycle; the backend `/api/elaborate` accepts a list of source-article URLs so Digest sends N URLs while Zen sends one.

## Client Flow

1. `ArticleCard` opens `ZenModeOverlay` when summary state is expanded; `App.jsx` mounts `DigestOverlay` while `digest.expanded` is true.
2. Each overlay wrapper composes `useOverlayContextMenu(true)`, instantiates `useElaboration({ sourceMarkdown, articleUrls })`, defines the `Elaborate` action against `runElaboration`, and passes an `overlayMenu` contract into `BaseOverlay`.
3. `BaseOverlay` renders `OverlayContextMenu` and opts its scroll surface into the menu contract by adding `data-overlay-content` plus the `onContextMenu` handler when `overlayMenu` is present.
4. `useOverlayContextMenu` opens the menu on:
   - desktop right-click in the overlay content surface
   - mobile text selection settled inside `[data-overlay-content]`
5. The hook stores `selectedText` in menu state at open time.
6. `OverlayContextMenu` uses that captured text, clears the window selection, closes the menu, then calls the action handler.
7. `useElaboration` runs `/api/elaborate`, owns the fetch `AbortController` and the `idle | loading | available | error` state, and is consumed by both wrappers; each wrapper renders `ElaborationPreview` against the hook's state.

## Verified Coupling Points

- `BaseOverlay` → `useOverlayContextMenu`
  - `overlayMenu` is the explicit opt-in contract for menu surface wiring.
  - `data-overlay-content` scopes mobile selection detection only when the contract is present.
  - `event.defaultPrevented` in `BaseOverlay` lets the menu claim Escape first.
- `useOverlayContextMenu` → `BaseOverlay`
  - capture-phase Escape handler calls `preventDefault()` + `stopImmediatePropagation()`.
  - menu close path clears selection only when the menu opened from selection.
- `OverlayContextMenu` → wrapper actions
  - action click uses captured `selectedText`, not live `window.getSelection()`.
  - portal root stops click propagation so the overlay behind it does not receive the click.
- `ElaborationPreview` → overlay stack
  - portal root also stops click propagation.
  - Escape and backdrop close only the preview.
- `useElaboration` → backend
  - posts `{ selected_text, source_markdown, article_urls }` to `/api/elaborate`. `article_urls` is a non-empty list — Zen sends `[url]`, Digest sends `data.articleUrls`.
  - aborts in-flight fetch on consumer unmount.

## Not Coupled

- Feed cards do not use this menu.
- No global `contextmenu` interception exists outside overlay content.
- `BaseOverlay` does not own elaboration state. Elaboration is wrapper-side (via the shared hook), not a shell concern.

## Backend Path

`POST /api/elaborate` → `tldr_app.elaborate()` → `tldr_service.elaborate_content()` → parallel `_fetch_article_markdowns_parallel()` (max 5 workers, fail-loud on any miss) → `summarizer.elaborate()` → `_build_elaborate_prompt()`.

The backend canonicalizes each URL, scrapes all of them in parallel, concatenates the bodies into the `<source-articles>` prompt section (per-article `<article index="N">...</article>` delimiters when the list has more than one entry), and returns `{ elaboration_markdown, canonical_urls }`.
