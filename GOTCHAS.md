---
last-updated: 2025-11-03 23:13, b43b1c6
---
# Gotchas

This document catalogs recurring pitfalls in various topics, including managing client-side state persistence and reactivity, surprising design decisions, and so on.

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
