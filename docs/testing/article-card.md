---
last_updated: 2025-12-02 13:09, 061a370
description: ArticleCard data attributes for state inspection and testing
---
# ArticleCard Data Attributes

## Overview

ArticleCard components expose their state through data attributes for reliable testing and debugging. These attributes reflect the component's state machine faithfully and update automatically on every state transition.

## Boolean State Attributes

### Core State Variables

1. **`data-removed`** - Boolean
   - `true`: Article has been removed by user
   - `false`: Article is visible
   - State transitions: `toggleRemove()` in `useArticleState`

2. **`data-tldr-available`** - Boolean
   - `true`: TLDR has been fetched and is ready to display
   - `false`: TLDR has not been fetched or failed to fetch
   - Computed from: `tldr.status === 'available' && tldr.markdown exists`
   - State transitions: `fetch()` in `useSummary`

3. **`data-expanded`** - Boolean
   - `true`: TLDR content is currently visible
   - `false`: TLDR content is collapsed
   - State transitions: `toggle()`, `expand()`, `collapse()` in `useSummary`

### Additional State Attributes

4. **`data-read`** - Boolean
   - `true`: Article has been marked as read
   - `false`: Article is unread
   - State transitions: `markAsRead()`, `markAsUnread()`, `toggleRead()` in `useArticleState`

### Legacy String Attributes (maintained for backward compatibility)

- **`data-article-state`** - String: `'removed'` | `'read'` | `'unread'`
- **`data-tldr-status`** - String: `'unknown'` | `'creating'` | `'available'` | `'error'`
- **`data-tldr-expanded`** - Boolean (redundant with `data-expanded`)

## State Machine

### Article State Transitions

```
unread (data-read="false")
  │
  ├─> read (data-read="true")
  │    └─> Triggered by: clicking title, expanding TLDR
  │
  └─> removed (data-removed="true")
       └─> Triggered by: clicking trash button
```

### TLDR State Transitions

```
unknown (data-tldr-available="false", data-expanded="false")
  │
  ├─> creating (fetching from API)
  │    └─> data-tldr-status="creating"
  │
  ├─> available (data-tldr-available="true")
  │    │
  │    ├─> expanded (data-expanded="true")
  │    │    └─> Triggered by: clicking TLDR button, clicking card body
  │    │
  │    └─> collapsed (data-expanded="false")
  │         └─> Triggered by: clicking Close button, clicking card body, removing article
  │
  └─> error (data-tldr-available="false")
       └─> data-tldr-status="error"
```

## Automatic State Coupling

**No manual coupling needed.** React's reactivity ensures data attributes update automatically:

1. **User action** → State transition function called
   - Example: User clicks trash button → `toggleRemove()` called

2. **State function** → Supabase write + local state update
   - `useArticleState` updates article state
   - `useSupabaseStorage` persists to database

3. **State change** → React re-render
   - Component re-renders with new state values

4. **JSX attributes** → DOM updated
   - `data-removed={isRemoved}` automatically reflects new value
   - Browser DevTools show updated attribute

## Testing Selectors

### Playwright/Cypress Selectors

```javascript
// Find all removed articles
const removedArticles = page.locator('[data-removed="true"]')

// Find all articles with available TLDRs
const articlesWithTldr = page.locator('[data-tldr-available="true"]')

// Find all expanded TLDRs
const expandedTldrs = page.locator('[data-expanded="true"]')

// Find unread articles
const unreadArticles = page.locator('[data-read="false"]')

// Find specific article by URL
const article = page.locator(`[data-article-url="https://example.com/article"]`)

// Combine selectors
const expandedUnreadArticles = page.locator('[data-read="false"][data-expanded="true"]')
```

### CSS Selectors

```css
/* Style removed articles */
[data-removed="true"] {
  opacity: 0.5;
  filter: grayscale(100%);
}

/* Style articles with available TLDRs */
[data-tldr-available="true"] {
  cursor: pointer;
}

/* Style expanded articles */
[data-expanded="true"] {
  margin-bottom: 1.5rem;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}
```

### DevTools Inspection

Open browser DevTools and run:

```javascript
// Count articles by state
console.log('Total articles:', document.querySelectorAll('[data-article-url]').length)
console.log('Removed:', document.querySelectorAll('[data-removed="true"]').length)
console.log('Read:', document.querySelectorAll('[data-read="true"]').length)
console.log('With TLDR:', document.querySelectorAll('[data-tldr-available="true"]').length)
console.log('Expanded:', document.querySelectorAll('[data-expanded="true"]').length)

// Find first article with available TLDR
document.querySelector('[data-tldr-available="true"]')
```

## Implementation Details

### Location

**File:** `client/src/components/ArticleCard.jsx` (lines 71-74)

```jsx
<div
  onClick={handleCardClick}
  // ... other attributes ...
  data-removed={isRemoved}
  data-read={isRead}
  data-tldr-available={isAvailable}
  data-expanded={tldr.expanded}
  className={...}
>
```

### State Sources

| Attribute | State Variable | Hook | Persisted |
|-----------|---------------|------|-----------|
| `data-removed` | `isRemoved` | `useArticleState` | Yes (Supabase) |
| `data-read` | `isRead` | `useArticleState` | Yes (Supabase) |
| `data-tldr-available` | `isAvailable` | `useSummary` | Yes (Supabase) |
| `data-expanded` | `tldr.expanded` | `useSummary` | No (local only) |

### Why These States?

1. **`data-removed`** - Critical for testing article removal/restoration flow
2. **`data-tldr-available`** - Distinguishes between "no TLDR yet" and "TLDR ready" states
3. **`data-expanded`** - Tracks UI visibility state (not persisted, resets on refresh)
4. **`data-read`** - Useful for testing read/unread tracking

## Example Test Cases

### Playwright E2E Test

```javascript
import { test, expect } from '@playwright/test'

test('article state transitions', async ({ page }) => {
  await page.goto('http://localhost:3000')

  // Find first unread article
  const article = page.locator('[data-read="false"]').first()

  // Initial state
  await expect(article).toHaveAttribute('data-removed', 'false')
  await expect(article).toHaveAttribute('data-expanded', 'false')

  // Click title to mark as read
  await article.locator('a').first().click()
  await expect(article).toHaveAttribute('data-read', 'true')

  // Expand TLDR
  await article.getByRole('button', { name: /TLDR/i }).click()
  await expect(article).toHaveAttribute('data-expanded', 'true')
  await expect(article).toHaveAttribute('data-tldr-available', 'true')

  // Remove article
  await article.getByRole('button', { name: /trash/i }).click()
  await expect(article).toHaveAttribute('data-removed', 'true')
  await expect(article).toHaveAttribute('data-expanded', 'false') // Should collapse
})
```

### Manual Browser Testing

1. Open application in browser
2. Open DevTools → Elements tab
3. Inspect an ArticleCard `<div>` element
4. Observe data attributes update in real-time as you:
   - Click article title → `data-read` changes to `"true"`
   - Click TLDR button → `data-expanded` changes to `"true"`
   - Click trash button → `data-removed` changes to `"true"`

## Future Enhancements

Potential additional state attributes to consider:

- `data-loading` - Boolean for async operations in progress
- `data-tldr-effort` - String for TLDR detail level (`'minimal'` | `'low'` | `'medium'` | `'high'`)
- `data-source` - String for newsletter source (already exists as `data-article-source`)
- `data-has-error` - Boolean for error states

## Related Documentation

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Full state machine documentation
- [headless_playwright_guide.md](./headless_playwright_guide.md) - Browser testing guide
- [useArticleState.js](../../client/src/hooks/useArticleState.js) - Article state management hook
- [useSummary.js](../../client/src/hooks/useSummary.js) - TLDR state management hook
