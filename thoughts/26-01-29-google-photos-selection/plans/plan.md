---
last_updated: 2026-01-29 13:28
---
# Google Photos-Style Selection Implementation Plan

## Overview

Replace the three-dot menu + bottom sheet interaction with Google Photos-style long-press multi-selection. All four component levels (CalendarDay, NewsletterDay, Section, ArticleCard) become selectable. Selecting a parent recursively selects all descendant articles. A selection counter pill appears in the sticky header (right end) when in select mode.

## Current State Analysis

**Existing Components:**
- `Selectable.jsx:5-41` - render-props component providing `menuButton` and `openMenu` to children
- `ThreeDotMenuButton.jsx:3-17` - MoreVertical icon button with stopPropagation
- `BottomSheet.jsx:5-58` - 66vh overlay with pull-to-close, backdrop, escape key dismiss
- `FoldableContainer.jsx` - has `rightContent` prop for menu button placement

**Current Flow:**
1. User clicks three-dot button → BottomSheet opens
2. User clicks "Select" → ID added to `localStorage['podcastSources-1']`
3. BottomSheet closes

**Components Using Selectable:**
- `CalendarDay.jsx:73-88` - ID pattern: `calendar-{date}`
- `NewsletterDay.jsx:99-133` - ID pattern: `newsletter-{date}-{source_id}`
- `NewsletterDay.jsx:52-68` (Section) - ID pattern: `section-{date}-{sourceId}-{sectionKey}`
- `ArticleCard.jsx:299-395` - ID pattern: `article-{url}`

**Gesture Patterns Available:**
- `usePullToClose.js` - touch gesture tracking
- `useSwipeToRemove.js` - horizontal drag detection
- Touch events: `touchstart`, `touchmove`, `touchend`

## Desired End State

1. **Long-press activation**: Long-press (500ms) on any card enters "select mode" and selects that card
2. **Visual indicators for selected cards**:
   - Thick grey border around the card (`ring-4 ring-slate-300`)
   - Brand-color filled checkmark in top-left corner (absolute positioned)
3. **Selection counter pill**: In sticky header (right end), black pill showing "✕ N" format
4. **Select mode behavior**:
   - Single taps select/deselect cards (no long-press needed)
   - Tapping a selected card deselects it
   - Deselecting the last card exits select mode
5. **Recursive selection**: Selecting a parent (CalendarDay/NewsletterDay/Section) selects all its descendant articles
6. **Gesture conflicts resolved**: Swipe-to-remove disabled during select mode; long-press ignored on removed cards

**Verification:**
- Long-press on ArticleCard → enters select mode, card shows selected styling, counter shows "✕ 1"
- Tap another card → counter shows "✕ 2"
- Tap selected card → deselects, counter decrements
- Tap "✕" in counter → clears all, exits select mode
- Long-press on Section → all articles in section become selected
- Swipe gesture on card while in select mode → no effect (swipe disabled)

## What We're NOT Doing

- Not changing the localStorage key or data format (`podcastSources-1` stays as JSON array)
- Not adding batch actions beyond select/deselect (no "delete selected", "share selected", etc.)
- Not adding select-all button (only recursive parent selection)
- Not modifying ZenModeOverlay behavior (it's full-screen, no selection needed there)

## Implementation Approach

1. Create a React context for selection state that all components can access
2. Create a reusable `useLongPress` hook for gesture detection
3. Transform `Selectable` from render-props-for-menu to a wrapper that handles long-press and visual states
4. Parents pass their descendant IDs to Selectable for recursive selection
5. Integrate counter pill into App header
6. Clean up removed components

---

## Phase 1: Selection State Infrastructure

### Overview
Create the foundational state management and hooks needed for the new selection system.

### Changes Required:

#### 1. SelectionContext Provider
**File**: `client/src/contexts/SelectionContext.jsx` (new file)
**Changes**: Create context with selection state and actions

```jsx
// State shape:
// - selectedIds: Set<string>
// - isSelectMode: boolean (derived: selectedIds.size > 0)

// Actions:
// - toggle(id) - add if not present, remove if present
// - selectMany(ids[]) - add multiple IDs (for recursive selection)
// - clear() - clear all, exit select mode

// localStorage sync on selectedIds change
```

#### 2. useLongPress Hook
**File**: `client/src/hooks/useLongPress.js` (new file)
**Changes**: Create hook for long-press detection on touch and mouse

```jsx
// Parameters: onLongPress callback, options { threshold: 500, disabled: false }
// Returns: { onTouchStart, onTouchEnd, onTouchMove, onMouseDown, onMouseUp, onMouseLeave }
// Behavior:
// - Start timer on touchstart/mousedown
// - Clear timer on touchend/mouseup/mouseleave
// - Clear timer on touchmove if moved > 10px (prevents scroll triggering long-press)
// - Fire callback after threshold
```

#### 3. SelectionCounterPill Component
**File**: `client/src/components/SelectionCounterPill.jsx` (new file)
**Changes**: Create the "✕ N" pill for the header

```jsx
// Consumes SelectionContext
// Renders: black pill with X icon + count
// X button calls clear()
// Only renders when isSelectMode is true
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd client && npm run lint` passes
- [ ] `cd client && npm run build` succeeds

#### Manual Verification:
- [ ] Context can be imported and provides expected shape
- [ ] useLongPress fires callback after holding 500ms
- [ ] SelectionCounterPill renders count correctly when given selected IDs

---

## Phase 2: Transform Selectable Component

### Overview
Rework Selectable from render-props-for-menu to long-press-selection-wrapper with visual states.

### Changes Required:

#### 1. Rework Selectable.jsx
**File**: `client/src/components/Selectable.jsx`
**Changes**: Complete rewrite

```jsx
// New props: id, title (keep), descendantIds (new, optional array)
// No more render props - just wraps children directly

// Behavior:
// - useLongPress to detect long-press → toggle selection (self + descendantIds if present)
// - In select mode: onClick → toggle selection
// - Not in select mode: onClick → pass through (let child handle)

// Visual rendering:
// - Wrap children in relative container
// - When selected: add ring-4 ring-slate-300 border
// - When selected: render absolute-positioned checkmark (top-left, brand-500 bg, white check icon)

// Skip long-press if disabled prop is true (for removed cards)
```

#### 2. CSS for Selection Visuals
**File**: `client/src/index.css`
**Changes**: Add selection-related styles (checkmark animation)

```css
// @keyframes check-enter - scale-up spring animation for checkmark
// @utility animate-check-enter
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd client && npm run lint` passes
- [ ] `cd client && npm run build` succeeds

#### Manual Verification:
- [ ] Long-press on wrapped component triggers selection
- [ ] Selected component shows grey border and checkmark
- [ ] Tap in select mode toggles selection
- [ ] Tap outside select mode passes through to child onClick

---

## Phase 3: Integrate & Clean Up

### Overview
Wire up all components, handle gesture conflicts, add counter to header, remove old components.

### Changes Required:

#### 1. Wrap App with SelectionProvider
**File**: `client/src/App.jsx`
**Changes**: Wrap app content with SelectionProvider, add SelectionCounterPill to header

```jsx
// Import SelectionProvider, SelectionCounterPill
// Wrap return content with <SelectionProvider>
// Add <SelectionCounterPill /> in header area (right end)
```

#### 2. Update CalendarDay
**File**: `client/src/components/CalendarDay.jsx`
**Changes**: Compute descendantIds from newsletters data, pass to Selectable

```jsx
// descendantIds = all article URLs from all newsletters in this calendar day
// Flatten: newsletters → sections → articles → article.url → `article-${url}`
// Selectable no longer uses render props, just wraps FoldableContainer
// Remove rightContent prop from FoldableContainer (no more menu button)
```

#### 3. Update NewsletterDay
**File**: `client/src/components/NewsletterDay.jsx`
**Changes**: Compute descendantIds for NewsletterDay and Section, pass to Selectable

```jsx
// NewsletterDay descendantIds = all article URLs from all sections
// Section descendantIds = all article URLs in that section
// Remove rightContent from FoldableContainer
```

#### 4. Update ArticleCard
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Disable swipe in select mode, pass disabled to Selectable for removed cards

```jsx
// Import useSelection context
// canDrag = !isRemoved && !stateLoading && !isSelectMode
// Selectable disabled={isRemoved} (no long-press on removed)
// Selectable has no descendantIds (articles are leaf nodes)
// Remove menuButton from render, remove openMenu from ZenModeOverlay
```

#### 5. Update FoldableContainer
**File**: `client/src/components/FoldableContainer.jsx`
**Changes**: Remove rightContent prop (no longer needed)

```jsx
// Remove rightContent prop and its rendering
// Simplify header layout
```

#### 6. Delete Obsolete Files
**Files to delete**:
- `client/src/components/ThreeDotMenuButton.jsx`
- `client/src/components/BottomSheet.jsx`

#### 7. Clean Up CSS
**File**: `client/src/index.css`
**Changes**: Remove sheet-related animations

```css
// Remove: @keyframes sheet-enter
// Remove: @keyframes sheet-backdrop-enter
// Remove: @utility animate-sheet-enter
// Remove: @utility animate-sheet-backdrop
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd client && npm run lint` passes
- [ ] `cd client && npm run build` succeeds
- [ ] No import errors (deleted files not referenced)

#### Manual Verification:
- [ ] Long-press on ArticleCard enters select mode, shows styling, counter appears in header
- [ ] Long-press on Section selects all articles in section
- [ ] Long-press on NewsletterDay selects all articles in newsletter
- [ ] Long-press on CalendarDay selects all articles in that day
- [ ] Tap in select mode toggles individual cards
- [ ] Tap "✕" clears selection and exits select mode
- [ ] Swipe-to-remove does NOT work while in select mode
- [ ] Long-press does NOT work on removed cards
- [ ] Normal tap on card (not in select mode) still opens TLDR
- [ ] FoldableContainer fold/unfold still works

---

## Testing Strategy

### Unit Tests:
- None required (UI-only feature, no complex logic)

### Integration Tests:
- None required

### Manual Testing Steps:
1. Load app with newsletter data
2. Long-press an ArticleCard → verify enters select mode, card selected, counter shows "✕ 1"
3. Tap another ArticleCard → verify selected, counter shows "✕ 2"
4. Tap a selected card → verify deselected, counter shows "✕ 1"
5. Tap "✕" in counter → verify all cleared, counter disappears
6. Long-press a Section header → verify all articles in section selected
7. Long-press a NewsletterDay header → verify all articles in newsletter selected
8. Long-press a CalendarDay header → verify all articles in that day selected
9. While in select mode, try to swipe an ArticleCard → verify swipe is disabled
10. Mark an article as removed, try to long-press it → verify no selection
11. While not in select mode, tap a card → verify TLDR opens normally
12. Tap fold/unfold on any FoldableContainer → verify still works

## References

- Previous three-dot menu plan: `thoughts/26-01-27-add-three-dot-menu/plans/three-dot-menu-bottom-sheet.md`
- Existing gesture hooks: `client/src/hooks/usePullToClose.js`, `client/src/hooks/useSwipeToRemove.js`
