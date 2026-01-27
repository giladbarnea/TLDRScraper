---
date: 2026-01-27T08:37:43+00:00
researcher: Codex
git_commit: d9e2ff234271b5eefc572ef62e6a9f831905ff96
branch: work
repository: TLDRScraper
topic: "Three-dots menu for calendar day and newsletter headers"
tags: [research, client, calendar-day, newsletter-day]
status: complete
last_updated: 26-01-27
last_updated_by: Codex
---

# Research: Three-dots menu for calendar day and newsletter headers

**Date**: 2026-01-27T08:37:43+00:00
**Researcher**: Codex
**Git Commit**: d9e2ff234271b5eefc572ef62e6a9f831905ff96
**Branch**: work
**Repository**: TLDRScraper

## Research Question
Where should a Notion-style three-dots menu be added for calendar-day and newsletter headers, and what layout constraints exist?

## Summary
Calendar days and newsletter sections are rendered via `CalendarDay` and `NewsletterDay`, each passing a title block into `FoldableContainer`. `FoldableContainer` owns the header layout and currently keeps the title content in a non-growing container, with a chevron on the right. Adding a right-aligned menu requires updating header layout and the title blocks in both components to include a new menu trigger. `FoldableContainer` is the shared layout container for both headers, so any change to title alignment affects all collapsible headers. 

## Detailed Findings

### CalendarDay header
- Calendar day titles are rendered by `CalendarDayTitle`, which currently shows the date, read stats, and syncing indicator in a single row. `CalendarDay` passes this title into `FoldableContainer`, which controls the header layout and click behavior for collapse/expand. (`client/src/components/CalendarDay.jsx:15-81`)

### NewsletterDay header
- Newsletter headers are rendered inside `NewsletterDay` with a title row and read stats badge, also passed into `FoldableContainer` as the header content. (`client/src/components/NewsletterDay.jsx:78-119`)

### FoldableContainer layout
- `FoldableContainer` wraps the title in a non-growing container and keeps the chevron on the right. Any right-aligned UI inside the header needs the title block to expand and allow `ml-auto` alignment to place controls on the right. (`client/src/components/FoldableContainer.jsx:16-35`)

## Code References
- `client/src/components/CalendarDay.jsx:15-81` - Calendar day title and usage in a foldable header.
- `client/src/components/NewsletterDay.jsx:78-119` - Newsletter header structure within a foldable container.
- `client/src/components/FoldableContainer.jsx:16-35` - Shared header layout and chevron control.

## Architecture Documentation
Calendar days and newsletter headers both render inside `FoldableContainer`, which owns the header click handler for fold/unfold behavior. Any menu trigger added to header content must stop propagation to avoid toggling the container. The layout must accommodate right-aligned controls before the chevron.

## Related Research
- None.

## Open Questions
- None.
