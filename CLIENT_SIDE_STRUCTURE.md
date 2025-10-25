# JavaScript Modularization Plan

## Executive Summary

This document outlines the plan to extract approximately 2,200 lines of JavaScript from `templates/index.html` into 9 cohesive, orthogonal modules. Each module has a single, clear responsibility and minimal coupling with other modules.

## Analysis of Current Structure

The current JavaScript in `index.html` (lines 1242-3461) contains the following functional domains:

1. **Debug Panel** (~64 lines) - Console logging override and debug UI
2. **Client Storage Model** (~167 lines) - localStorage operations and data schema
3. **Client Hydration** (~572 lines) - Data processing, DOM building, and rendering
4. **Article State Tracking** (~214 lines) - Article card state management
5. **Summary Effort Selector** (~95 lines) - Reasoning effort configuration
6. **Summary Clipboard** (~40 lines) - Copy-to-clipboard functionality
7. **Removal Controls** (~18 lines) - Article removal/restore
8. **Summary Delivery** (~210 lines) - Summary expansion and API integration
9. **TLDR Delivery** (~174 lines) - TLDR expansion and API integration
10. **Scrape Intake** (~131 lines) - Form handling and scrape workflow
11. **Issue Collapse Manager** (~92 lines) - Issue content collapse/expand
12. **App Bootstrap** (~26 lines) - Initialization and event binding

## Proposed Module Structure

### 1. **storage.js** (~200 lines)
**Responsibility:** All localStorage operations and data model definitions

**Exports:**
- `ARTICLE_STATUS` - Status constants (unknown, creating, available, error)
- `normalizeIsoDate(value)` - ISO date normalization
- `getStorageKeyForDate(date)` - Storage key generation
- `cloneArticleState(article)` - Deep clone with normalization
- `sanitizeIssue(issue)` - Issue normalization
- `ClientStorage` object:
  - `readDay(date)` - Read daily payload from localStorage
  - `writeDay(date, payload)` - Write daily payload to localStorage
  - `mergeDay(date, payload)` - Merge new data with existing
  - `hasDay(date)` - Check if date exists in storage
  - `updateArticle(date, url, updater)` - Transactional article update

**Dependencies:** None (pure data layer)

**Why cohesive:** All storage operations and data model logic in one place. This is the foundation layer that other modules depend on.

---

### 2. **dom-builder.js** (~600 lines)
**Responsibility:** Building HTML structures and transforming DOM elements

**Exports:**
- `escapeHtml(value)` - HTML escaping utility
- `computeDateRange(startDate, endDate)` - Date range calculation
- `buildDailyPayloadsFromScrape(data)` - Convert API response to daily payloads
- `buildStatsFromPayloads(payloads)` - Aggregate statistics
- `buildWhiteyHtmlFromPayloads(payloads)` - Generate Whitey surface HTML
- `buildPayloadIndices(payloads)` - Create lookup maps
- `transformWhiteySurface(root, maps)` - Transform static HTML to interactive cards
- `renderPayloads(payloads, options)` - Main rendering orchestrator
- `hydrateRangeFromStore(startDate, endDate)` - Load range from storage
- `applyStoredArticleState(payloads)` - Apply persisted state to DOM

**Dependencies:**
- `storage.js` - For data reading/writing
- `article-card.js` - For card state utilities (imported by article-card.js actually uses this)

**Why cohesive:** All DOM construction and transformation logic. Converts data structures into visual representations. This is the presentation layer.

---

### 3. **article-card.js** (~250 lines)
**Responsibility:** Article card state management and behavior

**Exports:**
- `getArticleState(card)` - Get card state (0=unread, 1=read, 2=removed)
- `sortArticlesByState(articleList)` - Sort and re-insert section titles
- `markCategoryBoundaries(articleList)` - Visual separation markers
- `parseTitleWithDomain(titleWithDomain)` - Extract title and domain
- `getDomainLabelFromUrl(url)` - Generate domain label
- `setArticleLinkText(link, text)` - Update link text
- `isCardRemoved(card)` - Check removal state
- `setCardRemovedState(card, removed)` - Toggle removal state
- `markArticleAsRead(card)` - Mark card as read
- `updateStoredArticleFromCard(card, updater)` - Helper to update storage

**Dependencies:**
- `storage.js` - For persisting state changes

**Why cohesive:** Everything related to individual article card state and ordering. This is the article-specific business logic layer.

---

### 4. **summary.js** (~310 lines)
**Responsibility:** Summary functionality including effort selection and delivery

**Exports:**
- `SUMMARY_EFFORT_OPTIONS` - Available effort levels
- `normalizeSummaryEffort(value)` - Validate and normalize effort
- `getCardSummaryEffort(card)` - Read card's effort setting
- `setCardSummaryEffort(card, value)` - Update card's effort setting
- `setupSummaryEffortControls(card, expandBtn, chevronBtn, dropdown)` - Wire dropdown
- `bindSummaryExpansion()` - Main summary event handler
- `toggleCopyButton(card, shouldShow)` - Show/hide copy button

**Dependencies:**
- `storage.js` - For state persistence
- `article-card.js` - For marking as read
- External: `marked`, `DOMPurify`

**Why cohesive:** All summary-related functionality in one place. Effort selection and delivery are tightly coupled - changing effort triggers new delivery.

---

### 5. **tldr.js** (~180 lines)
**Responsibility:** TLDR functionality

**Exports:**
- `bindTldrExpansion()` - TLDR click handler and API integration

**Dependencies:**
- `storage.js` - For state persistence
- `article-card.js` - For marking as read, getting effort
- External: `marked`, `DOMPurify`

**Why cohesive:** Parallel to summary.js but for TLDR. Kept separate because it's a distinct feature with its own API endpoint and state.

---

### 6. **issue.js** (~130 lines)
**Responsibility:** Issue-level operations (collapse/expand)

**Exports:**
- `escapeIssueKeySelector(issueKey)` - CSS selector escaping
- `findIssueContainer(issueKey, toggleEl)` - Find issue container
- `getIssueContentNodes(container)` - Get nodes belonging to issue
- `collapseIssueContent(container, options)` - Collapse issue
- `expandIssueContent(container)` - Expand issue
- `toggleIssueContent(container)` - Toggle collapse state
- `bindIssueToggleControls()` - Handle issue toggle events

**Dependencies:**
- None

**Why cohesive:** Issue operations are distinct from article operations. This handles entire issue sections as units, with their own collapse logic.

---

### 7. **scrape.js** (~140 lines)
**Responsibility:** Scraping workflow and form handling

**Exports:**
- `setDefaultDates()` - Initialize date inputs
- `bindScrapeForm()` - Form submission handler and orchestration

**Dependencies:**
- `storage.js` - For reading/writing scraped data
- `dom-builder.js` - For rendering results
- `issue.js` - For restoring read state

**Why cohesive:** Orchestrates the entire scrape workflow from form validation through API call to rendering. This is the main user interaction flow.

---

### 8. **ui-utils.js** (~110 lines)
**Responsibility:** General UI utilities and helpers

**Exports:**
- `clipboardIconMarkup` - SVG icon
- `showCopyToast()` - Display copy confirmation
- `bindCopySummaryFlow()` - Copy button handler
- `bindRemovalControls()` - Article remove/restore handler
- Debug panel functionality:
  - `debugLog(message, options)` - Log to debug panel
  - `initDebugPanel()` - Override console and setup panel

**Dependencies:**
- `article-card.js` - For checking removal state
- `storage.js` - For persisting removal state

**Why cohesive:** Small, reusable UI utilities that don't fit cleanly into other modules. These are cross-cutting concerns used by multiple features.

---

### 9. **app.js** (~30 lines)
**Responsibility:** Application initialization and orchestration

**Exports:**
- None (immediately executes initialization)

**Functionality:**
- Import all modules
- Call `initDebugPanel()`
- Call `setDefaultDates()`
- Execute initial hydration IIFE
- Call all `bind*()` functions

**Dependencies:**
- All other modules

**Why cohesive:** Single entry point that wires everything together. Thin orchestration layer that knows about all modules but doesn't contain business logic.

---

## Module Dependency Graph

```
┌─────────────┐
│  storage.js │  ← Foundation layer (no dependencies)
└─────────────┘
      ▲
      │
      ├──────────────────┬────────────┬─────────────┬──────────────┐
      │                  │            │             │              │
┌─────────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐
│dom-builder │  │article-card│  │issue.js│  │summary.js│  │   tldr.js    │
└─────────────┘  └───────────┘  └────────┘  └──────────┘  └──────────────┘
      ▲                ▲            ▲             ▲                ▲
      │                │            │             │                │
      └─────┬──────────┴────────────┴─────────────┴────────────────┘
            │                                                  │
      ┌───────────┐                                     ┌──────────┐
      │ scrape.js │                                     │ui-utils.js│
      └───────────┘                                     └──────────┘
            ▲                                                  ▲
            │                                                  │
            └──────────────────┬───────────────────────────────┘
                               │
                          ┌─────────┐
                          │ app.js  │  ← Orchestration layer
                          └─────────┘
```

## Implementation Strategy

### Phase 1: Create Module Files
1. Create 9 new `.js` files in flat structure (no directories)
2. Add ES6 module imports/exports
3. Extract code from `index.html` preserving all comments and region markers

### Phase 2: Update HTML
1. Remove `<script>` content from `index.html`
2. Add module script imports:
   ```html
   <script type="module" src="/storage.js"></script>
   <script type="module" src="/dom-builder.js"></script>
   <script type="module" src="/article-card.js"></script>
   <script type="module" src="/summary.js"></script>
   <script type="module" src="/tldr.js"></script>
   <script type="module" src="/issue.js"></script>
   <script type="module" src="/scrape.js"></script>
   <script type="module" src="/ui-utils.js"></script>
   <script type="module" src="/app.js"></script>
   ```

### Phase 3: Serve Static JS Files
Update `serve.py` to serve static JavaScript files from the root directory.

### Phase 4: Test
1. Verify localStorage operations
2. Test scraping workflow
3. Test summary/TLDR expansion
4. Test issue collapse/read state
5. Test article removal
6. Test copy-to-clipboard
7. Verify debug panel

## Benefits of This Approach

1. **Cohesion**: Each module has a single, clear responsibility
2. **Orthogonality**: Modules have minimal overlap in functionality
3. **Maintainability**: Easier to locate and modify specific features
4. **Testability**: Each module can be unit tested independently
5. **Performance**: Modules can be loaded in parallel by browser
6. **Scalability**: New features can be added as new modules
7. **Developer Experience**: Smaller files are easier to navigate
8. **Reusability**: Modules like `storage.js` and `ui-utils.js` are highly reusable

## Trade-offs and Considerations

### Pros
- Clear separation of concerns
- Easier to reason about codebase
- Better code organization for future development
- Parallel module loading potential

### Cons
- More HTTP requests (mitigated by HTTP/2 multiplexing)
- Need to manage module imports/exports
- Slightly more complex build/serve setup

### Why Flat Structure?
As requested, all modules are in the root directory with no nesting. This:
- Keeps import paths simple
- Makes all modules equally accessible
- Avoids artificial grouping that may not age well
- Follows the principle: "only add hierarchy when absolutely necessary"

## Notes on Dependencies

### External Dependencies
The following external libraries are used:
- `marked` - Markdown parsing (summary/TLDR rendering)
- `DOMPurify` - HTML sanitization (security)

Both are currently loaded via CDN in `index.html` and will remain there.

### Internal Cross-Module Communication

Some modules need to call functions from other modules:
- `summary.js` and `tldr.js` call `markArticleAsRead()` from `article-card.js`
- `dom-builder.js` calls `applyStoredArticleState()` which uses `article-card.js`
- `scrape.js` orchestrates `storage.js`, `dom-builder.js`, and `issue.js`

These dependencies are kept minimal and unidirectional (no circular dependencies).

## Region Comments Preservation

The original code uses region comments like:
```javascript
// #region -------[ ClientStorageModel ]-------
// ... code ...
// #endregion
```

These will be preserved in the extracted modules to maintain code organization and IDE folding support. However, some regions may be renamed to match the new module structure.

## Future Enhancements

After modularization, these improvements become easier:

1. **Type Safety**: Add JSDoc or TypeScript type annotations
2. **Testing**: Add unit tests for each module
3. **Build Process**: Optionally bundle/minify for production
4. **Code Splitting**: Load modules on-demand for faster initial load
5. **Shared Constants**: Extract magic strings to a constants module
6. **Dependency Injection**: Make modules more testable by injecting dependencies

## Conclusion

This modularization plan balances:
- **Cohesion** (each module does one thing well)
- **Orthogonality** (minimal functional overlap)
- **Pragmatism** (not over-engineering for unknown future needs)
- **Simplicity** (flat structure, clear responsibilities)

The result is a maintainable, scalable architecture that preserves all existing functionality while dramatically improving code organization.
