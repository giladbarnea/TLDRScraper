---
last_updated: 2025-12-21 10:11, 0ac7109
---
# Component & Hooks Refactoring

**Commits:** `04cd038`..`0cf4d39` (2025-12-15 → 2025-12-21)

## Product Level

**Before:** TLDR expand/collapse wrote `tldrHidden` to storage (never read back). Hooks exposed unused functions.
**After:** TLDR visibility is purely local state. Cleaner hook APIs.

User-facing behavior unchanged—internal cleanup only.

## Architecture Changes

**Components refactored:**
- CalendarDay (109→78 LOC): Extracted `formatDateDisplay`, `CalendarDayTitle`, `NewsletterList`
- ScrapeForm (134→166 LOC): Extracted `validateDateRange`, 5 sub-components (`CacheBadge`, `DateInput`, etc.)
- NewsletterDay (86→113 LOC): Extracted `groupArticlesBySection`, `getSortedSectionKeys`, 4 sub-components
- ResultsDisplay (107→122 LOC): Extracted `enrichArticlesWithOrder`, 5 sub-components

**Hooks refactored:**
- useSummary (184→167 LOC): Extracted `markdownToHtml` to file scope; removed unused `toggleVisibility`, `buttonLabel`
- useArticleState (90→53 LOC): Removed 6 dead exports (`state`, `markAsRead`, `markAsUnread`, `toggleRead`, `setRemoved`, `setTldrHidden`)
- useLocalStorage (49→36 LOC): Removed journaling comments

**Dead code removed:** `tldrHidden` feature—written on collapse but never read.

## Patterns Applied

1. Pure functions at file scope (testable in isolation)
2. MECE sub-components (single responsibility)
3. Declarative derived state (no IIFE/inline computation)
4. Remove unused APIs rather than formalize them
