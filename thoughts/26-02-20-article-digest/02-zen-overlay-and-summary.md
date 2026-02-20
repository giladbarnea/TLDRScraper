---
last_updated: 2026-02-20 13:24, 99f0acd
---
# Analysis: ZenOverlay/ZenMode System and Summary Flow

## Overview
The ZenMode overlay is a full-screen, immersive reading experience that displays AI-generated summaries as sanitized HTML. It uses a global "zen lock" to ensure only one overlay can be open at a time, and integrates pull-to-close, overscroll-to-mark-removed gestures, and scroll progress tracking. Summary content flows from API response → markdown storage → HTML rendering via marked.js and DOMPurify.

## Entry Points

1. `client/src/components/ArticleCard.jsx:30-173` - ZenModeOverlay component
2. `client/src/components/ArticleCard.jsx:363-376` - ZenModeOverlay invocation
3. `client/src/hooks/useSummary.js:27-222` - useSummary hook (fetch, expand, toggle, abort/rollback)
4. `client/src/reducers/summaryDataReducer.js:1-84` - Summary state machine
5. `client/src/hooks/useOverscrollUp.js:3-72` - Overscroll-to-mark-removed gesture
6. `client/src/hooks/usePullToClose.js:3-61` - Pull-down-to-close gesture
7. `client/src/hooks/useScrollProgress.js:3-23` - Scroll progress indicator

## Core Implementation

### 1. ZenModeOverlay Component (`client/src/components/ArticleCard.jsx:30-173`)

**Purpose**: Full-screen overlay that renders summary content with gestures and navigation.

**Structure**:
- Rendered via `createPortal(...)` at `document.body` level (`:66-172`)
- Fixed positioning with `z-[100]` (`:68`)
- Animated entry with `animate-zen-enter` (`:74`)
- Body overflow hidden while open (`:47`)

**Visual Layout**:
- **Header** (`:76-122`): Close button, domain/favicon link, mark-removed button, scroll progress bar
  - Close button (`:84-89`): `ChevronDown` icon, triggers `onClose`
  - Domain link (`:91-108`): Clickable external link with favicon and metadata
  - Mark-removed button (`:110-115`): `Check` icon, triggers `onMarkRemoved`
  - Progress bar (`:118-121`): Horizontal indicator scaling with scroll progress
- **Content Area** (`:125-168`): Scrollable summary HTML
  - Prose-styled container (`:134-137`): Tailwind typography classes
  - `dangerouslySetInnerHTML` renders sanitized HTML (`:136`)
  - Overscroll completion zone (`:142-167`): Visual feedback for mark-removed gesture

**Props**:
- `url`: Full article URL
- `html`: Sanitized HTML from summary markdown
- `hostname`, `displayDomain`: Domain metadata
- `articleMeta`: Article metadata (author, date, etc.)
- `onClose`: Callback to collapse overlay
- `onMarkRemoved`: Callback to mark article as removed and close overlay

**Gestures**:
- Pull-to-close: `usePullToClose` (`:35`), transforms overlay Y position (`:70`)
- Overscroll-to-mark-removed: `useOverscrollUp` (`:36-40`), translates content (`:129`)
- Scroll progress: `useScrollProgress` (`:34`), drives progress bar (`:120`)

**State**:
- `hasScrolled`: Toggles header blur/border when scrolled past 10px (`:31, :54-56, :81`)

**Keyboard**:
- Escape key closes overlay (`:48-51`)

**Cleanup**:
- Restores `document.body.overflow` on unmount (`:60`)

### 2. ZenModeOverlay Invocation (`client/src/components/ArticleCard.jsx:363-376`)

**Trigger Condition**: Rendered when `!isRemoved && summary.expanded && summary.html` (`:363`)

**Props Passed**:
- `url={fullUrl}`: HTTP-prefixed URL (`:365`)
- `html={summary.html}`: Sanitized HTML from `useSummary` (`:366`)
- `hostname`, `displayDomain`: Extracted from URL (`:367-368`)
- `articleMeta`: Article metadata (`:369`)
- `onClose={() => summary.collapse()}`: Collapses summary view (`:370`)
- `onMarkRemoved`: Collapses without marking as read, then marks as removed (`:371-374`)

**Integration**: Conditional render within ArticleCard, triggered by `summary.expanded` state.

### 3. Zen Lock Mechanism (`client/src/hooks/useSummary.js:11-25`)

**Purpose**: Global mutex ensuring only one ZenModeOverlay can be open at a time across all ArticleCards.

**State**: Module-level variable `zenLockOwner` (`:11`) stores current owner URL or `null`.

**Functions**:
- `acquireZenLock(url)` (`:13-19`): Attempts to acquire lock. Returns `true` if successful (lock was `null`), `false` if another URL holds it.
- `releaseZenLock(url)` (`:21-25`): Releases lock only if `zenLockOwner === url`.

**Usage in useSummary**:
- Acquired on successful fetch (`:131-134`): After `SUMMARY_LOAD_SUCCEEDED`, if lock acquired, set `expanded = true`.
- Acquired on toggle expand (`:174-177`): When `isAvailable && !expanded`, acquire lock before expanding.
- Acquired on explicit expand (`:191-194`): Direct expand call acquires lock.
- Released on collapse (`:185`): Always releases lock when collapsing.
- Released on unmount (`:199`): Cleanup ensures lock is released if component unmounts.

**Behavior**: If user taps ArticleCard A while ArticleCard B's overlay is open, ArticleCard A's `acquireZenLock` fails, so ArticleCard A won't expand. User must first close B's overlay to free the lock.

### 4. Summary Content Flow: API → Storage → HTML

**Flow Stages**:

1. **Fetch Request** (`useSummary.js:83-168`):
   - User taps article or calls `summary.toggle()` (`:170-181`)
   - If not available, `fetchSummary(effort)` called (`:83`)
   - Abort previous request if pending (`:86-90`)
   - Create unique request token (`:92-93`)
   - Store previous summary data for rollback (`:94`)
   - Dispatch `SUMMARY_REQUESTED` event (`:97-103`), sets status to `LOADING`
   - POST to `/api/summarize-url` with `{ url, summarize_effort }` (`:108-116`)

2. **API Response Processing** (`:118-145`):
   - Parse JSON response (`:118`)
   - Validate request token to avoid race conditions (`:120`)
   - **Success path** (`:122-134`):
     - Dispatch `SUMMARY_LOAD_SUCCEEDED` with `markdown`, `effort`, `checkedAt` (`:123-128`)
     - Clear request token and previous data (`:129-130`)
     - Acquire zen lock and expand if successful (`:131-134`)
   - **Failure path** (`:135-144`):
     - Dispatch `SUMMARY_LOAD_FAILED` with `errorMessage` (`:136-142`)
     - Clear request token and previous data (`:143-144`)

3. **Abort/Rollback** (`:146-156`):
   - If `AbortError` thrown (request aborted), dispatch `SUMMARY_ROLLBACK` with `previousData` (`:147-155`)
   - Restores previous summary state (`:71-79` in `summaryDataReducer.js`)

4. **Storage Update** (`useSummary.js:57-79`):
   - `dispatchSummaryEvent` calls `reduceSummaryData` from reducer (`:61`)
   - Reducer returns `{ state, patch }` (`:61`)
   - Patch applied via `updateArticle` (`:72-77`)
   - Article updated in Supabase storage via `useArticleState.updateArticle` (`:28`)

5. **Markdown → HTML Conversion** (`useSummary.js:39-50`):
   - Read `markdown` from `article.summary.markdown` (`:37`)
   - Parse with `marked.parse(markdown)` (`:42`)
   - Sanitize with `DOMPurify.sanitize(rawHtml, { ADD_TAGS: ['annotation', 'semantics'] })` (`:43-45`)
   - Return sanitized HTML (`:43`)
   - Error handling: Returns empty string on parse failure (`:46-49`)

6. **Rendering** (`ArticleCard.jsx:363-376`):
   - `summary.html` passed to `ZenModeOverlay` (`:366`)
   - Rendered via `dangerouslySetInnerHTML` (`:136`)

**Data Shape**:
```javascript
article.summary = {
  status: 'available',  // 'unknown' | 'loading' | 'available' | 'error'
  markdown: '# Summary\n\nContent...',
  effort: 'low',  // 'low' | 'medium' | 'high'
  checkedAt: '2026-02-20T12:00:00Z',
  errorMessage: null
}
```

### 5. useSummary Lifecycle (`client/src/hooks/useSummary.js:27-222`)

**Hook Signature**: `useSummary(date, url, type = 'summary')`

**Dependencies**:
- `useArticleState(date, url)`: Provides article data, `updateArticle` function, read state (`:28`)
- `summaryDataReducer`: State machine for summary data transitions (`:6`)
- `marked`, `DOMPurify`: Markdown parsing and HTML sanitization (`:1-2`)

**State**:
- `expanded`: Boolean, overlay open/closed (`:29`)
- `effort`: Current effort level ('low', 'medium', 'high') (`:30`)
- `abortControllerRef`: AbortController for canceling fetch (`:31`)
- `requestTokenRef`: Unique token for request deduplication (`:32`)
- `previousSummaryDataRef`: Snapshot for rollback on abort (`:33`)

**Derived State**:
- `data`: `article.summary` object (`:35`)
- `status`: Summary status from reducer (`:36`)
- `markdown`: Raw markdown string (`:37`)
- `html`: Sanitized HTML from markdown (`:39-50`)
- `errorMessage`: Error message if status is ERROR (`:52`)
- `isAvailable`: Status is AVAILABLE and markdown exists (`:53`)
- `isLoading`: Status is LOADING (`:54`)
- `isError`: Status is ERROR (`:55`)

**Public Methods**:

1. **`fetchSummary(summaryEffort = effort)`** (`:83-168`):
   - Aborts pending request if exists (`:86-90`)
   - Creates new AbortController and request token (`:89-93`)
   - Saves previous summary data for rollback (`:94`)
   - Dispatches `SUMMARY_REQUESTED` event (`:97-103`)
   - POSTs to `/api/summarize-url` (`:105-116`)
   - On success: Dispatches `SUMMARY_LOAD_SUCCEEDED`, acquires zen lock, expands (`:122-134`)
   - On failure: Dispatches `SUMMARY_LOAD_FAILED` (`:136-144`)
   - On abort: Dispatches `SUMMARY_ROLLBACK` to restore previous state (`:147-155`)

2. **`toggle(summaryEffort)`** (`:170-181`):
   - If `isAvailable`:
     - If `expanded`: Call `collapse()` (`:173`)
     - Else: Acquire zen lock and expand (`:174-177`)
   - Else: Call `fetchSummary(summaryEffort)` (`:179`)

3. **`collapse(markAsReadOnClose = true)`** (`:183-188`):
   - Logs transition (`:184`)
   - Releases zen lock (`:185`)
   - Sets `expanded = false` (`:186`)
   - If `markAsReadOnClose && !isRead`, marks article as read (`:187`)

4. **`expand()`** (`:190-195`):
   - Acquires zen lock (`:191`)
   - If successful, logs transition and sets `expanded = true` (`:192-193`)

**Cleanup** (`:197-204`):
- Releases zen lock (`:199`)
- Aborts pending request (`:200-202`)

**Return Object** (`:206-221`):
```javascript
{
  data,           // Raw summary data object
  status,         // 'unknown' | 'loading' | 'available' | 'error'
  markdown,       // Raw markdown string
  html,           // Sanitized HTML
  errorMessage,   // Error message if status is ERROR
  loading,        // Boolean (isLoading)
  expanded,       // Boolean, overlay open state
  effort,         // Current effort level
  isAvailable,    // Boolean, ready to display
  isError,        // Boolean, failed state
  fetch,          // fetchSummary function
  toggle,         // toggle function
  collapse,       // collapse function
  expand          // expand function
}
```

### 6. Summary Data State Machine (`client/src/reducers/summaryDataReducer.js:1-84`)

**States** (`:1-6`):
- `UNKNOWN`: Initial state, no data
- `LOADING`: Fetch in progress
- `AVAILABLE`: Summary loaded successfully
- `ERROR`: Fetch failed

**Events** (`:8-14`):
- `SUMMARY_REQUESTED`: User requests summary
- `SUMMARY_LOAD_SUCCEEDED`: API returned success
- `SUMMARY_LOAD_FAILED`: API returned error
- `SUMMARY_RESET`: Clear summary data
- `SUMMARY_ROLLBACK`: Restore previous state (on abort)

**Reducer Function** (`:29-84`):

`reduceSummaryData(summaryData, event)` returns `{ state, patch }`:

- **`SUMMARY_REQUESTED`** (`:33-41`):
  - Transitions to `LOADING`
  - Patch: `{ status: 'loading', effort, errorMessage: null }`

- **`SUMMARY_LOAD_SUCCEEDED`** (`:42-52`):
  - Transitions to `AVAILABLE`
  - Patch: `{ status: 'available', markdown, effort, checkedAt, errorMessage: null }`

- **`SUMMARY_LOAD_FAILED`** (`:53-60`):
  - Transitions to `ERROR`
  - Patch: `{ status: 'error', errorMessage }`

- **`SUMMARY_RESET`** (`:61-70`):
  - Transitions to `UNKNOWN`
  - Patch: `{ status: 'unknown', markdown: '', errorMessage: null, checkedAt: null }`

- **`SUMMARY_ROLLBACK`** (`:71-80`):
  - Transitions to previous state (from `event.previousData`)
  - Patch: Restores `previousData` or defaults to UNKNOWN state

**Helper**: `getSummaryDataStatus(summaryData)` (`:16-18`) extracts status, defaults to `UNKNOWN`.

### 7. Gesture Hooks

#### useOverscrollUp (`client/src/hooks/useOverscrollUp.js:3-72`)

**Purpose**: Detects upward overscroll at bottom of scroll container to trigger mark-as-removed action.

**Parameters**:
- `scrollRef`: Ref to scrollable element
- `onComplete`: Callback when threshold exceeded
- `threshold`: Pixel distance to trigger completion (default 60)

**State**:
- `overscrollOffset`: Current overscroll distance in pixels (`:4`)
- `overscrollOffsetRef`: Ref to latest offset for touch handlers (`:5`)
- `startY`: Touch start Y coordinate (`:6`)
- `isOverscrolling`: Boolean flag (`:7`)

**Touch Handlers**:
- **`touchstart`** (`:22-26`): If at bottom (`scrollHeight - scrollTop - clientHeight < 1`), record `startY`
- **`touchmove`** (`:28-42`):
  - Calculate `deltaY = startY - currentY` (`:31`)
  - If `deltaY > 0` (upward swipe) and at bottom: Prevent default, set `isOverscrolling = true`, set offset to `min(deltaY * 0.5, threshold * 1.5)` (`:33-36`)
  - If `deltaY < -10` (downward swipe): Reset state (`:37-40`)
- **`touchend`** (`:44-51`): If `isOverscrolling && offset >= threshold * 0.5`, call `onComplete()` (`:45-46`)

**Return** (`:66-71`):
```javascript
{
  overscrollOffset,           // Current pixel offset
  isOverscrolling: offset > 0, // Boolean
  progress: min(offset / (threshold * 0.5), 1), // 0-1 progress
  isComplete: progress >= 1   // Threshold reached
}
```

**Usage in ZenModeOverlay**:
- Translate content Y position: `transform: translateY(-offset * 0.4)` (`:129`)
- Show completion indicator when `isOverscrolling` (`:145`)
- Animate CheckCircle icon based on `progress` (`:162-163`)

#### usePullToClose (`client/src/hooks/usePullToClose.js:3-61`)

**Purpose**: Detects downward pull gesture at top of overlay to close.

**Parameters**:
- `containerRef`: Ref to overlay container
- `scrollRef`: Ref to scrollable element
- `onClose`: Callback when threshold exceeded
- `threshold`: Pixel distance to trigger close (default 80)

**State**:
- `pullOffset`: Current pull distance in pixels (`:4`)
- `pullOffsetRef`: Ref to latest offset (`:5`)
- `startY`: Touch start Y coordinate (`:6`)
- `isPulling`: Boolean flag (`:7`)

**Touch Handlers**:
- **`touchstart`** (`:17-22`): If touched outside scroll area OR scroll at top, record `startY`
- **`touchmove`** (`:24-38`):
  - Calculate `diff = currentY - startY` (`:27`)
  - If `diff > 0` (downward pull): Prevent default, set `isPulling = true`, set offset to `diff * 0.5` (`:29-32`)
  - If `diff < -10` (upward swipe): Reset state (`:33-36`)
- **`touchend`** (`:40-47`): If `isPulling && offset > threshold`, call `onClose()` (`:41-42`)

**Return** (`:60`): `{ pullOffset }`

**Usage in ZenModeOverlay**:
- Transform overlay Y position: `transform: translateY(${pullOffset}px)` (`:70`)
- Animate transition when released (`:71`)

#### useScrollProgress (`client/src/hooks/useScrollProgress.js:3-23`)

**Purpose**: Tracks scroll progress (0-1) for visual indicator.

**Parameters**: `scrollRef` - Ref to scrollable element

**Implementation** (`:10-14`):
- `maxScroll = scrollHeight - clientHeight`
- `progress = scrollTop / maxScroll`
- Clamped to [0, 1]

**Return**: `progress` (number 0-1)

**Usage in ZenModeOverlay**:
- Progress bar width: `transform: scaleX(${progress})` (`:120`)

## Configuration

**Markdown Parsing** (`useSummary.js:9`):
- `marked.use(markedKatex({ throwOnError: false }))` - KaTeX support for math equations

**HTML Sanitization** (`useSummary.js:43-45`):
- `DOMPurify.sanitize(rawHtml, { ADD_TAGS: ['annotation', 'semantics'] })` - Allows MathML tags

**Gesture Thresholds**:
- Pull-to-close: 80px (default in `usePullToClose.js:3`)
- Overscroll-to-mark: 60px (default in `useOverscrollUp.js:3`, override at `ArticleCard.jsx:39`)

**Scroll Detection**:
- Header blur threshold: 10px (`ArticleCard.jsx:55`)

## Error Handling

**Fetch Errors** (`useSummary.js:146-167`):
- `AbortError`: Rollback to previous state via `SUMMARY_ROLLBACK` (`:147-155`)
- Other errors: Dispatch `SUMMARY_LOAD_FAILED` with error message (`:157-166`)

**Markdown Parse Errors** (`useSummary.js:46-49`):
- Catch and log error, return empty string

**Summary Error Display** (`ArticleCard.jsx:224-230, 359-361`):
- `SummaryError` component renders red toast with error message
- Only shown when `summary.status === 'error'` and `!isRemoved`

## Key Patterns

**Portal Rendering**: ZenModeOverlay uses `createPortal(content, document.body)` (`:66-172`) to render above all other UI at `z-[100]`.

**Global Mutex Lock**: Module-level `zenLockOwner` variable ensures single overlay open across all ArticleCards.

**Request Deduplication**: `requestTokenRef` (`:32`) prevents race conditions when rapid toggles occur.

**State Rollback**: `previousSummaryDataRef` (`:33, :94`) enables undo on abort, preserving previous `AVAILABLE` or `ERROR` state.

**Optimistic Expand**: Zen lock acquired immediately after successful fetch (`:131-134`), auto-expanding overlay.

**Conditional Mark-as-Read**: `collapse(markAsReadOnClose = true)` (`:183`) allows mark-removed action to skip read marking (`:372-374`).

**Gesture Coordination**:
- Pull-to-close: Acts on header/top area when scroll at top (`:18-21` in `usePullToClose.js`)
- Overscroll-to-mark: Acts on content area when scroll at bottom (`:17-20` in `useOverscrollUp.js`)
- No conflict due to opposite scroll positions

**Passive vs. Active Listeners**:
- `touchstart`, `touchend`: Passive (`:53, :55` in `useOverscrollUp.js`)
- `touchmove`: Non-passive (`:54`) to allow `preventDefault()` for overscroll effect

## Data Flow Summary

```
User taps ArticleCard
  ↓
summary.toggle() called
  ↓
fetchSummary() if not available
  ↓
POST /api/summarize-url { url, summarize_effort }
  ↓
API returns { success: true, summary_markdown: '...' }
  ↓
dispatchSummaryEvent(SUMMARY_LOAD_SUCCEEDED, { markdown })
  ↓
reduceSummaryData() returns { state: 'available', patch: { status, markdown, ... } }
  ↓
updateArticle() merges patch into article.summary
  ↓
useSupabaseStorage updates Supabase storage
  ↓
useSummary re-renders with new markdown
  ↓
html = DOMPurify.sanitize(marked.parse(markdown))
  ↓
acquireZenLock(url) → setExpanded(true)
  ↓
ZenModeOverlay renders with html
  ↓
dangerouslySetInnerHTML={{ __html: html }}
```

## What a Digest Overlay Would Need

### Reusable Components

1. **ZenModeOverlay Structure**: The full-screen portal pattern, header layout, content scrolling area (`:66-172`)
2. **Gesture Hooks**: `useOverscrollUp`, `usePullToClose`, `useScrollProgress` (unchanged)
3. **Markdown → HTML Pipeline**: `marked.parse()` + `DOMPurify.sanitize()` (`:39-50` in `useSummary.js`)
4. **Zen Lock Mechanism**: Global mutex pattern (`:11-25` in `useSummary.js`)

### Build Fresh

1. **Multi-Article State**: Digest needs to track multiple articles, not single article summary:
   - `useDigest(date, urls[])` instead of `useSummary(date, url)`
   - Storage key for digest: Different from per-article summary key
   - Digest data structure: `{ status, markdown, articleUrls[], checkedAt, errorMessage }`

2. **API Endpoint**: New endpoint `/api/summarize-digest` accepting `{ urls[], date, effort }`

3. **Header Content**: Digest header shows count ("3 articles") instead of single domain:
   - No favicon (or multi-favicon cluster)
   - Close button → `onClose`
   - Mark-all-removed button → marks all digest articles as removed

4. **Expanded State Management**: Digest overlay can coexist with or replace per-article overlays:
   - Option A: Share zen lock (only digest OR single article open)
   - Option B: Separate digest lock (digest overlay uses different z-index/lock)

5. **Fetch Flow**: Similar to `useSummary.fetchSummary()` but:
   - Request body: `{ urls: string[], date, summarize_effort }`
   - Response: `{ success, summary_markdown, articleUrls }`
   - Store in digest-specific key: `digest-${date}-${hash(urls)}`

6. **Error Handling**: If digest fetch fails, show error in digest overlay (not per-article)

7. **Reducer**: New `digestDataReducer.js` or reuse `summaryDataReducer.js` with `type='digest'`

### Integration Points

**Trigger Digest**:
- User selects multiple articles via `isSelectMode` (InteractionContext)
- Digest button in UI calls `digest.toggle(selectedUrls)`

**Dismiss Digest**:
- Close button → `digest.collapse()`
- Pull-to-close gesture → same as single article
- Overscroll-to-mark → marks all digest articles as removed

**Persistence**:
- Digest markdown stored in Supabase under key `digest-{date}-{urlHash}`
- Reuse `useSupabaseStorage` hook pattern

**Zen Lock**:
- Option A (recommended): Share lock with single-article overlays. Digest acquires `zenLockOwner = 'digest-{urlHash}'`, preventing per-article overlays from opening.
- Option B: Separate lock + higher z-index. Allows digest to open over articles, but increases complexity.
