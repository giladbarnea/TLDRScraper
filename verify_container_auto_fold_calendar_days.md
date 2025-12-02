---
last_updated: 2025-12-02 10:07, 746b247
---
# Calendar Day Auto-Fold Implementation

## Summary

Implemented auto-collapse and dim behavior for calendar days when all newsletter days within them are removed. This brings calendar days into consistency with existing newsletter day and section behavior.

## Changes Made

### 1. CalendarDay.jsx

**Logic Change** (lines 23-27):
- **Before**: Checked if all articles globally are removed: `articles.every(a => a.removed)`
- **After**: Checks if all newsletter days are all-removed:
  ```javascript
  const newsletterDaysAllRemoved = issues.map(issue => {
    const newsletterArticles = articles.filter(a => a.category === issue.category)
    return newsletterArticles.length > 0 && newsletterArticles.every(a => a.removed)
  })
  const allNewsletterDaysRemoved = newsletterDaysAllRemoved.length > 0 && newsletterDaysAllRemoved.every(removed => removed)
  ```

**Data Attribute** (line 39):
- Added: `data-all-removed={allNewsletterDaysRemoved}`
- Allows O(1) inspection of calendar day state without guessing from CSS

**Dim Styling** (line 44):
- Added conditional opacity to header:
  ```javascript
  ${allNewsletterDaysRemoved ? 'border-slate-200/40 opacity-50' : 'border-slate-200/60'}
  ```

**Collapse Behavior** (line 43):
- Passes `defaultFolded={allNewsletterDaysRemoved}` to FoldableContainer

### 2. NewsletterDay.jsx

**Data Attribute** (line 34):
- Added: `data-all-removed={allRemoved}`
- Exposes newsletter day removed state for O(1) inspection

### 3. FoldableContainer.jsx

**Props Update** (line 5):
- Added: `'data-all-removed': dataAllRemoved` parameter
- Applies data attribute to container div (line 17)

### 4. Section FoldableContainers (within NewsletterDay.jsx)

**Data Attribute** (line 72):
- Added: `data-all-removed={sectionAllRemoved}`
- Exposes section removed state for O(1) inspection

## Behavior Hierarchy

```
CalendarDay
├─ allNewsletterDaysRemoved = ALL newsletter days have all articles removed
│  ├─ Collapses when true
│  └─ Dims (opacity-50, border-slate-200/40) when true
│
└─ NewsletterDay (multiple)
   ├─ allRemoved = ALL articles in this newsletter are removed
   │  ├─ Collapses when true
   │  └─ Dims (opacity-50, border-slate-200) when true
   │
   └─ Section (multiple, optional)
      ├─ sectionAllRemoved = ALL articles in this section are removed
      │  ├─ Collapses when true
      │  └─ Dims (opacity-50) when true
      │
      └─ Articles
```

## Data Attributes for Testing

All three levels now expose their removed state via `data-all-removed` attributes:

```javascript
// Query calendar day state
document.querySelector('section[data-all-removed]').getAttribute('data-all-removed')
// Returns: "true" or "false"

// Query newsletter day states
document.querySelectorAll('[id^="newsletter-"]')
  .map(el => el.parentElement.getAttribute('data-all-removed'))
// Returns: ["true", "false", ...] for each newsletter

// Query section states
document.querySelectorAll('[id^="section-"]')
  .map(el => el.parentElement.getAttribute('data-all-removed'))
// Returns: ["true", "false", ...] for each section
```

## Test Scenarios

Created comprehensive Playwright test suite in `/workspace/tests/test_calendar_day_collapse.py`:

1. **Test 1: Initial State**
   - Calendar day with unremoved articles
   - Expected: `data-all-removed="false"`, no dim styling, not collapsed

2. **Test 2: Partial Removal**
   - All articles removed from one newsletter, but other newsletters have unremoved articles
   - Expected: Newsletter with removed articles collapses/dims, but calendar day remains open

3. **Test 3: Full Removal**
   - All articles removed from all newsletters
   - Expected: Calendar day collapses/dims, all newsletter days collapse/dims

## Verification Commands

```bash
# Syntax check
cd /workspace/client && npx biome check src/components/CalendarDay.jsx src/components/NewsletterDay.jsx src/components/FoldableContainer.jsx

# Run test suite (requires servers running)
cd /workspace
source ./setup.sh && start_server_and_watchdog
cd client && CI=1 npm run dev &
sleep 5
uv run --with=playwright python3 tests/test_calendar_day_collapse.py
```

## Design Principles Applied

1. **No CSS Guessing**: State exposed via dedicated `data-all-removed` attributes for O(1) inspection
2. **Consistent Behavior**: All three levels (calendar day, newsletter day, section) follow the same collapse/dim pattern
3. **Hierarchical Logic**: Calendar day state derived from newsletter day states, not from global article state
4. **Minimal Changes**: Surgical modifications only to required components
5. **Zero Fallbacks**: Code assumes valid inputs and fails early if assumptions are broken
