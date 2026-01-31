---
last_updated: 2026-01-10 14:34, 1be13c0
---
# Gotchas

This document catalogs recurring pitfalls in various topics, including managing client-side state persistence and reactivity, surprising design decisions, and so on.

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

#### 2025-11-06: useLocalStorage hook instances race to overwrite each other

**Desired behavior that didn't work**: Removed articles should persist their removed state after page refresh.

**What actually happened and falsified original thesis**: Article showed "Restore" button immediately after removal, but after refresh showed "Remove" button. We had wrongly assumed one useLocalStorage instance per key would prevent conflicts.

**Cause & Fix**: Multiple useLocalStorage hook instances (one per ArticleCard) each owned their own copy of the payload. When one instance stored an update, other instances later wrote their stale copy back, erasing the change. Rewrote useLocalStorage to use useSyncExternalStore so every subscriber reads and writes through a single source of truth, dramatically simplifying the flow and eliminating the race.

---

#### 2025-10-31 `3bfceee`: State property lost during cache merge

**Desired behavior that didn't work**: When hiding a TLDR, the article should move to bottom so users can deprioritize completed items.

**What actually happened and falsified original thesis**: The article stayed in place. We had wrongly assumed that saving the state property to storage was sufficient.

**Cause & Fix**: The merge function wasn't transferring the new property from cached data. The fix was to add the missing property to the merge operation.

