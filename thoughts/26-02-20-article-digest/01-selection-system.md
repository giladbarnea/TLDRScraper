---
last_updated: 2026-02-20 07:52
---
# Analysis: Client-Side Article Selection System

## Overview
The selection system is built around a central interaction state managed via React Context and a custom reducer. Articles enter selection via long-press gestures and can be batch-selected via container long-presses. The system provides selectedIds as a Set and exposes helper methods for toggling, clearing, and checking selection state.

## Entry Points

1. `/home/user/TLDRScraper/client/src/contexts/InteractionContext.jsx:1-136` - Context provider and public API
2. `/home/user/TLDRScraper/client/src/reducers/interactionReducer.js:1-172` - State reducer with all selection logic
3. `/home/user/TLDRScraper/client/src/components/Selectable.jsx:1-44` - Wrapper component handling long-press and visual selection feedback
4. `/home/user/TLDRScraper/client/src/components/ArticleCard.jsx:232-387` - Individual article component wrapped in Selectable
5. `/home/user/TLDRScraper/client/src/components/SelectionCounterPill.jsx:1-23` - Selection count UI and clear button
6. `/home/user/TLDRScraper/client/src/hooks/useLongPress.js:1-79` - Gesture detection hook

## Core Implementation

### 1. InteractionContext Provider (`/home/user/TLDRScraper/client/src/contexts/InteractionContext.jsx:39-127`)

**State Management:**
- Wraps `interactionReducer` with `useReducer` hook
- Initializes state via `init()` function at lines 33-37, loading expanded containers from localStorage
- State contains: `selectedIds` (Set), `disabledIds` (Set), `expandedContainerIds` (Set), `suppressNextShortPress` object

**Public API exposed via context:**
- `selectedIds`: Set of currently selected item IDs
- `isSelectMode`: Boolean computed from `selectedIds.size > 0` (line 53)
- `isSelected(id)`: Function checking if ID is in selectedIds (line 73)
- `clearSelection()`: Dispatches CLEAR_SELECTION event (lines 65-67)
- `itemLongPress(itemId)`: Dispatches ITEM_LONG_PRESS event (lines 79-81)
- `containerLongPress(containerId, childIds)`: Dispatches CONTAINER_LONG_PRESS event (lines 83-85)
- `itemShortPress(itemId)`: Dispatches ITEM_SHORT_PRESS and returns decision object (lines 91-94)
- `registerDisabled(id, isDisabled)`: Marks items as disabled/enabled (lines 61-63)
- `isExpanded(containerId)`: Checks if container is expanded (lines 75-77)
- `setExpanded(containerId, expanded)`: Sets container expand state (lines 69-71)

**Integration Points:**
- Used by `Selectable`, `ArticleCard`, `FoldableContainer`, `SelectionCounterPill`
- Provider wraps entire app in `/home/user/TLDRScraper/client/src/App.jsx:133` and line 196

### 2. Selection Logic Reducer (`/home/user/TLDRScraper/client/src/reducers/interactionReducer.js`)

**Event Types (lines 1-9):**
- `ITEM_LONG_PRESS`: Toggles individual item selection
- `ITEM_SHORT_PRESS`: Toggles selection in select-mode, otherwise returns decision to open item
- `CONTAINER_LONG_PRESS`: Batch toggles all children (selects all if any unselected, deselects all if all selected)
- `CONTAINER_SHORT_PRESS`: Toggles expand/collapse
- `CLEAR_SELECTION`: Clears all selections
- `REGISTER_DISABLED`: Adds/removes item from disabled set (disabled items auto-deselect)
- `SET_EXPANDED`: Sets container expanded state

**Core Selection Functions:**
- `toggleItemSelection(state, itemId)` (lines 50-56): Adds to selectedIds if absent, removes if present. Respects disabledIds.
- `selectMany(state, itemIds)` (lines 58-64): Adds multiple IDs, skipping disabled ones
- `deselectMany(state, itemIds)` (lines 66-70): Removes multiple IDs from selectedIds
- `toggleContainerChildren(state, childIds)` (lines 72-80): Checks if all selectable children are selected, then deselects all or selects all accordingly

**Suppression Mechanism:**
- `latchSuppress(state, targetId, windowMs)` (lines 28-36): Sets 800ms suppression window after long-press
- `shouldSuppressShortPress(state, targetId)` (lines 38-43): Checks if short-press should be ignored
- Purpose: Prevents accidental short-press right after long-press gesture completes
- Used in ITEM_LONG_PRESS (line 129), CONTAINER_LONG_PRESS (line 136), ITEM_SHORT_PRESS (lines 153-156), CONTAINER_SHORT_PRESS (lines 142-145)

**Decision Object:**
- ITEM_SHORT_PRESS returns `{ shouldOpenItem: true }` when not in select-mode and not suppressed (line 165)
- All other events return `decision: null`
- Consumed by `itemShortPress` in context to determine if article should open (line 93)

### 3. Selectable Component (`/home/user/TLDRScraper/client/src/components/Selectable.jsx`)

**Props:**
- `id`: Unique identifier for the selectable item
- `descendantIds`: Array of child IDs for batch selection (containers only)
- `disabled`: Whether selection is disabled
- `children`: Wrapped content

**Behavior:**
- For items (no descendantIds): Long-press calls `itemLongPress(id)` (line 15)
- For containers (with descendantIds): Long-press calls `containerLongPress(id, descendantIds)` (line 14)
- Uses `useLongPress` hook with 500ms threshold (from `/home/user/TLDRScraper/client/src/lib/interactionConstants.js:1`)
- Pointer events stop propagation to prevent bubbling (line 22)
- Sets `touchAction: 'pan-y'` to allow vertical scrolling while capturing horizontal gestures (line 28)

**Visual Feedback:**
- Selected items get `ring-4 ring-slate-300 rounded-xl` border (line 30)
- Checkmark badge appears at top-left with green background and animation (lines 34-38)
- Checkmark uses `animate-check-enter` animation class

### 4. ArticleCard Integration (`/home/user/TLDRScraper/client/src/components/ArticleCard.jsx`)

**Component ID:**
- Each article gets unique ID: `article-${article.url}` (line 241)
- Registered in Selectable wrapper (line 296)

**Selection Behavior:**
- Short-press handler at lines 272-288
- In select-mode: `itemShortPress` toggles selection (lines 284-287)
- Not in select-mode: `itemShortPress` returns true and summary expands (line 286)
- Removed articles cannot be selected (registered as disabled at lines 290-293)
- Swipe-to-remove is disabled when `isSelectMode` is true (line 255)

**Data Attributes on ArticleCard:**
- `data-article-title={article.title}` (line 320)
- `data-article-url={article.url}` (line 321)
- `data-article-date={article.issueDate}` (line 322)
- `data-article-category={article.category}` (line 323)
- `data-article-source={article.sourceId}` (line 324)
- These attributes are on the motion.div element and could be used to extract article data from DOM

### 5. SelectionCounterPill (`/home/user/TLDRScraper/client/src/components/SelectionCounterPill.jsx`)

**Location:**
- Rendered in header at `/home/user/TLDRScraper/client/src/App.jsx:152`
- Positioned between date display and calendar/settings button

**Behavior:**
- Only renders when `isSelectMode` is true (line 7)
- Displays `selectedIds.size` count (line 17)
- Provides X button that calls `clearSelection()` (lines 11-16)
- Styled as dark pill with white text: `bg-slate-900 text-white px-3 py-1.5 rounded-full`

### 6. Long-Press Detection (`/home/user/TLDRScraper/client/src/hooks/useLongPress.js`)

**Threshold Constants:**
- `LONG_PRESS_THRESHOLD_MS = 500` (from interactionConstants.js:1)
- `POINTER_MOVE_THRESHOLD_PX = 10` (from interactionConstants.js:2)

**Detection Logic:**
- Starts timer on pointerDown (lines 51-54)
- Cancels if pointer moves more than 10px (lines 31-42)
- Fires `onLongPress` callback after 500ms of stationary press (lines 25-28)
- Cancels on pointerUp or pointerCancel (lines 60-67)
- Tracks pointer ID to handle multi-touch correctly (line 7, 20, 32, 45)

**Return Value:**
- Returns `handlers` object with onPointerDown, onPointerMove, onPointerUp, onPointerCancel (lines 69-76)
- Also exposes `didLongPressRef` for checking if long-press actually fired

## Data Flow: How Articles Enter/Exit Selected State

### Entering Selection (Item):
1. User long-presses on ArticleCard
2. `useLongPress` detects 500ms stationary press → calls `handleLongPress` in Selectable (line 13-16)
3. Selectable calls `itemLongPress(componentId)` from context (line 15)
4. Context dispatches `ITEM_LONG_PRESS` event (line 80)
5. Reducer processes at lines 126-131: calls `toggleItemSelection` then `latchSuppress`
6. `toggleItemSelection` adds ID to selectedIds Set (line 54)
7. State update triggers re-render
8. Selectable re-renders with `selected=true` (line 10), shows checkmark and ring border (lines 30, 34-38)

### Entering Selection (Batch via Container):
1. User long-presses on newsletter/section/day header
2. Selectable (with descendantIds) calls `containerLongPress(id, descendantIds)` (line 14)
3. Context dispatches `CONTAINER_LONG_PRESS` event (line 84)
4. Reducer processes at lines 133-138: calls `toggleContainerChildren` then `latchSuppress`
5. `toggleContainerChildren` checks if all children are selected:
   - If all selected: calls `deselectMany` to remove all (line 78)
   - If any unselected: calls `selectMany` to add all (line 79)
6. Each child Selectable re-renders with updated selection state

### Exiting Selection:
1. **Individual toggle**: Same long-press flow, but `toggleItemSelection` removes ID (line 53)
2. **Clear all**: SelectionCounterPill X button calls `clearSelection()` → reducer sets `selectedIds: new Set()` (line 116)
3. **Item becomes disabled**: When article is removed, `registerDisabled` is called → reducer auto-deselects disabled items (lines 106-110)

## Accessing Selected Article Data

### Current Access Methods:

**1. Via selectedIds Set directly:**
```javascript
const { selectedIds } = useInteraction()
// selectedIds is a Set containing IDs like "article-https://example.com/article"
```

**2. Extract article data from DOM using data attributes:**
```javascript
const { selectedIds } = useInteraction()
const selectedArticles = Array.from(selectedIds).map(id => {
  const element = document.querySelector(`[data-article-url]`)
  return {
    url: element.dataset.articleUrl,
    title: element.dataset.articleTitle,
    issueDate: element.dataset.articleDate,
    category: element.dataset.articleCategory,
    sourceId: element.dataset.articleSource
  }
})
```

**3. Pass article data to a new component that filters based on selectedIds:**
- The Feed component hierarchy already has access to all article objects
- A new component could be added that receives all articles and filters by selectedIds
- Example location: In App.jsx, pass `results.payloads` to a DigestButton component
- DigestButton filters articles where `article-${article.url}` is in selectedIds

**4. Enhance InteractionContext to track article objects:**
- Currently only tracks IDs (Set of strings)
- Could add `selectedArticles` Map in reducer state: `Map<id, articleObject>`
- Would require passing article data when calling `itemLongPress`
- This would be a more invasive change to the existing architecture

### Recommended Approach for Digest Feature:

**Option A: Top-level filtering (cleanest)**
- Add DigestButton component in App.jsx header (next to SelectionCounterPill)
- Pass `results.payloads` as prop to DigestButton
- DigestButton uses `selectedIds` from context
- Flattens payloads to articles array and filters where `article-${article.url}` in selectedIds
- Extracts url, title, issueDate, category for each selected article
- Sends to digest API endpoint

**Option B: DOM scraping (works with current architecture, no changes needed)**
- Add DigestButton that reads from DOM using data attributes
- More fragile but requires zero changes to existing selection system
- Could miss articles if they're not in DOM (folded containers, virtualization)

**Option C: Enhanced context (most robust but invasive)**
- Modify reducer to store `Map<id, {url, title, date, category}>`
- Update all call sites of `itemLongPress` to pass article data
- Breaks current clean separation between selection system and article data

## Existing Batch Actions

**None currently implemented.** The selection system exists but has no batch actions except:
- Clear all selections (via SelectionCounterPill X button)
- Visual indication of selection count

The system was built to support batch operations but no actions consume the selection yet. This makes it perfect timing to add the digest feature as the first batch action.

## Component Hierarchy & Selection Points

### Selectable Wrappers (with descendantIds for batch selection):
1. `CalendarDay` (lines 67-68 in CalendarDay.jsx): `calendar-${date}` wrapping all articles for that day
2. `NewsletterDay` (lines 90-91 in NewsletterDay.jsx): `newsletter-${date}-${sourceId}` wrapping all articles in that newsletter
3. `Section` (lines 49-50 in NewsletterDay.jsx): `section-${date}-${sourceId}-${sectionKey}` wrapping all articles in that section

### Individual Selectables:
4. `ArticleCard` (line 241 in ArticleCard.jsx): `article-${url}` for each individual article

### Batch Selection Flow Example:
- Long-press newsletter header → selects all articles in that newsletter across all sections
- Long-press section header → selects all articles in that specific section
- Long-press day header → selects all articles for that entire day
- Long-press individual article → toggles that single article

## SelectionCounterPill Rendering

**Location:** `/home/user/TLDRScraper/client/src/App.jsx:152`

**Context:**
```jsx
<div className="flex items-center gap-3">
  <SelectionCounterPill />
  <button ... Calendar icon for settings ... />
</div>
```

**Conditional Rendering:**
- Only visible when `selectedIds.size > 0`
- Positioned in header, between date display and calendar button
- Fixed position as part of sticky header

**Visual Appearance:**
- Dark pill: `bg-slate-900 text-white`
- Rounded: `rounded-full`
- Padding: `px-3 py-1.5`
- Contains X button (clear) and count display

## Integration Points for Digest Feature

### Where to Add DigestButton:

**Recommended Location:** Next to SelectionCounterPill in header (`/home/user/TLDRScraper/client/src/App.jsx:151-152`)

```jsx
<div className="flex items-center gap-3">
  <SelectionCounterPill />
  <DigestButton payloads={results?.payloads} />  {/* New component */}
  <button ... Calendar icon ... />
</div>
```

**DigestButton Implementation Plan:**
1. Import `useInteraction` to access `selectedIds` and `isSelectMode`
2. Only render when `isSelectMode` is true
3. Accept `payloads` prop to access article data
4. Flatten payloads to articles array: `payloads.flatMap(p => p.articles)`
5. Filter articles where `article-${article.url}` is in selectedIds
6. Extract needed data: `{ url, title, issueDate, category }` for each
7. On click: call new API endpoint `/api/generate-digest` with article list
8. Handle loading/success/error states

**Alternative Location:** As a floating action button (FAB) when in select-mode
- Fixed position at bottom-right
- More prominent for the action
- Follows mobile UI patterns

### Data Extraction Function:

```javascript
function getSelectedArticles(selectedIds, payloads) {
  if (!payloads) return []

  const allArticles = payloads.flatMap(p => p.articles || [])

  return allArticles
    .filter(article => selectedIds.has(`article-${article.url}`))
    .map(article => ({
      url: article.url,
      title: article.title,
      issueDate: article.issueDate,
      category: article.category,
      articleMeta: article.articleMeta,
      section: article.section,
      sourceId: article.sourceId
    }))
}
```

## Key Patterns

**State Management Pattern:**
- Custom reducer with event-driven architecture
- Events clearly named by interaction type (ITEM_LONG_PRESS, CONTAINER_SHORT_PRESS, etc.)
- Single source of truth for all interaction state (selection, expansion, disabled items)

**Gesture Detection Pattern:**
- Custom hook (`useLongPress`) encapsulating pointer event logic
- Threshold-based detection (500ms for long-press, 10px for movement cancellation)
- Properly handles pointer capture and multi-touch

**Selection Toggle Pattern:**
- Individual items: Long-press toggles
- In select-mode: Short-press also toggles
- Containers: Toggle all children at once (smart select all/none based on current state)

**Component Composition Pattern:**
- Selectable is a wrapper component providing selection behavior
- Works for both individual items (articles) and containers (newsletters, sections, days)
- Parent/child relationship tracked via `descendantIds` prop

**Suppression Pattern:**
- Prevents short-press from firing immediately after long-press completes
- Uses time-based latch (800ms window)
- Cleared on first suppressed event (lines 47, 143, 154)

## Configuration

**Long-press threshold:** 500ms (`LONG_PRESS_THRESHOLD_MS` in `/home/user/TLDRScraper/client/src/lib/interactionConstants.js:1`)

**Movement threshold:** 10px (`POINTER_MOVE_THRESHOLD_PX` in interactionConstants.js:2)

**Suppression window:** 800ms (hardcoded in `latchSuppress` at `/home/user/TLDRScraper/client/src/reducers/interactionReducer.js:28`)

**Touch behavior:** `touchAction: 'pan-y'` allows vertical scrolling while capturing horizontal gestures (Selectable.jsx:28)

**Expanded state persistence:** Stored in localStorage as `expandedContainers:v1` (InteractionContext.jsx:10, 15-31)

## Notes for Digest Feature Implementation

### Selection State is Ready:
- `selectedIds` Set is globally accessible via `useInteraction()`
- `isSelectMode` boolean indicates when selection is active
- All article IDs follow pattern: `article-${article.url}`

### No Conflicts Expected:
- Selection system is purely additive (no existing batch actions to conflict with)
- Disabled state is properly managed (removed articles auto-deselect)
- Swipe-to-remove already respects select-mode (disabled when selecting)

### Data Access Strategy:
- Top-level filtering is cleanest: pass `payloads` to DigestButton, filter by selectedIds
- All article data already available in `results.payloads` in App.jsx
- No need to enhance InteractionContext to store article objects

### UI Integration:
- SelectionCounterPill provides pattern to follow (conditional render when `isSelectMode`)
- Header has space for additional button next to SelectionCounterPill
- Could also use FAB pattern for more prominent action button

### Cleanup Considerations:
- After digest generation, probably want to call `clearSelection()`
- Could optionally mark digested articles as read (call `markAsRemoved` for each)
- Error handling should not clear selection (allow retry)
