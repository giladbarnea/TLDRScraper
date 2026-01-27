# Three-Dots Menu Sheet Implementation Plan

## Overview
Add a Notion-style three-dots menu to calendar-day and newsletter headers that opens a bottom sheet with the item title and a Select action.

## Current State Analysis
Calendar day and newsletter headers render their title blocks into `FoldableContainer`, which owns the header layout and collapse behavior. There is no per-header menu control today. `FoldableContainer` constrains title content to a non-growing container, so right-aligned controls are not possible without layout adjustments.

## Desired End State
Calendar day and newsletter headers show a three-dots button aligned to the right. Clicking it opens a bottom sheet that covers roughly two-thirds of the viewport height, shows the title, and provides a pill-shaped Select action with a no-op callback. The menu button does not toggle fold/unfold.

### Key Discoveries:
- `CalendarDayTitle` and `NewsletterDay` pass their title blocks into `FoldableContainer`. (`client/src/components/CalendarDay.jsx:15-81`, `client/src/components/NewsletterDay.jsx:78-119`)
- `FoldableContainer` owns the header click handler and title container layout. (`client/src/components/FoldableContainer.jsx:16-35`)

## What We're NOT Doing
- No wiring of Select action to backend or state changes.
- No new persistence or analytics.
- No changes to article or section layouts.

## Implementation Approach
Introduce a reusable menu sheet component and insert it into calendar-day and newsletter header rows, while adjusting the header layout to allow right-aligned controls and preventing menu clicks from toggling fold state.

## Phase 1: Add menu sheet and integrate in headers

### Overview
Create the reusable menu sheet component, update `FoldableContainer` layout to allow right-aligned controls, and add menu triggers to calendar-day and newsletter headers.

### Changes Required:

#### 1. Menu Sheet Component
**File**: `client/src/components/ActionMenuSheet.jsx`
**Changes**: Add a reusable three-dots trigger and bottom sheet with title and Select action.

```javascript
- Add ActionMenuSheet component with internal open state
- Render MoreHorizontal icon button as trigger
- Render fixed overlay + bottom sheet with title + Select button
- Stop propagation on trigger and sheet content
```

#### 2. Foldable header layout
**File**: `client/src/components/FoldableContainer.jsx`
**Changes**: Allow title content to stretch, enabling right-aligned menu controls.

```javascript
- Update title wrapper to flex-grow and allow min-width
```

#### 3. Calendar day header integration
**File**: `client/src/components/CalendarDay.jsx`
**Changes**: Add the menu trigger to the right side of the calendar day header.

```javascript
- Import ActionMenuSheet
- Update CalendarDayTitle layout to include right-aligned menu trigger
```

#### 4. Newsletter header integration
**File**: `client/src/components/NewsletterDay.jsx`
**Changes**: Add the menu trigger to the right side of the newsletter header.

```javascript
- Import ActionMenuSheet
- Update header layout to include right-aligned menu trigger
```

### Success Criteria:

#### Automated Verification:
- [x] None specified.

#### Manual Verification
- [ ] Calendar day headers show a three-dots menu button aligned to the right.
- [ ] Newsletter headers show a three-dots menu button aligned to the right.
- [ ] Clicking the three-dots button opens a bottom sheet covering about two-thirds of the screen.
- [ ] The sheet shows the correct title and a Select pill button.
- [ ] Clicking the three-dots button does not fold/unfold the section.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None planned.

### Integration Tests:
- None planned.

### Manual Testing Steps:
1. Load the feed view and find a calendar day header.
2. Click the three-dots button and confirm the sheet appears with the title and Select pill.
3. Close the sheet and repeat on a newsletter header.
4. Confirm the fold/unfold chevron still works when clicking the header background.

## References
- Related research: `thoughts/26-01-27-ENG-0000/research/three-dots-menu.md`
- Similar implementation: `client/src/components/FoldableContainer.jsx:16-35`
