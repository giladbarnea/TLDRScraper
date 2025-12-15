---
last_updated: 2025-12-15 22:07, e986bc9
---
# Component Refactoring Priority Analysis

## Reference Standard: ArticleCard.jsx

Well-decomposed with MECE sub-components (ErrorToast, ZenModeOverlay, ArticleTitle, ArticleMeta, TldrError). Clean separation between UI and business logic.

---

## Priority Rankings

### 1. CalendarDay.jsx - ✅ DONE
- **Core functionality**: 10/10 (Main daily display)
- **Refactoring need**: 9/10
- **Priority Score**: 90

**Refactored:** Extracted `formatDateDisplay`, `CalendarDayTitle`, `NewsletterList` sub-components. Removed 43-line comment block. Reduced from 109 to 78 lines.

---

### 2. ScrapeForm.jsx - CRITICAL
- **Core functionality**: 10/10 (Primary user interaction)
- **Refactoring need**: 8/10
- **Priority Score**: 80

**Problems identified:**
- 50-line async formAction with mixed concerns
- Inline validation logic
- Scattered progress state updates
- UI state, business logic, side effects intertwined

---

### 3. NewsletterDay.jsx - HIGH
- **Core functionality**: 9/10 (Newsletter/section organization)
- **Refactoring need**: 7/10
- **Priority Score**: 63

**Problems identified:**
- Complex section grouping (lines 8-15)
- Section sorting by first article's sectionOrder (lines 17-21)
- Repeated inline title formatting pattern
- Nested ternary for hasSections

---

### 4. ResultsDisplay.jsx - MEDIUM
- **Core functionality**: 7/10 (Alternative display mode)
- **Refactoring need**: 6/10
- **Priority Score**: 42

**Problems identified:**
- Stats display mixed with component
- Inline mapping/filtering in DailyResults
- Repetitive issue rendering (lines 71-95)
- Duplicate storage patterns

---

### 5. ArticleList.jsx - LOW
- **Core functionality**: 8/10 (Shared article renderer)
- **Refactoring need**: 4/10
- **Priority Score**: 32

**Problems identified:**
- Section building logic in component body (lines 13-42)
- Inline ternary in map
- Data transformation during render

---

## No Refactoring Needed

- **CacheToggle.jsx**: Simple, single responsibility
- **Feed.jsx**: Trivial wrapper
- **FoldableContainer.jsx**: Well-designed reusable component
