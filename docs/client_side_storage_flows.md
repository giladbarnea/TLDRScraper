# Client-Side Local Storage Architecture

This document expands the "everything lives in the browser" design by mapping each feature to its client-owned data and event sequence. The browser is the sole source of truth: every user action mutates in-memory state first, immediately mirrors that change to `localStorage`, and renders directly from the hydrated objects. No other persistence layer exists.

## Local Storage Keys and Shapes

| Key | Shape | Purpose |
| --- | ----- | ------- |
| `tldr:scrapes:<ISO-date>` | `{ articles: Article[], issues: Issue[], cachedAt: ISO-string }` | Stores the newsletter payload for a specific day. Each `Article` carries summary, TLDR, removal, and read flags. |

`Article` objects include the fields below; they are the *only* authority for card rendering.

```
type Article = {
    url: string;              // canonical key
    title: string;
    issueDate: string;        // same ISO date used in key
    section: string | null;
    removed: boolean;
    summary: {
        status: 'unknown' | 'available' | 'creating' | 'error';
        markdown?: string;
        effort: 'low' | 'medium' | 'high';
        checkedAt?: ISO-string;
        errorMessage?: string;
    };
    tldr: {
        status: 'unknown' | 'available' | 'creating' | 'error';
        markdown?: string;
        effort: 'low' | 'medium' | 'high';
        checkedAt?: ISO-string;
        errorMessage?: string;
    };
    read: {
        isRead: boolean;
        markedAt?: ISO-string;
    };
};
```

`Issue` objects mirror the current cache format (metadata, sections) and are unchanged.

---

## Summaries → `"Available"` UI State

### Flow A – Hydrate daily payload

```
User opens dashboard
        ↓
HydrateController
        ├─ readLocal('tldr:scrapes:<date>')
        │       ↓
        │   hit → hydrate in-memory store exactly as saved (including summary/tldr/read state)
        │   miss → fetchNewsletter(date)
        │           ↓
        │       normalize articles → set summary.status='unknown'
        │       writeLocal('tldr:scrapes:<date>', payload)
        └─ Renderer draws cards from hydrated store
```

### Flow B – User requests summary

```
User clicks Summary button
        ↓
SummaryController
        ├─ lookup article from in-memory store (already hydrated from localStorage)
        ├─ if article.summary.markdown exists
        │       ↓
        │   toggle inline view
        │   markArticleAsRead()
        ├─ else if status !== 'creating'
        │       ↓
        │   set status='creating', writeLocal()
        │   fetch('/api/summarize-url', { method: 'POST', body: { url } })
        │       ↓
        │   on success → persist markdown, status='available'
        │   on failure → status='error', set errorMessage
        │   writeLocal()
        └─ Renderer reacts to state: shows markdown, spinner, or error message
```

*Outcome:* `Article.summary.status` flips to `'available'` only when `article.summary.markdown` is stored locally, so the UI and persistence are always in lockstep.

---

## TLDR → `"Available"` UI State

### Flow C – Hydrate TLDR state

```
HydrateController completes Flow A
        ↓
Articles in memory already include whatever TLDR state localStorage held
        ↓
Renderer labels TLDR buttons directly from article.tldr.status
```

### Flow D – User requests TLDR creation

```
User clicks TLDR button
        ↓
TldrController
        ├─ read article from store
        ├─ if tldr.markdown exists → toggle display, mark as read
        ├─ else if status !== 'creating'
        │       ↓
        │   set status='creating', writeLocal()
        │   fetch('/api/tldr-url', { method: 'POST', body: { url } })
        │       ↓
        │   on success → status='available', markdown=resp.tldr_markdown
        │   on failure → status='error', errorMessage
        │   writeLocal()
        └─ Renderer shows TLDR markdown / spinner / error based on state
```

*Outcome:* TLDR availability is always inferred from `Article.tldr.status`, which only becomes `'available'` after the TLDR markdown is persisted locally.

---

## Marked as Read State

The read toggle is purely client-owned; it never reaches the server.

### Flow E – Automatic mark-as-read when content is expanded

```
Summary or TLDR expansion completes
        ↓
ReadStateManager
        ├─ if article.read.isRead already true → no-op
        ├─ else
        │       ↓
        │   set article.read = { isRead: true, markedAt: now }
        │   writeLocal('tldr:scrapes:<date>')
        └─ Renderer adds "Read" styling instantly
```

### Flow F – Manual mark/unmark control (e.g., checkbox or bulk action)

```
User toggles "Mark as read" control
        ↓
ReadStateManager
        ├─ lookup all targeted articles
        ├─ update read.isRead flag per action
        ├─ writeLocal()
        └─ Renderer syncs badges + collapse state
```

*Interaction with other subsystems:* Because `Article.read.isRead` lives inside the same record that holds summary and TLDR metadata, any subsequent hydration (Flow A, and the TLDR reflection in Flow C) replays the read state alongside other fields. No cross-store reconciliation is required.

---

## Cross-Feature Observations

* The same `Article` payload drives every card. Inline mutations (hydration, summary requests, TLDR requests, read toggles) update the record and immediately write the full object back to the owning day key, so future sessions or tabs start from the latest state.
* Because each flow writes through the same serialization path, clearing localStorage or switching browsers simply resets the experience—there is no orphaned state elsewhere.

