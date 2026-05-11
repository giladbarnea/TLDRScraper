---
last_updated: 2026-05-11 14:32, 556a66e
---

# Overlay Context Menu

Built a shared context menu surface for Zen and Digest overlays, triggered by desktop right-click or mobile text selection inside `[data-overlay-content]`. The menu carries a single `Elaborate` action — POST selected text + source markdown + article URLs to `/api/elaborate` — which scrapes source articles in parallel and opens a modal glass-panel preview (`ElaborationPreview`).

**Architecture evolution (5 steps, see `impl-review/0-g-review-1.md`):**

1. **Split desktop/mobile paths** inside `useOverlayContextMenu` — desktop right-click and mobile selection are now separate internal hooks.
2. **Explicit mobile reducer** (`mobileSelectionMenuReducer`) replacing `touchActive` + `openedBySelectionRef` with a pure state machine.
3. **Shared `overlayMenu` contract on `BaseOverlay`** — `BaseOverlay` owns `data-overlay-content`, surface `onContextMenu`, and the `OverlayContextMenu` render site. `DigestOverlay` mounted only while open (matching Zen's lifecycle). `expanded` prop deleted.
4. **Floating UI positioning** — `@floating-ui/react-dom` replaces hand-rolled `clampMenuPosition`. Point refs for desktop right-click; range refs with copied client rects for mobile selection. `flip()` + `shift()` for viewport collision.
5. **Layer/focus stack via `@floating-ui/react`** — `FloatingTree` at `App` root; `BaseOverlay`, `OverlayContextMenu`, `ElaborationPreview` each register as `FloatingNode` with `useDismiss`. All project-source `document.addEventListener('keydown')` and `stopImmediatePropagation` arbitration deleted. `OverlayContextMenu`: non-modal focus manager that skips auto-focus on coarse pointers (preserves native selection). `ElaborationPreview`: true modal with focus trap + return.

**Backend generalization:** `/api/elaborate` accepts `source_markdown` + `article_urls` (non-empty list). Zen sends `[url]`; Digest sends its source URL list. Backend scrapes all in parallel (`ThreadPoolExecutor(max_workers=5)`), concatenates bodies into `<source-articles>` prompt section. Old field names (`url`, `summary_markdown`) removed end-to-end. `useElaboration` is the sole client-side caller.

**Key design decisions:** `Elaborate` action copy-pasted between Zen and Digest (premature abstraction with only 2 callers); `useElaboration` lives in `client/src/hooks/` (independent of the menu); `ToastContainer` outside `FloatingTree` (not a dismissible layer); pull-to-close remains disabled (item 6, deferred). No BaseUI migration — positioning and interaction primitives from Floating UI are enough.
