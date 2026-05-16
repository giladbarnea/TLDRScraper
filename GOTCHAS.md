---
last_updated: 2026-05-16 12:12
what_is_a_gotcha: Rather confidently signing off on something that later on proved to be at least partially wrong due to wrong assumptions; Figuratively, going thourhg "[allegedly] fixed" -> "oh actually it's not fixed" -> "ahh right... fixed now".
---
# Gotchas

This document catalogs recurring pitfalls in various topics, including managing client-side state persistence and reactivity, surprising design decisions, and so on.

---

#### 2026-05-15: Forcing `WEBGL_lose_context` in React effect cleanup breaks dev remounts

**Desired behavior that didn't work**: A WebGL-backed touch glow (`LiquidGlassTouchLight`) inside the toast should initialize reliably and react to `pointerdown` on mobile.

**What actually happened and falsified original thesis**: The canvas reported `webgl` context support, but one toast instance logged `TypeError: Argument 1 ('shader') to WebGLRenderingContext.shaderSource must be an instance of WebGLShader`, and later `createShader failed for type 35633`. We initially investigated the shader code and pointer event wiring. That was the wrong level.

**Cause & Fix**: In React dev/StrictMode, effects mount, clean up, and mount again. The first mount compiled successfully. Cleanup then called `gl.getExtension('WEBGL_lose_context')?.loseContext()`, which intentionally poisoned the context/canvas. On the second mount, `getContext('webgl')` still returned an object, but `createShader()` returned `null`, so shader setup aborted before the `pointerdown` listener path became usable. Removing the forced context-loss call from cleanup fixed the remount and restored the effect.

**Generalized principle**: in React effect cleanup, do not force-destroy scarce browser resources unless the runtime actually requires it. Dev remount semantics are part of the execution model; cleanup must leave the next mount able to reinitialize normally. A context object existing does not imply it is healthy.

---

#### 2026-05-05: Derived multi-article UI can still go stale after a "store-backed" fix if the subscription shape is wrong

**Desired behavior that didn't work**: After fixing the newsletter/day `n/m` badge to read completion from `articleStore`, removing or reading an article should immediately update the badge and any all-removed visuals (newsletter/section dimming + auto-fold).

**What actually happened and falsified original thesis**: We initially signed off on the badge fix because the implementation had been moved off structural props and onto store state. That confidence was premature. In a real repro (`HN Show` going from `1/2` to all removed), the last article dimmed, the newsletter collapsed, but the badge stayed at `1/2`. We had wrongly assumed that "subscribing to the relevant article keys" was automatically enough to make a multi-article derived UI reliable.

**Cause & Fix**: The first fix subscribed the badge through a render-time-derived set of per-article listeners. That subscription shape was brittle for `useSyncExternalStore`: it depended on a recreated key collection/subscribe closure rather than a stable lifecycle signal. At the same time, newsletter and section `allRemoved` logic was still reading structural `articles.every(a => a.removed)` props instead of live lifecycle state. The durable fix was to add a day-level lifecycle notification path in `articleStore`, then expose selectors that derive grouped state from live slices for a given `(date, urls)` set: `useCompletedArticlesCount(date, urls)` and `useAllArticlesRemoved(date, urls)`. The badge, newsletter containers, and section containers now all use those selectors.

**Generalized principle**: in external-store React code, "derived from the store" is not enough. The subscription boundary itself must match the semantic domain of the UI you are deriving. For grouped UI (badge counts, all-removed container state), prefer a stable grouped lifecycle selector over ad-hoc render-time fan-out subscriptions or structural prop scans.

---

#### 2026-04-28: `visibility: hidden` on a portal lets the iOS native callout render alongside it

**Cause & Fix**: Floating UI's `isPositioned` guard (`visibility: hidden` until coordinates settle) was used to prevent a (0,0) flash. On iOS/Chromium, handling `contextmenu` but presenting no *visible* element lets the OS callout commit before the menu becomes visible — both then stay on screen. Removing the guard keeps the menu visible from first paint, suppressing the callout. The (0,0) flash is a non-issue: Floating UI settles position in a layout effect before the browser paints.

**Generalized principle**: on iOS (including Chromium-based browsers), suppressing the native callout requires a visible DOM element at event time. Mounted-but-invisible (`visibility: hidden`, `opacity: 0`) does not count.

---

#### 2026-04-20: Portal clicks bubble through React tree and ghost-click underlying components

**Desired behavior that didn't work**: Tapping "Elaborate" in the context menu should start the elaboration fetch and keep the ZenModeOverlay open.

**What actually happened**: The overlay closed immediately after the fetch started. Logs showed `[summary-view] expanded → collapsed` 9ms after the action click, aborting the in-flight fetch.

**Cause & Fix**: React portals render into a different DOM node but events still bubble through the **React component tree**. `OverlayContextMenu` is a portal but is a React child of `ZenModeOverlay` → `ArticleCard`. The click on the menu button bubbled up to `ArticleCard`'s `onClick={handleCardClick}`. By then, `removeAllRanges()` had already cleared the selection, so the `if (selection.toString().length > 0) return` guard didn't fire, and `summary.toggle()` → `collapse()` closed the overlay. `BaseOverlay` already had `onClick={(e) => e.stopPropagation()}` for this reason. Adding the same to `OverlayContextMenu` and `ElaborationPreview` fixed it.

**The generalized principle**: every portal that is a React descendant of a click-handling ancestor needs `onClick={e => e.stopPropagation()}` on its root, or clicks will silently reach ancestors via React's synthetic event bubbling regardless of DOM structure.

---

#### 2026-02-15: Article clicks silently fail after background merge

**Desired behavior that didn't work**: Clicking any article after the background rescrape merge should trigger a summarize request, same as before the merge.

**What actually happened and falsified original thesis**: After the Phase 2 merge completed and new articles appeared, clicking newly merged articles did nothing—no network request, no error. Old cached articles in days/categories that received new articles also stopped responding. Articles in untouched days still worked. Opening and closing the zen overlay (from a working article) unstuck the broken ones. We initially investigated the merge algorithm itself and various state management fixes, but these didn't resolve it.

**Cause & Fix**: `ArticleCard` passes `article.issueDate` to `useArticleState(date, url)`, which derives the storage key via `getNewsletterScrapeKey(date)`. The article is then looked up by URL in that day's payload. If `issueDate` doesn't match the CalendarDay's actual date (the key under which the article is stored), the lookup hits a different/empty storage key, `article` resolves to `null`, and `fetchSummary` silently returns (`if (!article) return`). After the background merge, `issueDate` could diverge from the CalendarDay's date because `SERVER_ORIGIN_FIELDS` carried whatever `issueDate` the fresh scrape returned—and some adapters set `date` from the article's publication date rather than the target scrape date. The fix was to make CalendarDay stamp `issueDate: date` on every article at render time (the authoritative source of truth for which day an article belongs to), and to force `issueDate: freshPayload.date` in `mergePreservingLocalState`.

**The generalized principle**: when a component derives a storage/lookup key from a data field, that field must be set by the authority that owns the key—not carried blindly from upstream data. CalendarDay owns the storage key, so it must stamp the corresponding `issueDate`.

---

#### 2026-01-10: Optimistic update only affected calling hook instance, not other subscribers

**Desired behavior that didn't work**: Swipe-to-remove gesture should update UI immediately without waiting for server response.

**What actually happened and falsified original thesis**: Changing `useSupabaseStorage.setValueAsync` to call `setValue(resolved)` before `await writeValue()` had no visible effect—the UI still waited ~1 second for the server. We wrongly assumed updating the local React state in the calling hook would propagate to all components.

**Cause & Fix**: Multiple components use `useSupabaseStorage` with the same key (e.g., `ArticleCard` and `CalendarDay`). Each creates its own hook instance with independent local state. Calling `setValue()` only updates that one instance. Other subscribers only update when `emitChange(key)` fires, which happened inside `writeValue()` after the server responded. The fix was to also update the shared `readCache` and call `emitChange(key)` immediately—before the server request—so all subscribers re-render optimistically. On error, revert cache and emit again.

**The generalized principle is to always investigate the broader dependency tree**—upstream and downstream—of the scope you intend to affect before implementing changes. Logic is usually part of a larger system, and you need to understand that system for the change to work as intended.

---

#### 2025-11-27 `7f72ea8`: Base layer styles overridden by Typography plugin

**Desired behavior that didn't work**: Add margin-top: 0.8em and margin-bottom: 0.6em to h1 elements via base layer styles.

**What actually happened and falsified original thesis**: No visual change. h1 elements inside prose-wrapped content kept the Typography plugin's default margins. We had wrongly assumed base layer `h1` selectors would override plugin styles.

**Cause & Fix**: The `@tailwindcss/typography` plugin's `.prose :where(h1)` and `.prose-sm :where(h1)` selectors have higher specificity and cascade priority than base layer styles. The fix was to target `.prose h1` and `.prose-sm h1` specifically, placed outside of `@layer` for highest priority.

---


#### 2025-11-17: Child component bypassing state management layer causes infinite API hammering

session-id: 892fa714-0087-4c5a-9930-cffdfc5f5359

**Desired behavior that didn't work**: Just browsing the app should load data once per date, then remain quiet until user interaction.

**What actually happened and falsified original thesis**: Continuous machine-gun API requests to GET /api/storage/daily/{date} for the same dates, hammering the server non-stop. <turned-out-to-be-wrong>We initially assumed it was a React re-render loop from unstable useEffect dependencies (e.g., `defaultValue` object creating new references). Then we thought it was multiple `useSupabaseStorage` hook instances all mounting simultaneously (20+ ArticleCards per date). We added global read deduplication to prevent concurrent requests, which helped but didn't stop the hammering. We had wrongly assumed the hooks were the problem.</turned-out-to-be-wrong>

**Cause & Fix**: `ArticleList.jsx` had a useEffect that directly called `storageApi.getDailyPayload(article.issueDate)` for every article (20+ API calls per date), completely bypassing the `useSupabaseStorage` hook abstraction. This useEffect ran whenever the `articles` prop changed. The parent component recreated the `articles` array on every render (via `.map()`), creating a new reference and triggering the useEffect again. Result: infinite loop of 20+ API calls per render. The entire useEffect was redundant - article states were already being synced via `useSupabaseStorage` in parent components. The fix was to delete the broken useEffect entirely and let ArticleList simply sort the articles it receives from props. **Key lesson**: When you build a proper data management layer (custom hooks), don't bypass it by directly calling storage APIs in child components. Child components should consume data from props, not fetch it themselves. Breaking this rule creates duplicate data fetching, races, and infinite loops.

---

#### 2025-11-15 `750f83e`: Concurrent TLDR updates race to overwrite each other

**Desired behavior that didn't work**: When two articles' TLDR buttons are clicked simultaneously, both TLDRs should be fetched and stored independently.

**What actually happened and falsified original thesis**: One article showed "Available" state but with no content, then clicking "Available" triggered a new TLDR request instead of displaying the cached result. We had wrongly assumed React's state would handle concurrent setValueAsync calls correctly.

**Cause & Fix**: Classic read-modify-write race condition. Both updates captured the same stale `value` from the closure, so the second write overwrote the first, losing one article's TLDR data. The fix was to use a ref (valueRef) to track the latest state, ensuring each concurrent update operates on current data instead of stale closure captures.

---

#### [principle] Shared mutable state behind a custom hook

When shared mutable state lives behind a custom hook, each hook instance must be a pure subscriber to a single external source of truth. Authoritative mutations must go through that shared store; per-hook local copies become stale immediately. The same shape reappears in any new hook that does "useState + some side-effect around shared data."

Current implementation (`useSupabaseStorage`): module-level `readCache` and `changeListenersByKey`, with `emitChange` driving all subscribers. Optimistic writes update both the caller’s state + the shared cache before network.

---

#### [principle] Merge algorithms must be protected from fields they do not own

`mergePreservingLocalState` (feedMerge.js) separates concerns: the daily payload is a narrow source of truth for server-origin fields only (`SERVER_ORIGIN_FIELDS` whitelist); every UI-only field lives in an orthogonal hook (`useArticleState`, `useSummary`) keyed by (date, url) and derived from the shared payload cache. Because those fields never enter the payload, they cannot be lost during a merge.

Goodness: the merge contract stays tiny and static. Local UI state evolves independently under its own storage keys and is reconciled via `useSupabaseStorage` subscriptions rather than merge logic.

---

#### 2026-05-01: Queued article mutations computed from render-time state instead of apply-time state

**Desired behavior that didn't work**: Multiple queued mutations for the same article should resolve in order against the latest queued article state, so non-idempotent transitions like toggles behave correctly.

**What actually happened and falsified original thesis**: After moving article writes to the queued patch path, it looked safe to compute `const optimisticPatch = updater(article)` in `useArticleState` before enqueueing. That assumption was incomplete. If two mutations were queued before re-render, both could derive from the same stale render snapshot. For example, two fast toggles could both compute the same patch from the same initial state, producing the wrong final result.

**Cause & Fix**: The queue serialized persistence, but patch derivation was still happening too early. The fix was to pass the updater function into the queue and evaluate it against the latest article state when the queued task actually begins. Crucially, once that patch is resolved, it must then be frozen and reused across optimistic-concurrency retries. Recomputing on retry would reintroduce the older toggle-intent drift bug.

**Generalized principle**: for queued state mutations, there are two distinct moments that must not be conflated:
1. derive the mutation from the latest local state at apply time, not render time;
2. once derived, preserve that exact mutation intent across retries and conflicts.
