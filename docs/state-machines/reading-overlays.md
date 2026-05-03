---
name: state-machines/reading-overlays
description: State machines for Zen mode, digest overlay, and base overlay gesture primitives.
last_updated: 2026-05-03 15:10, bb6b54a
---
# State Machines: Reading Overlays

[→ Client: Reading Overlays](../client/reading-overlays.md)

### 11. Zen Mode Overlay

| | |
|---|---|
| **Pattern** | Thin wrapper around `BaseOverlay` |
| **File** | `components/ZenModeOverlay.jsx` |
| **Scope** | Per-article, rendered only when `summary.expanded && summary.html` |

#### Architecture

ZenModeOverlay is now a minimal component that composes `BaseOverlay`, providing only:
- `headerContent`: Domain favicon + displayDomain + truncated articleMeta, wrapped in a link to the original URL
- `children`: Prose-styled HTML via `overlayProseClassName`
- `overlayMenu`: menu surface contract built from `useOverlayContextMenu` plus Zen's action list (single `Elaborate` action whose handler is `runElaboration` from the shared `useElaboration` hook)

It passes `overlayLayers={<ElaborationPreview … />}` into `BaseOverlay`, keeping the preview in the same Floating UI tree as the reader and menu. All gesture handling, scroll progress, body scroll lock, reader-level Escape handling, and menu surface rendering are delegated to `BaseOverlay`. All elaboration state, abort lifecycle, and `/api/elaborate` POST live in `useElaboration`.

#### Close Triggers

| Trigger | Handler | Effect |
|---|---|---|
| ChevronDown button | `onClose()` → `summary.collapse()` | Release lock, mark read |
| Escape key | `onClose()` → `summary.collapse()` | Release lock, mark read (suppressed if context menu or elaboration preview is open) |
| Pull-to-close threshold (80px) | `onClose()` → `summary.collapse()` | Release lock, mark read |
| Check button | `onMarkRemoved()` | `summary.collapse(false)` + `markAsRemoved()` |
| Overscroll-up threshold (30px) | `onMarkRemoved()` | `summary.collapse(false)` + `markAsRemoved()` |

#### Context Menu

ZenModeOverlay wires `useOverlayContextMenu(true)`, defines a single `Elaborate` action against `runElaboration` from `useElaboration({ sourceMarkdown: summaryMarkdown, articleUrls: [url] })`, and passes the resulting `overlayMenu` contract to `BaseOverlay`. `BaseOverlay` renders `<OverlayContextMenu>` when that contract is present. The action invokes the shared elaboration request hook and Zen renders `ElaborationPreview` against the hook's state. The exact same wiring lives in `DigestOverlay` (see §12 and §19).

---

### 12. Digest Overlay

| | |
|---|---|
| **Pattern** | Thin wrapper around `BaseOverlay` |
| **File** | `components/DigestOverlay.jsx` |
| **Scope** | Singleton, rendered when `digest.expanded` |

#### Architecture

DigestOverlay composes `BaseOverlay`, providing:
- `headerContent`: BookOpen icon + article count label
- `children`: Prose-styled HTML (or error message if `errorMessage && !html`)
- `overlayMenu`: menu surface contract built from `useOverlayContextMenu` plus a single `Elaborate` action whose handler is `runElaboration` from the shared `useElaboration` hook

It passes `overlayLayers={<ElaborationPreview … />}` into `BaseOverlay`, keeping the preview in the same Floating UI tree as the reader and menu. All gesture handling, scroll progress, body scroll lock, and reader-level Escape handling are delegated to `BaseOverlay`. All elaboration state and `/api/elaborate` POST live in `useElaboration`.
`App.jsx` mounts `DigestOverlay` only while `digest.expanded` is true, matching the conditional mount lifecycle of `ZenModeOverlay`.

#### Differences from Zen Mode

| Aspect | Zen Mode | Digest Overlay |
|---|---|---|
| Content source | Single `article.summary.markdown` | `payload.digest.markdown` (multi-article) |
| `useElaboration` `articleUrls` | `[url]` (one element) | `data.articleUrls` (N elements) |
| Zen lock owner | `article.url` | `'digest'` |
| Header info | Domain + favicon | Article count |
| Mark removed | Single article | All articles in digest |
| Close → mark read | `summary.collapse()` → single article | `digest.collapse(false)` → all articles |
| Check → mark removed | `summary.collapse(false)` + `markAsRemoved()` | `digest.collapse(true)` → all articles |
| Context menu | wired (single `Elaborate` action) | wired (same `Elaborate` action, undifferentiated) |

#### Context Menu

DigestOverlay wires `useOverlayContextMenu(true)`, instantiates `useElaboration({ sourceMarkdown: markdown, articleUrls })`, defines an `Elaborate` action with the same key/label/icon/trampoline as Zen's, and passes the resulting `overlayMenu` contract to `BaseOverlay`. The duplication of the action definition is deliberate (two callers don't earn an `actionFactory` abstraction yet). See §19.

---

### 16. BaseOverlay (Shared Foundation)

| | |
|---|---|
| **Pattern** | Portal + composed gesture hooks + body scroll lock |
| **File** | `components/BaseOverlay.jsx` |
| **Scope** | Shared foundation for ZenModeOverlay and DigestOverlay |

#### Architecture

BaseOverlay is the shared foundation that eliminates duplication between ZenModeOverlay and DigestOverlay. If it is mounted, the overlay is open; callers control visibility by mounting/unmounting it. It registers as a `FloatingNode`, so Floating UI treats it as the reader layer underneath the context menu and elaboration preview. It handles all common overlay behavior:

- **Body scroll lock**: `document.body.style.overflow = 'hidden'` while mounted
- **Escape key**: `useDismiss({ escapeKey: true, outsidePress: false })` closes the reader only when no child floating layer is open (§19)
- **Scroll progress**: Renders progress bar via `useScrollProgress`
- **Pull-to-close**: Handles pull-down gesture via `usePullToClose` (currently passed `enabled: false` — see `usePullToClose` inline comment and GOTCHAS: the non-passive `touchmove` listener hijacks mobile long-press-to-select)
- **Overscroll-up**: Handles pull-up-at-bottom gesture via `useOverscrollUp`
- **Header**: Renders ChevronDown (close), `headerContent` slot, Check (mark removed) buttons
- **Progress bar**: 2px bar at header bottom, scaled by scroll progress
- **Overscroll zone**: CheckCircle icon that animates as overscroll progresses
- **Context-menu surface**: When `overlayMenu` is present, the scroll surface is tagged `data-overlay-content`, receives `overlayMenu.handleContextMenu`, and `BaseOverlay` renders `OverlayContextMenu` with the provided state/actions. Without `overlayMenu`, the shell has no context-menu participation.
- **Nested overlay layers**: Renders `overlayLayers` (currently `ElaborationPreview`) inside the same Floating UI subtree so the preview sits above the reader without custom Escape arbitration.

#### Props

| Prop | Type | Description |
|---|---|---|
| `headerContent` | ReactNode | Slot for header middle content (domain info or article count) |
| `onClose` | () => void | Called on ChevronDown, Escape, or pull-to-close threshold |
| `onMarkRemoved` | () => void | Called on Check button or overscroll-up threshold |
| `overlayMenu` | object \| undefined | Optional menu surface contract: menu state, `handleContextMenu`, `onOpenChange`, and wrapper-owned actions |
| `overlayLayers` | ReactNode | Additional floating layers rendered in the same Floating UI subtree (currently `ElaborationPreview`) |
| `children` | ReactNode | Content to render in scrollable area |

#### Exports

- `default`: BaseOverlay component
- `overlayProseClassName`: Tailwind prose classes for consistent overlay content styling

#### Composed Hooks

| Hook | Configuration |
|---|---|
| `useScrollProgress` | `(scrollRef)` |
| `usePullToClose` | `({ containerRef, scrollRef, onClose, enabled: false })` — currently hard-disabled for native text selection |
| `useOverscrollUp` | `({ scrollRef, onComplete: onMarkRemoved, threshold: 60 })` |

The `useOverlayContextMenu` hook is **not** composed by `BaseOverlay` itself. Wrappers instantiate it and pass an `overlayMenu` contract when they want menu behavior. `BaseOverlay` owns the opted-in DOM surface, the `OverlayContextMenu` render site, the `overlayLayers` render site, and the reader-level `FloatingNode`.

---

### 13. Scroll Progress

| | |
|---|---|
| **Pattern** | `useState` × 2 + passive scroll listener |
| **File** | `hooks/useScrollProgress.js` |
| **Scope** | Per-overlay instance (used internally by `BaseOverlay`) |

#### State

| Value | Type | Derivation |
|---|---|---|
| `progress` | float ∈ [0, 1] | `scrollTop / (scrollHeight - clientHeight)` |
| `hasScrolled` | boolean | `scrollTop > 10` |

#### API

```js
useScrollProgress(scrollRef, enabled = true) → { progress, hasScrolled }
```

When `enabled` is false, both states reset to `0` and `false` respectively.

#### Consumers

`BaseOverlay` consumes both:
- `progress` → 2px progress bar at header bottom, scaled via `transform: scaleX(progress)`
- `hasScrolled` → header backdrop blur transition (solid → blurred)

#### Performance

`{ passive: true }` listener. No throttle needed — browser coalesces scroll events; React 19 batches state updates; the progress bar uses GPU-accelerated CSS transform.

---

### 14. Pull to Close

| | |
|---|---|
| **Pattern** | `useTrackedState` + touch event handlers on container ref |
| **File** | `hooks/usePullToClose.js` |
| **Scope** | Per-overlay instance (used internally by `BaseOverlay`) |

#### State

`pullOffset: number` — how many pixels the overlay has been pulled down (with 0.5× damping). Tracked via `useTrackedState` so the ref stays in sync with state for use in `handleTouchEnd`.

#### API

```js
usePullToClose({ containerRef, scrollRef, onClose, threshold = 80, enabled = true }) → { pullOffset }
```

When `enabled` is false, `pullOffset` resets to `0` and gesture detection is disabled.

#### Detection

- **Activates** when touch starts outside scroll area OR when `scrollTop === 0`.
- **Pull down** (`diff > 0`): `e.preventDefault()`, set `pullOffset = diff * 0.5`.
- **Pull up** (`diff < -10`): Cancel gesture.
- **Release**: If `pullOffset > 80` (threshold) → `onClose()`. Always reset to 0.

#### Visual

Entire overlay `translateY(pullOffset)`. During pull: no CSS transition (instant tracking). On release: `transition: transform 0.3s ease-out` (spring-back).

#### Boundary Guard

Works in tandem with `useOverscrollUp`. Pull-to-close operates at the **top** boundary; overscroll-up operates at the **bottom** boundary. They never conflict because each checks scroll position before activating.

---

### 15. Overscroll Up

| | |
|---|---|
| **Pattern** | `useTrackedState` + touch event handlers on scroll ref |
| **File** | `hooks/useOverscrollUp.js` |
| **Scope** | Per-overlay instance (used internally by `BaseOverlay`) |

#### State

| Value | Type | Derivation |
|---|---|---|
| `overscrollOffset` | number | `min(deltaY * 0.5, threshold * 1.5)` |
| `isOverscrolling` | boolean | `overscrollOffset > 0` |
| `progress` | float 0→1 | `overscrollOffset / (threshold * 0.5)` |
| `isComplete` | boolean | `progress >= 1` |

`overscrollOffset` is tracked via `useTrackedState` so the ref stays in sync with state for use in `handleTouchEnd`.

#### API

```js
useOverscrollUp({ scrollRef, onComplete, threshold = 60, enabled = true }) → { overscrollOffset, isOverscrolling, progress, isComplete }
```

When `enabled` is false, `overscrollOffset` resets to `0` and gesture detection is disabled.

#### Detection

- **Activates** only when `isAtBottom()` (`scrollHeight - scrollTop - clientHeight < 1`).
- **Pull up** (`deltaY > 0` at bottom): Track offset with 0.5× damping, max `threshold * 1.5`.
- **Release**: If `offset >= threshold * 0.5` (i.e., 30px with default threshold 60) → `onComplete()`. Always reset to 0.

#### Visual Feedback Progression

| Progress | Icon opacity | Icon scale | Background |
|---|---|---|---|
| 0% | 0.3 | 0.8× | `bg-slate-100` |
| 50% | 0.65 | 0.9× | `bg-slate-100` |
| 100% | 1.0 | 1.0× + container 1.1× | `bg-green-500 text-white` |

Content slides up at 0.4× the offset rate during the gesture.

---
