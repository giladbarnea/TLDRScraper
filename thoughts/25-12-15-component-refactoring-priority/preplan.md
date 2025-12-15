---
last_updated: 2025-12-15 18:32
---
# Component Refactoring Priority Analysis

## Reference: ArticleCard.jsx (The Standard)

ArticleCard demonstrates good MECE decomposition:
- **Sub-components**: ErrorToast, ZenModeOverlay, ArticleTitle, ArticleMeta, TldrError
- **Each has single responsibility**: Presentation-focused, minimal logic
- **Main component**: Orchestrates hooks and delegates to sub-components
- **Clean separation**: UI components vs business logic hooks

---

## Prioritized Refactoring List

### 1. **CalendarDay.jsx** (CRITICAL - Core + Dire Need)

**Core functionality score**: 10/10 (Main display component for daily data)
**Refactoring need score**: 9/10

**Problems**:
- **Giant comment block** (lines 44-87): Code explaining code = code smell. Logic should be self-documenting
- **Inline date formatting**: `toLocaleDateString` with options embedded in component
- **Inline article filtering**: `articles.filter(a => a.category === newsletterName)` inside map
- **Inline issue mapping**: Complex newsletter grouping logic in JSX
- **Mixed concerns**: Date presentation, data filtering, and rendering all in one place

**Refactoring targets**:
```javascript
// Extract to utility functions:
- formatCalendarDate(date) => returns { niceDate, isToday }
- groupArticlesByNewsletter(articles, issues) => returns filtered articles per issue

// Extract to sub-components:
- CalendarDayHeader({ date, isToday, loading })
- NewsletterSection (already exists as NewsletterDay, but integration could be cleaner)
```

**Impact**: High - This is the main container for daily article display

---

### 2. **ScrapeForm.jsx** (CRITICAL - Core + Dire Need)

**Core functionality score**: 10/10 (Primary user interaction for data fetching)
**Refactoring need score**: 8/10

**Problems**:
- **Complex form action**: 50-line async function with validation, error handling, progress tracking all mixed together
- **Inline validation**: Date comparison and range checking embedded in formAction
- **Progress state management**: setProgress calls scattered throughout try/catch
- **No separation of concerns**: UI state, business logic, and side effects all intertwined

**Refactoring targets**:
```javascript
// Extract to utility functions:
- validateDateRange(start, end) => returns { valid, error }
- calculateProgress(step, total) => progress percentage logic

// Extract to sub-components:
- DateRangeInputs({ startDate, endDate, onStartChange, onEndChange })
- ProgressBar({ progress, isPending })
- FormError({ error })
- SyncButton({ isPending, progress })

// Extract to custom hook:
- useScrapeForm({ onResults }) => returns { state, handleSubmit, progress, ... }
```

**Impact**: High - This is the primary user entry point

---

### 3. **NewsletterDay.jsx** (HIGH - Core + Moderate Need)

**Core functionality score**: 9/10 (Organizes articles by newsletter and sections)
**Refactoring need score**: 7/10

**Problems**:
- **Complex section grouping** (lines 8-15): Reduce logic embedded in component body
- **Complex section sorting** (lines 17-21): Sorting by sectionOrder extracted from first article
- **Inline title formatting**: `sectionEmoji ? ${sectionEmoji} ${sectionKey}` repeated pattern
- **Nested ternary**: hasSections ? sortedSections.map() : ArticleList

**Refactoring targets**:
```javascript
// Extract to utility functions:
- groupArticlesBySections(articles) => returns { sections, sortedSectionKeys }
- formatSectionTitle(sectionKey, sectionEmoji) => returns display title

// Extract to sub-components:
- NewsletterHeader({ title, subtitle, allRemoved })
- SectionContainer({ sectionKey, articles, date, title })
  - This would replace the inline FoldableContainer + ArticleList pattern
```

**Impact**: High - Core display component for newsletter organization

---

### 4. **ResultsDisplay.jsx** (MEDIUM - Important + Some Need)

**Core functionality score**: 7/10 (Alternative display mode, less used than CalendarDay)
**Refactoring need score**: 6/10

**Problems**:
- **Stats display**: Could be extracted (lines 10-37)
- **DailyResults sub-component**: Good pattern but has inline mapping/filtering
- **Repetitive issue rendering**: issue.map with embedded ArticleList (lines 71-95)
- **Duplicate storage logic**: Same useSupabaseStorage pattern as CalendarDay

**Refactoring targets**:
```javascript
// Extract to sub-components:
- StatsDisplay({ stats }) - The grid of article/URL/date counts
- IssueSection({ date, issue, articles }) - Replace inline issue.map logic
- IssueTitleBlock({ title, subtitle }) - Extract lines 80-89

// Consider:
- Shared hook for live payload syncing (used in both CalendarDay and DailyResults)
```

**Impact**: Medium - Important but secondary display mode

---

### 5. **ArticleList.jsx** (LOW - Important + Minor Need)

**Core functionality score**: 8/10 (Used by multiple parents to render articles)
**Refactoring need score**: 4/10

**Problems**:
- **Section building logic** (lines 13-42): Could be cleaner
- **Inline ternary in map**: `item.type === 'section' ? ... : ...`
- **Mixed data transformation and rendering**: Building sections array in render flow

**Refactoring targets**:
```javascript
// Extract to utility function:
- buildSectionedArticles(articles) => returns sectionsWithArticles array

// Possible optimization:
- Memoize section building if articles array changes frequently
```

**Impact**: Medium - Used in multiple places, but currently functional

---

## Components That Don't Need Refactoring

### CacheToggle.jsx
- **Score**: Simple, well-focused, single responsibility
- **Verdict**: Leave as-is

### Feed.jsx
- **Score**: Trivial wrapper component
- **Verdict**: Perfect as-is

### FoldableContainer.jsx
- **Score**: Well-designed reusable component
- **Verdict**: No changes needed

---

## Recommended Refactoring Order

1. **CalendarDay.jsx** - Highest impact, worst state, most complex
2. **ScrapeForm.jsx** - Highest impact, critical path, complex state management
3. **NewsletterDay.jsx** - High impact, moderate complexity
4. **ResultsDisplay.jsx** - Medium impact, good opportunity to extract shared patterns
5. **ArticleList.jsx** - Low priority, minor cleanup

---

## Key Patterns to Extract Across All Refactorings

1. **Data transformation → Pure functions outside components**
   - Date formatting
   - Article grouping/filtering
   - Section building
   - Validation logic

2. **Repetitive UI blocks → Sub-components**
   - Headers with loading states
   - Error displays
   - Progress indicators
   - Title/subtitle blocks

3. **Complex hooks → Custom hooks**
   - Form state + validation + submission
   - Live payload syncing (useSupabaseStorage pattern)

4. **Inline JSX logic → Computed variables**
   - Move complex expressions to const variables before return
   - Use early returns where possible

---

## Success Criteria (Per ArticleCard Standard)

Each refactored component should have:
- ✅ Sub-components with single responsibilities
- ✅ Main component under 150 lines
- ✅ No inline logic longer than 3 lines
- ✅ Pure functions for data transformations
- ✅ Clear separation: data fetching → transformation → presentation
- ✅ No comments explaining what code does (code should be self-documenting)
