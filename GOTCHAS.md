---
last_updated: 2025-11-24 19:04, c120e94
---
# Gotchas

This document catalogs recurring pitfalls in various topics, including managing client-side state persistence and reactivity, surprising design decisions, and so on.

---

#### 2025-11-24: Removed article repositioning on TLDR collapse

session-id: 01UFCK16ngqZGTQNBXCogUbU

**Feature removed**: Previously, when a user collapsed a TLDR, the article would be marked as `tldrHidden` and repositioned to a lower position in the list (below read articles, above removed articles). This "deprioritization" behavior has been removed.

**Current behavior**: Articles now maintain their position when TLDRs are collapsed. The `tldrHidden` property is still tracked internally but no longer affects article sorting.

**Changes made**:
- `ArticleList.jsx:7-12` - Removed `tldrHidden` from sorting logic (3-state system now: unread→read→removed)
- `ARCHITECTURE.md:154,167,868-881` - Updated documentation to remove references to deprioritization behavior

**Historical context**: The deprioritization feature was originally implemented to help users move articles they'd finished reading to the bottom of their feed. However, this automatic repositioning was confusing and not desired. The feature existed from 2025-10-31 through 2025-11-24.

---

#### 2025-11-24: Removed article repositioning on read/unread state changes

session-id: 01UFCK16ngqZGTQNBXCogUbU

**Feature removed**: Previously, articles were repositioned based on read/unread state. The sorting system used a 3-state priority: unread (top) → read (middle) → removed (bottom). When a user marked an article as read (by clicking the title or expanding TLDR), the article would move from the top section to the middle section.

**Current behavior**: Articles maintain their original position when marked as read/unread. Only removed articles are repositioned (to bottom). The `read` property is still tracked and displayed visually (bold for unread, muted for read) but no longer affects article sorting.

**Changes made**:
- `ArticleList.jsx:7-8` - Simplified sorting to 2-state system (removed: 1, everything else: 0)
- `ARCHITECTURE.md:167,868-881` - Updated documentation to reflect new sorting behavior

**Rationale**: Automatic repositioning when reading articles was unexpected and disorienting. Users prefer articles to stay in their original order as they read through them. Removed articles still go to bottom as this is an explicit "hide this" action.

**State transitions affected**:
- Mark as read (click title, expand TLDR) - NO LONGER repositions
- Toggle read/unread - NO LONGER repositions
- Remove/restore - STILL repositions (moved to bottom / restored to original position)

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

#### 2025-11-04 `102a8dcd`: HackerNews articles not displayed in UI because of surprising server response shape

**Desired behavior that didn't work**: HackerNews articles fetched by backend should appear in the UI.

**What actually happened and falsified original thesis**: HackerNews articles were fetched (183 articles in API response) but invisible in the UI. We had wrongly assumed `articles` field alone was sufficient for display.

**Cause & Fix**: The frontend requires both `articles` and `issues` arrays. It only displays articles that match an issue's category. HackerNews adapter returned empty `issues` array, so all HN articles were filtered out during rendering. The fix was to generate fake issue objects for each HackerNews category.

---

#### 2025-10-31 `3bfceee`: State property lost during cache merge

**Desired behavior that didn't work**: When hiding a TLDR, the article should move to bottom so users can deprioritize completed items.

**What actually happened and falsified original thesis**: The article stayed in place. We had wrongly assumed that saving the state property to storage was sufficient.

**Cause & Fix**: The merge function wasn't transferring the new property from cached data. The fix was to add the missing property to the merge operation.

---

#### 2025-10-31 `16bd653`: Component not reactive to storage changes

**Desired behavior that didn't work**: When state changes in storage, the list should re-sort so visual order reflects current state.

**What actually happened and falsified original thesis**: The list used stale prop values. We had wrongly assumed that components automatically react to storage mutations.

**Cause & Fix**: Computed properties only track their declared dependencies. The fix was to dispatch custom events on storage writes and listen for them in consuming components.

---
