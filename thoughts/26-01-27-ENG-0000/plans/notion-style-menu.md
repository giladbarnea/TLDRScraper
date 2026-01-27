# Notion-Style Menu for Calendar and Newsletter Headers Implementation Plan

## Overview
Add a three-dot menu control to calendar day and newsletter headers that opens a bottom sheet menu, mirroring the Notion interaction pattern for selection actions.

## Current State Analysis
Calendar day and newsletter headers are rendered as `title` props passed into `FoldableContainer`. The header row is clickable to toggle fold state, so any new menu interactions must stop event propagation to avoid folding. The title blocks currently contain text and read stats badges only. `FoldableContainer` lays out the title and a chevron icon in a flex row. (`client/src/components/CalendarDay.jsx:14-75`, `client/src/components/NewsletterDay.jsx:77-114`, `client/src/components/FoldableContainer.jsx:5-36`)

## Desired End State
Each calendar day and newsletter header displays a three-dot menu icon aligned to the right. Clicking it opens a bottom sheet covering roughly two-thirds of the viewport height, showing the header title and a pill-shaped "Select" button. Selecting is a no-op and does not change state. Clicking outside closes the sheet. The fold toggle should not trigger when interacting with the menu.

### Key Discoveries
- Header click-to-fold behavior lives in `FoldableContainer`, so menu interactions must stop propagation. (`client/src/components/FoldableContainer.jsx:22-34`)
- Calendar day and newsletter headers are defined in `CalendarDayTitle` and the `NewsletterDay` title block. (`client/src/components/CalendarDay.jsx:14-24`, `client/src/components/NewsletterDay.jsx:84-95`)

## What We're NOT Doing
- Implementing any selection logic or backend state updates.
- Adding keyboard shortcuts or persistent menu state.

## Implementation Approach
Introduce a reusable client component responsible for rendering the three-dot trigger and bottom sheet. Update calendar and newsletter title blocks to include the new menu control and adjust header layout so right-side alignment is possible.

## Phase 1: Add Menu Component and Wire into Headers

### Overview
Create a reusable action menu component and attach it to the calendar day and newsletter header blocks while ensuring fold toggling is not triggered.

### Changes Required

#### 1. Shared menu component
**File**: `client/src/components/ActionMenu.jsx`
**Changes**: Add a component that renders a three-dot trigger button and a fixed-position bottom sheet with title and "Select" pill button. The component should manage its open state and stop event propagation in header context.

```jsx
- ActionMenu component with isMenuOpen state
- Trigger button using a three-dot icon
- Fixed overlay and bottom sheet with title + "Select" button
```

#### 2. Header layout adjustments
**File**: `client/src/components/FoldableContainer.jsx`
**Changes**: Allow the header title container to expand so right-aligned menu content can be positioned before the chevron.

```jsx
- Update title wrapper to use flex growth and min-width handling
```

#### 3. Calendar day header menu
**File**: `client/src/components/CalendarDay.jsx`
**Changes**: Import the menu component and render it within `CalendarDayTitle`, aligned to the right, passing the formatted date text as the menu title.

```jsx
- Render ActionMenu with calendar day display text
- Ensure layout uses flex + ml-auto for right alignment
```

#### 4. Newsletter header menu
**File**: `client/src/components/NewsletterDay.jsx`
**Changes**: Import the menu component and render it within the newsletter title block, aligned to the right, passing the newsletter title as the menu title.

```jsx
- Render ActionMenu with newsletter title
- Ensure layout uses flex + ml-auto for right alignment
```

### Success Criteria

#### Automated Verification
- [ ] No automated tests required.

#### Manual Verification
- [ ] Each calendar day header shows a three-dot menu on the right.
- [ ] Each newsletter header shows a three-dot menu on the right.
- [ ] Clicking the menu opens a bottom sheet covering roughly two-thirds of the viewport height.
- [ ] The bottom sheet displays the header title and a "Select" pill button.
- [ ] Clicking outside the sheet closes it, and interacting with the menu does not fold/unfold the container.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests
- Not planned for this UI-only change.

### Integration Tests
- Not planned; verify visually in the client.

### Manual Testing Steps
1. Open the feed and locate a calendar day header.
2. Click the three-dot menu and confirm the bottom sheet appears with the date title and "Select" button.
3. Click outside the sheet to close it without folding the calendar day.
4. Repeat the same interaction for a newsletter header.

## References
- Related research: `thoughts/26-01-27-ENG-0000/research/notion-style-menu.md`
- `client/src/components/CalendarDay.jsx:14-75`
- `client/src/components/NewsletterDay.jsx:77-114`
- `client/src/components/FoldableContainer.jsx:5-36`
