---
last_updated: 2025-11-16 05:28, c2b5db7
---
# Gotchas

This document catalogs recurring pitfalls in various topics, including managing client-side state persistence and reactivity, surprising design decisions, and so on.

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
