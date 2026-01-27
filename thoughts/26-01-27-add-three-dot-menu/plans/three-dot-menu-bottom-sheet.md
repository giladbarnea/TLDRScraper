---
last_updated: 2026-01-27 21:47, b3b7570
---
# Three-Dot Menu with Bottom Sheet Implementation Plan

## Overview

Add Notion-style three-dot menu (kebab menu) to CalendarDay and NewsletterDay components. Clicking the menu opens a bottom sheet pane that slides up from the bottom, taking 2/3 of vertical space. The sheet displays the component's title and a single "Select" pill button with a no-op callback.

## Implementation Status: ✅ COMPLETE

**All phases completed successfully:**
- ✅ Phase 1: BottomSheet component with animations, pull-to-close, backdrop, and escape key support
- ✅ Phase 2: ThreeDotMenuButton component with stopPropagation
- ✅ Phase 3: CalendarDay integration
- ✅ Phase 4: NewsletterDay integration

**Additional enhancements beyond original plan:**
- **Layout fix**: Modified `FoldableContainer` to support `rightContent` prop, positioning the chevron icon next to the title and the three-dot menu on the far right (commit `4df48f2`)
- **localStorage persistence**: "Select" button now saves component IDs to `localStorage` under key `'podcastSources-1'` with format `calendar-{date}` and `newsletter-{date}-{title}` (commit `51480fc`). This enables tracking which content sources the user has selected for podcast generation (see Next Steps)

## Current State Analysis

### Existing Patterns
- **Portal-based overlays**: `ZenModeOverlay` in `ArticleCard.jsx:64-169` uses `createPortal` for full-screen overlay
- **Pull-to-close gesture**: `usePullToClose` hook (`hooks/usePullToClose.js:1-61`) tracks pull-down gesture
- **Entry animations**: `@keyframes zen-enter` in `index.css:50-63` with springy easing
- **Icon library**: lucide-react used throughout (ChevronRight, ChevronDown, etc.)
- **Button styling**: Circular icon buttons pattern in `App.jsx:79-85`

### Key Discoveries
- CalendarDayTitle renders inside `FoldableContainer` header (`CalendarDay.jsx:14-25`)
- NewsletterDay title is inline JSX passed to `FoldableContainer` (`NewsletterDay.jsx:88-95`)
- Both use `flex items-center gap-3` layout
- FoldableContainer header has `onClick` for fold/unfold - menu needs `e.stopPropagation()`
- Body scroll lock pattern: `document.body.style.overflow = 'hidden'` in ZenModeOverlay

## Desired End State

1. Three-dot (MoreVertical) icon button on the right side of CalendarDay and NewsletterDay headers
2. Clicking icon opens bottom sheet covering 2/3 of screen height
3. Bottom sheet shows:
   - Semi-transparent backdrop
   - Component title in header
   - "Select" pill button
4. Sheet dismissible via: backdrop click, pull-down gesture, Escape key
5. Click callback on "Select" is no-op for now

## What We're NOT Doing

- Not adding menu items beyond "Select"
- Not implementing selection logic
- Not modifying FoldableContainer component itself
- Not adding menus to Section headers (only CalendarDay and NewsletterDay)

## Implementation Approach

Create a reusable `BottomSheet` component and a `ThreeDotMenuButton` component. Integrate into existing title elements with minimal changes to CalendarDay and NewsletterDay.

---

## Phase 1: Create BottomSheet Component and CSS Animation

### Overview
Create the reusable bottom sheet overlay component with proper animations and dismiss behaviors.

### Changes Required:

#### 1. CSS Animation for Bottom Sheet
**File**: `client/src/index.css`
**Changes**: Add keyframes for sheet slide-up animation

```css
// Add after zen-enter keyframes:
@keyframes sheet-enter
@keyframes sheet-backdrop-enter
@utility animate-sheet-enter
@utility animate-sheet-backdrop
```

#### 2. BottomSheet Component
**File**: `client/src/components/BottomSheet.jsx` (new file)
**Changes**: Create portal-based bottom sheet component

```jsx
// Props: isOpen, onClose, title, children
// Features:
//   - createPortal to document.body
//   - Backdrop with click-to-close
//   - usePullToClose for swipe dismiss
//   - Escape key handler
//   - Body scroll lock
//   - 2/3 vertical height (h-[66vh])
```

### Success Criteria:

#### Automated Verification:
- [x] `npm run lint` passes in client directory
- [x] `npm run build` succeeds

#### Manual Verification:
- [x] Component can be imported without errors
- [x] Sheet renders at correct height (2/3 of viewport)

---

## Phase 2: Create ThreeDotMenuButton Component

### Overview
Create the trigger button component that opens the bottom sheet.

### Changes Required:

#### 1. ThreeDotMenuButton Component
**File**: `client/src/components/ThreeDotMenuButton.jsx` (new file)
**Changes**: Create menu trigger button with MoreVertical icon

```jsx
// Props: onClick
// Features:
//   - MoreVertical icon from lucide-react
//   - stopPropagation on click
//   - Hover/active states matching existing button patterns
//   - Accessible button element
```

### Success Criteria:

#### Automated Verification:
- [x] `npm run lint` passes
- [x] `npm run build` succeeds

#### Manual Verification:
- [x] Button renders with correct icon
- [x] Click does not trigger parent click handlers

---

## Phase 3: Integrate into CalendarDay Component

### Overview
Add three-dot menu to CalendarDayTitle with bottom sheet.

### Changes Required:

#### 1. CalendarDay Integration
**File**: `client/src/components/CalendarDay.jsx`
**Changes**:
- Add state for menu open/close
- Import ThreeDotMenuButton and BottomSheet
- Add button to CalendarDayTitle flex container
- Render BottomSheet with "Select" button

```jsx
// In CalendarDayTitle:
// - Add menuOpen state
// - Add ThreeDotMenuButton after loading indicator
// - Render BottomSheet when menuOpen=true

// Props needed: title (displayText), onSelect callback
```

### Success Criteria:

#### Automated Verification:
- [x] `npm run lint` passes
- [x] `npm run build` succeeds

#### Manual Verification:
- [x] Three-dot button visible on right side of calendar day header
- [x] Clicking button opens bottom sheet
- [x] Sheet shows correct date/title
- [x] Sheet has "Select" pill button
- [x] Sheet dismisses on backdrop click
- [x] Sheet dismisses on Escape key
- [x] Sheet dismisses on pull-down gesture

---

## Phase 4: Integrate into NewsletterDay Component

### Overview
Add three-dot menu to NewsletterDay title with bottom sheet.

### Changes Required:

#### 1. NewsletterDay Integration
**File**: `client/src/components/NewsletterDay.jsx`
**Changes**:
- Add state for menu open/close
- Import ThreeDotMenuButton and BottomSheet
- Add button to inline title JSX
- Render BottomSheet with "Select" button

```jsx
// In NewsletterDay title prop:
// - Move inline JSX to separate component or add state to NewsletterDay
// - Add ThreeDotMenuButton after ReadStatsBadge
// - Render BottomSheet when menuOpen=true
```

### Success Criteria:

#### Automated Verification:
- [x] `npm run lint` passes
- [x] `npm run build` succeeds

#### Manual Verification:
- [x] Three-dot button visible on right side of newsletter header
- [x] Clicking button opens bottom sheet
- [x] Sheet shows correct newsletter name
- [x] Sheet has "Select" pill button
- [x] All dismiss methods work correctly
- [x] Menu click doesn't trigger fold/unfold

---

## Testing Strategy

### Unit Tests:
- None required for this UI-only feature

### Integration Tests:
- None required for this UI-only feature

### Manual Testing Steps:
1. Open the app with newsletter data loaded
2. Verify three-dot icon appears on calendar day headers
3. Verify three-dot icon appears on newsletter headers
4. Click calendar day menu → sheet opens with date title
5. Click newsletter menu → sheet opens with newsletter name
6. Test dismiss via backdrop click
7. Test dismiss via Escape key
8. Test dismiss via pull-down gesture (mobile)
9. Verify "Select" button is visible and clickable (no action expected)
10. Verify clicking menu does not expand/collapse the FoldableContainer

## Next Steps

This feature lays the groundwork for **AI-generated voice podcast creation**. The intended workflow:

1. User selects multiple content sources (calendar days, newsletters) via the "Select" button in the bottom sheet
2. Selected sources are tracked in `localStorage['podcastSources-1']` as component IDs
3. User triggers podcast generation (future button/action)
4. Server aggregates content from selected sources
5. AI generates a conversational podcast episode about the aggregated content
6. User receives audio file for playback

**Current implementation status**: Selection persistence complete (Phase 1 of podcast feature)

**Remaining work**:
- UI for viewing/managing selected sources
- Podcast generation trigger button
- Server endpoint for content aggregation
- AI podcast generation integration
- Audio playback interface

## References

- Existing overlay pattern: `client/src/components/ArticleCard.jsx:28-171`
- Pull-to-close hook: `client/src/hooks/usePullToClose.js`
- CSS animations: `client/src/index.css:50-63`
- Icon buttons: `client/src/App.jsx:79-85`
