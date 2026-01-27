---
date: 2026-01-27T16:53:00+00:00
researcher: Codex
git_commit: 1840144110fd80bba16062e820352fad43cbd555
branch: work
repository: TLDRScraper
topic: "Notion-style menu for calendar day and newsletter headers"
tags: [research, client, calendar-day, newsletter-day, foldable-container]
status: complete
last_updated: 26-01-27
last_updated_by: Codex
---

# Research: Notion-style menu for calendar day and newsletter headers

**Date**: 2026-01-27T16:53:00+00:00
**Researcher**: Codex
**Git Commit**: 1840144110fd80bba16062e820352fad43cbd555
**Branch**: work
**Repository**: TLDRScraper

## Research Question
Where should a Notion-style three-dot menu be added for calendar day and newsletter header components, and how are those headers currently built?

## Summary
Calendar day and newsletter headers are both rendered inside a shared `FoldableContainer` component. `CalendarDay` provides a `CalendarDayTitle` element, and `NewsletterDay` provides a title block with the newsletter name and stats badge. Both are part of the clickable header row that toggles fold state, so any new menu trigger should stop event propagation to avoid triggering the fold toggle.

## Detailed Findings

### Foldable header layout
- `FoldableContainer` renders a header row with a title element and a right-aligned chevron that toggles folding on click. The click handler is attached to the header row container, so any new interactive elements inside the title must stop propagation. `FoldableContainer` controls the layout with flex classes and places the title before the chevron, which is important for placing a right-side menu button near the chevron. (`client/src/components/FoldableContainer.jsx`)

### Calendar day header
- `CalendarDay` passes `CalendarDayTitle` as the header title for its `FoldableContainer`. The title includes the formatted date string, a read stats badge, and an optional syncing label. This is the correct location to add the three-dot menu for each calendar day. (`client/src/components/CalendarDay.jsx`)

### Newsletter header
- `NewsletterDay` passes a title element that includes the newsletter name and read stats badge into its `FoldableContainer`. This is the correct place to add the three-dot menu for each newsletter. (`client/src/components/NewsletterDay.jsx`)

## Code References
- `client/src/components/FoldableContainer.jsx` - Header container, click-to-toggle fold behavior, and chevron layout.
- `client/src/components/CalendarDay.jsx` - `CalendarDayTitle` renders the header contents for calendar day entries.
- `client/src/components/NewsletterDay.jsx` - Newsletter header title block rendered inside `FoldableContainer`.

## Architecture Documentation
The client architecture documents that `CalendarDay` and `NewsletterDay` are primary containers in the feed hierarchy, and both are rendered as `FoldableContainer` instances in the feed flow. This aligns with adding a new menu control to each header instead of introducing a new layer in the hierarchy. (`client/CLIENT_ARCHITECTURE.md`)

## Related Research
- None.

## Open Questions
- None.
