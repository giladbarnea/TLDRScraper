---
last_updated: 2026-04-09 09:14, 81662be
---
# Presentation Domain Analysis

**Date**: 2026-04-08
**Scope**: CalendarDay.jsx, NewsletterDay.jsx, ArticleList.jsx, ArticleCard.jsx, FoldableContainer.jsx, ReadStatsBadge.jsx, DigestButton.jsx, ToastContainer.jsx

---

## Executive Summary

The Presentation domain has several clear maintenance issues:

1. **Monolithic ArticleCard.jsx**: A 350+ line file containing 6 components including a full-screen overlay
2. **Duplicated "all removed" check**: Same `articles.every(a => a.removed)` pattern in 4 locations
3. **Duplicated ID construction**: Component IDs built inline in every container component
4. **URL parsing logic inline**: Domain extraction logic embedded in component body
5. **Effect timing issue in FoldableContainer**: `defaultFolded` effect runs unnecessarily on every render

---

## Finding 1: Monolithic ArticleCard.jsx

### Location

`client/src/components/ArticleCard.jsx` (entire file, 354 lines)

### Problem

ArticleCard.jsx contains 6 components:
- `ErrorToast` (lines 12-26)
- `ZenModeOverlay` (lines 28-121) — **94 lines, a full-screen portal component**
- `ArticleTitle` (lines 123-134)
- `ArticleMeta` (lines 136-159)
- `SummaryError` (lines 161-166)
- `ArticleCard` (lines 168-354)

The `ZenModeOverlay` component alone is larger than most other components in the codebase. It manages:
- Scroll state (`hasScrolled`)
- Three gesture hooks (`useScrollProgress`, `usePullToClose`, `useOverscrollUp`)
- Portal rendering
- Escape key handling
- Body overflow locking
- Progress bar animation
- Overscroll completion UI

### Evidence

```javascript
// ArticleCard.jsx - The main component body contains:
// 1. URL parsing logic (lines 124-138)
// 2. Click handler with multiple conditionals (lines 148-163)
// 3. Two useEffect hooks (lines 165-182)
// 4. A complex JSX return with Framer Motion (lines 184-288)
// 5. Plus the embedded ZenModeOverlay component
```

### Impact

- **Cognitive overload**: Readers must understand 6 components to understand the file
- **Poor discoverability**: ZenModeOverlay is not findable via file search
- **Testing difficulty**: Cannot test ZenModeOverlay in isolation
- **Coupling**: ZenModeOverlay is only used here but contains substantial logic

---

## Finding 2: Duplicated "All Removed" Check

### Locations

1. `CalendarDay.jsx:27`
2. `NewsletterDay.jsx:54`
3. `NewsletterDay.jsx:16` (Section component)
4. `NewsletterDay.jsx:48` (IssueSubtitle)

### Problem

The same check appears in 4 places:

```javascript
// CalendarDay.jsx:27
const allArticlesRemoved = articles.length > 0 && articles.every(a => a.removed)

// NewsletterDay.jsx:54
const allRemoved = articles.length > 0 && articles.every(a => a.removed)

// NewsletterDay.jsx:16 (Section)
const allRemoved = articles.every(a => a.removed)

// NewsletterDay.jsx:48 (IssueSubtitle) - uses same allRemoved variable
```

### Differences

| Location | Empty array check | Variable name |
|----------|-------------------|---------------|
| CalendarDay | `articles.length > 0` | `allArticlesRemoved` |
| NewsletterDay | `articles.length > 0` | `allRemoved` |
| Section | None (assumes non-empty) | `allRemoved` |

### Impact

- Inconsistent handling of empty arrays
- Different variable names for the same concept
- Adding new conditions (e.g., `a.read?.isRead`) requires touching multiple files

---

## Finding 3: Inline URL Parsing in Component Body

### Location

`ArticleCard.jsx:124-138`

### Problem

URL parsing to extract `displayDomain` and `hostname` happens inline:

```javascript
const { displayDomain, hostname } = (() => {
  try {
    const urlObj = new URL(fullUrl)
    const h = urlObj.hostname
    const d = h.replace(/^www\./, '').split('.')[0].toLowerCase()
    return { displayDomain: d, hostname: h }
  } catch {
    return { displayDomain: null, hostname: null }
  }
})()
```

This IIFE runs on every render. The same URL parsing pattern appears again in `ZenModeOverlay` where it receives these values as props.

### Impact

- Unnecessary re-computation on every render
- Logic not reusable if needed elsewhere
- The same URL is parsed twice: once for ArticleCard props, once passed to ZenModeOverlay

---

## Finding 4: Duplicated Component ID Construction

### Locations

- `ArticleCard.jsx:64`: `` `article-${article.url}` ``
- `CalendarDay.jsx:29`: `` `calendar-${date}` ``
- `NewsletterDay.jsx:65`: `` `newsletter-${date}-${issue.source_id}` ``
- `NewsletterDay.jsx:31`: `` `section-${date}-${sourceId}-${sectionKey}` ``

### Problem

These ID patterns are duplicated across the hierarchy. Each parent must also compute `descendantIds`:

```javascript
// CalendarDay.jsx:30-31
const componentId = `calendar-${date}`
const descendantIds = articles.map(a => `article-${a.url}`)

// NewsletterDay.jsx:66-68
const componentId = `newsletter-${date}-${issue.source_id}`
const descendantIds = articles.map(a => `article-${a.url}`)

// NewsletterDay.jsx:32-33 (Section)
const componentId = `section-${date}-${sourceId}-${sectionKey}`
const descendantIds = articles.map(a => `article-${a.url}`)
```

### Impact

If the ID format changes, all locations must be updated. The `article-` prefix is hardcoded in 3 places for descendant computation.

---

## Finding 5: FoldableContainer Effect Timing Issue

### Location

`FoldableContainer.jsx:11-15`

### Problem

```javascript
useEffect(() => {
  if (defaultFolded) {
    setExpanded(id, false)
  }
}, [defaultFolded, id, setExpanded])
```

This effect runs on every render where `defaultFolded` is truthy, not just when it becomes true. If `defaultFolded` is a computed value that stays `true` across renders, the effect fires repeatedly.

### Impact

- Unnecessary dispatch calls to the interaction reducer
- Could cause subtle bugs if other components are watching expand state changes

### Expected Behavior

Should only run when `defaultFolded` transitions to `true`, or on initial mount.

---

## Finding 6: ReadStatsBadge vs "All Removed" Logic Overlap

### Location

`ReadStatsBadge.jsx:3-7`

### Problem

```javascript
const completedCount = articles.filter(a => a.read?.isRead || a.removed).length
```

The `ReadStatsBadge` counts articles that are read OR removed. But the "all removed" check elsewhere only checks `a.removed`. This creates an inconsistency:

- **Badge logic**: Read articles count as "completed"
- **Auto-fold logic**: Only removed articles trigger auto-fold

### Evidence

| Feature | Condition | Location |
|---------|-----------|----------|
| ReadStatsBadge completion | `a.read?.isRead \|\| a.removed` | ReadStatsBadge.jsx:6 |
| Auto-fold (CalendarDay) | `a.removed` | CalendarDay.jsx:27 |
| Auto-fold (NewsletterDay) | `a.removed` | NewsletterDay.jsx:54 |

### Impact

- An article marked as "read" shows in the badge as completed, but doesn't trigger auto-fold
- Semantic inconsistency between "completed" and "folded"
- May confuse users who expect "all read" to also trigger auto-fold

---

## Finding 7: Data Attribute Overload in ArticleCard

### Location

`ArticleCard.jsx:224-234`

### Problem

13 data attributes are set on the motion.div:

```javascript
data-article-title={article.title}
data-article-url={article.url}
data-article-date={article.issueDate}
data-article-category={article.category}
data-article-source={article.sourceId}
data-read={isRead}
data-removed={isRemoved}
data-state-loading={stateLoading}
data-summary-status={summary.status}
data-summary-expanded={summary.expanded}
data-summary-available={isAvailable}
data-dragging={isDragging}
data-can-drag={swipeEnabled}
```

### Impact

- JSX noise (13 lines of data attributes)
- Unclear which are for debugging vs testing vs production use
- Some values are redundant with props already passed (e.g., `article.title`)

---

## Finding 8: Duplicate DescendantIds Computation

### Location

Already noted in the interaction-selection analysis, but manifests in the presentation layer:

- `CalendarDay.jsx:31`
- `NewsletterDay.jsx:67`
- `NewsletterDay.jsx:33`

### Problem

Every container component computes its own `descendantIds` by mapping articles:

```javascript
const descendantIds = articles.map(a => `article-${a.url}`)
```

This requires each container to:
1. Know the ID format of its children (`article-` prefix)
2. Have access to the full articles array
3. Recompute on every render

### Impact

If ArticleCard's ID format changes, all parent containers must be updated.

---

## Finding 9: Toast Animation Constants in Component

### Location

`ToastContainer.jsx:8-9`

### Problem

```javascript
const TOAST_VISIBLE_MS = 12000
const EXIT_ANIMATION_MS = 350
```

These are defined inside the module but could be:

1. Extracted to a constants file
2. Configurable via props
3. Shared with other animation timings

### Impact

Low severity, but adds to the file's cognitive load.

---

## Finding 10: ZenModeOverlay State Management Embedded

### Location

`ArticleCard.jsx:31-121` (ZenModeOverlay component)

### Problem

The overlay manages multiple pieces of state and effects:

```javascript
// State
const [hasScrolled, setHasScrolled] = useState(false)

// Refs
const containerRef = useRef(null)
const scrollRef = useRef(null)

// Hooks
const progress = useScrollProgress(scrollRef)
const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose })
const { overscrollOffset, ... } = useOverscrollUp({ scrollRef, onComplete, threshold: 60 })

// Effects
useEffect(() => {
  document.body.style.overflow = 'hidden'
  // ... escape handler, scroll listener
  return () => { /* cleanup */ }
}, [onClose])
```

This is a complete sub-application embedded inside ArticleCard.

### Impact

- ArticleCard.jsx becomes a "God component"
- Hard to understand card rendering without reading overlay logic
- Cannot test overlay in isolation
- Cannot reuse overlay patterns elsewhere (e.g., DigestOverlay duplicates similar logic)

---

## Finding 11: DigestButton Extracts Articles on Every Render

### Location

`DigestButton.jsx:1-7`

### Problem

```javascript
function extractArticleDescriptors(selectedIds, payloads) {
  const allArticles = payloads.flatMap((payload) => payload.articles)
  return allArticles
    .filter((article) => selectedIds.has(`article-${article.url}`))
    .map(({ url, title, category, sourceId }) => ({ url, title, category, sourceId }))
}
```

Called on every render in `handleClick`:

```javascript
function handleClick() {
  const descriptors = extractArticleDescriptors(selectedIds, payloads)
  onTrigger(descriptors)
}
```

### Impact

- For large payloads, this flatMap + filter + map runs on every click
- Low severity since it only runs on click, but could be memoized

---

## Finding 12: Inconsistent Opacity Fading Pattern

### Locations

- `NewsletterDay.jsx:20` (Section headerClassName)
- `NewsletterDay.jsx:23` (Section content div)
- `NewsletterDay.jsx:50` (IssueSubtitle)

### Problem

The `opacity-50` class is applied conditionally when `allRemoved` is true:

```javascript
// Section header
headerClassName={`transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}

// Section content
<div className={`mt-2 transition-all duration-300 ${allRemoved ? 'opacity-50' : ''}`}>

// IssueSubtitle
<div className={`mb-3 text-xs ... ${allRemoved ? 'opacity-50' : ''}`}>
```

### Impact

- Same pattern repeated 3 times
- The `transition-all duration-300` classes are duplicated
- Changing the fade style requires updating multiple locations

---

## Finding 13: NewsletterDay Contains Two Components

### Location

`NewsletterDay.jsx` (entire file)

### Problem

The file contains both:
1. `Section` component (lines 23-44)
2. `NewsletterDay` component (lines 54-87)

Plus helper functions `groupArticlesBySection` and `getSortedSectionKeys`.

### Impact

- Section is only used by NewsletterDay but is a full component
- Could be extracted to its own file for clarity
- File structure doesn't match the component hierarchy (Section is a child, not a sibling)

---

## Summary Table

| Finding | Severity | Effort | Impact |
|---------|----------|--------|--------|
| Monolithic ArticleCard.jsx | High | High | Splits 350 lines into separate files |
| Duplicated "all removed" check | Medium | Low | Single utility function |
| Inline URL parsing | Medium | Low | Extract to utility |
| Duplicated ID construction | Medium | Low | Centralize ID builders |
| FoldableContainer effect timing | Low | Low | Add mount check |
| ReadStatsBadge vs auto-fold inconsistency | Low | Medium | Semantic clarification needed |
| Data attribute overload | Low | Low | Remove debugging attributes |
| Duplicate descendantIds | Medium | Low | Shared with interaction layer |
| Toast constants | Low | Low | Extract to config |
| ZenModeOverlay embedded | High | Medium | Extract to own file |
| DigestButton extraction | Low | Low | Memoize if needed |
| Inconsistent opacity fading | Low | Low | CSS class composition |
| NewsletterDay contains Section | Low | Low | File split |

---

## Recommended Priority

1. **#1 + #10 (Extract ZenModeOverlay)** — Highest value. Creates a clear separation and enables testing.
2. **#2 (Consolidate "all removed" check)** — Quick win, improves consistency.
3. **#4 (Centralize ID construction)** — Reduces coupling between parent/child components.
4. **#5 (Fix FoldableContainer effect)** — Prevents subtle bugs.
5. **#6 (Clarify read vs removed semantics)** — Decide what "completed" means.
6. **#13 (Split Section to own file)** — Improves file organization.

---

## Files Referenced

| File | Lines | Components |
|------|-------|------------|
| `client/src/components/ArticleCard.jsx` | 1-354 | ErrorToast, ZenModeOverlay, ArticleTitle, ArticleMeta, SummaryError, ArticleCard |
| `client/src/components/CalendarDay.jsx` | 1-63 | CalendarDayTitle, NewsletterList, CalendarDay |
| `client/src/components/NewsletterDay.jsx` | 1-88 | IssueSubtitle, SectionTitle, Section, SectionsList, NewsletterDay |
| `client/src/components/ArticleList.jsx` | 1-19 | ArticleList |
| `client/src/components/FoldableContainer.jsx` | 1-43 | FoldableContainer |
| `client/src/components/ReadStatsBadge.jsx` | 1-12 | ReadStatsBadge |
| `client/src/components/DigestButton.jsx` | 1-28 | DigestButton |
| `client/src/components/ToastContainer.jsx` | 1-79 | Toast, ToastContainer |
