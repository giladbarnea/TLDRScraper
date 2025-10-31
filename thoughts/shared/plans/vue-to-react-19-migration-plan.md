---
created: 2025-10-31
status: draft
---

# Vue 3 to React 19 Migration Plan

## Executive Summary

This document outlines a comprehensive plan to migrate TLDRScraper from Vue 3 to React 19. The migration takes advantage of React 19's new features (the `use` hook, `useTransition`, and the React Compiler for automatic memoization) while simplifying local state management compared to the Vue implementation. The focus is on preserving the existing state management patterns while translating them to React 19 paradigms.

**Timeline Estimate**: 3-4 weeks for full migration with testing

## Table of Contents

1. [Current Vue Architecture Analysis](#current-vue-architecture-analysis)
2. [React 19 State Management Strategy](#react-19-state-management-strategy)
3. [Component-by-Component Migration Map](#component-by-component-migration-map)
4. [Build System Changes](#build-system-changes)
5. [Testing Strategy](#testing-strategy)
6. [Implementation Order](#implementation-order)
7. [Risk Mitigation](#risk-mitigation)

---

## Current Vue Architecture Analysis

### Vue State Patterns Used

#### 1. localStorage Sync Pattern (`useLocalStorage.js`)

**Current Implementation:**
```javascript
// Vue pattern
const { data, clear } = useLocalStorage(key, defaultValue)

// Features:
// - ref() wraps localStorage value
// - watch() with deep: true syncs changes to localStorage
// - Dispatches 'local-storage-change' event for same-tab reactivity
// - Auto-serialization with JSON.stringify/parse
```

**Critical Insight**: Vue's `watch()` with `deep: true` automatically tracks nested object mutations and persists them. React doesn't have this built-in, so we need to handle updates explicitly.

**State Bug #1 (commit 16bd653)**: Components don't automatically react to localStorage changes. The fix was to dispatch a custom `'local-storage-change'` event that components listen to, forcing re-computation.

#### 2. Article State Management (`useArticleState.js`)

**Current Implementation:**
```javascript
// Manages per-article state
const {
  article,           // computed from localStorage
  isRead,           // computed boolean
  isRemoved,        // computed boolean
  isTldrHidden,     // computed boolean
  state,            // computed sort priority (0-3)
  markAsRead,       // mutation
  toggleRead,       // mutation
  toggleRemove,     // mutation
  markTldrHidden,   // mutation
  updateArticle     // generic mutation
} = useArticleState(date, url)

// Key features:
// - Reads from useLocalStorage
// - article is a computed() that finds the article by URL
// - State properties are all computed() from article
// - Mutations directly modify article.value properties
// - Vue's reactivity propagates changes back to localStorage
```

**State Bug #2 (commit 3bfceee)**: When merging cache data, a new property (`tldrHidden`) was lost because the merge function didn't include it. The fix was to add it to the merge operation in `useScraper.js:126`.

#### 3. Cache Settings (`useCacheSettings.js`)

**Current Implementation:**
```javascript
const {
  enabled,      // ref from localStorage
  statusText,   // computed string
  toggle        // mutation
} = useCacheSettings()

// Simple boolean toggle in localStorage
```

#### 4. Scraper (`useScraper.js`)

**Current Implementation:**
```javascript
const {
  loading,          // ref
  error,            // ref
  progress,         // ref
  results,          // ref
  scrape,           // async action
  isRangeCached,    // check function
  loadFromCache     // load function
} = useScraper()

// Key flows:
// 1. Check if range is fully cached
// 2. Load from cache OR fetch from API
// 3. Build daily payloads from API response
// 4. Merge with existing cache (preserving user state)
// 5. Update results ref
```

**Critical Merge Logic (lines 108-140):**
```javascript
function mergeWithCache(payloads) {
  return payloads.map(payload => {
    const { data } = useLocalStorage(key, null)
    if (data.value) {
      // Preserve: summary, tldr, read, removed, tldrHidden
      // Replace: everything else from fresh scrape
    }
  })
}
```

#### 5. Summary/TLDR (`useSummary.js`)

**Current Implementation:**
```javascript
const {
  status,         // computed from article
  markdown,       // computed from article
  html,           // computed (marked + DOMPurify)
  loading,        // ref (local UI state)
  expanded,       // ref (local UI state)
  isAvailable,    // computed
  buttonLabel,    // computed
  fetch,          // async action
  toggle,         // sync action
} = useSummary(date, url, type)

// Key features:
// - Reads article from useArticleState
// - Converts markdown to HTML with marked + DOMPurify
// - Manages local UI state (loading, expanded)
// - Updates article state on successful fetch
```

### Vue Reactivity Patterns

1. **`ref()`**: Wraps primitive values for reactivity
2. **`computed()`**: Derives values, auto-tracks dependencies
3. **`watch()`**: Side effects when dependencies change
4. **Custom events**: `window.dispatchEvent()` for cross-component sync
5. **Deep watchers**: `{ deep: true }` for nested object changes

### Component Hierarchy

```
App.vue
├── CacheToggle.vue (uses useCacheSettings)
├── ScrapeForm.vue (uses useScraper)
└── ResultsDisplay.vue
    └── ArticleList.vue (listens to 'local-storage-change')
        └── ArticleCard.vue (uses useArticleState, useSummary × 2)
```

### Data Structures

#### DailyPayload (localStorage key: `newsletters:scrapes:{date}`)
```typescript
{
  date: string,              // "2024-01-01"
  cachedAt: string,          // ISO timestamp
  articles: Article[],
  issues: Issue[]
}
```

#### Article
```typescript
{
  url: string,               // canonical URL (unique ID)
  title: string,
  issueDate: string,
  category: string,
  sourceId: string,
  section: string | null,
  sectionEmoji: string | null,
  sectionOrder: number | null,
  newsletterType: string | null,

  // User state
  removed: boolean,
  tldrHidden: boolean,
  read: {
    isRead: boolean,
    markedAt: string | null
  },

  // AI-generated content
  summary: {
    status: 'unknown' | 'creating' | 'available' | 'error',
    markdown: string,
    effort: 'minimal' | 'low' | 'medium' | 'high',
    checkedAt: string | null,
    errorMessage: string | null
  },

  tldr: {
    status: 'unknown' | 'creating' | 'available' | 'error',
    markdown: string,
    effort: 'minimal' | 'low' | 'medium' | 'high',
    checkedAt: string | null,
    errorMessage: string | null
  }
}
```

---

## React 19 State Management Strategy

### Core Translation Patterns

| Vue Pattern | React 19 Pattern | Notes |
|-------------|------------------|-------|
| `ref()` | `useState()` | Direct replacement for reactive primitives |
| `computed()` | Inline calculations | React Compiler auto-memoizes, no need for `useMemo` |
| `computed()` (complex) | `useMemo()` (if needed) | Only for effect dependencies |
| `watch()` | `useEffect()` | For side effects |
| Custom events | Shared subscription map + `useSyncExternalStore` | React-managed notifications without DOM events |
| `useLocalStorage()` deep watch | Custom hook with explicit updates | Need manual sync |

### React 19 Features to Leverage

#### 1. Form Submission Flow

**Use for:**
- Scrape form submission
- Summary/TLDR fetch buttons (if they evolve into forms)

**Approach:**
- Controlled inputs with `useState`
- Local `isSubmitting`/`error` state for feedback
- Introduce `useTransition` later if the UI needs to stay responsive during slower requests

**Example:**
```javascript
function ScrapeForm() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      const results = await scrapeNewsletters(startDate, endDate)
      onResults(results)
    } catch (err) {
      setError(err.message ?? 'Failed to scrape newsletters')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Scraping...' : 'Scrape Newsletters'}
      </button>
      {error && <div className="error">{error}</div>}
    </form>
  )
}
```

#### 2. Direct Local Updates

**Use for:**
- Marking articles as read
- Toggling removed state
- Updating TLDR hidden flag

**Example:**
```javascript
function ArticleCard({ article }) {
  const { article: liveArticle, updateArticle } = useArticleState(article.issueDate, article.url)
  const currentArticle = liveArticle ?? article

  const toggleRead = () => {
    updateArticle((current) => ({
      read: {
        isRead: !current.read?.isRead,
        markedAt: !current.read?.isRead ? new Date().toISOString() : null
      }
    }))
  }

  return (
    <div className={currentArticle.read?.isRead ? 'read' : 'unread'}>
      {/* article content */}
    </div>
  )
}
```

#### 3. The `use` Hook

**Use for:**
- Reading context conditionally
- Reading promises (for future streaming)

**Not needed initially** but good to know for future enhancements.

#### 4. React Compiler

**Enable by default**. Benefits:
- Automatic memoization of computed values
- No need for manual `useMemo` / `useCallback`
- Better performance than Vue's reactivity system
- Simpler code

**Configuration:**
```javascript
// vite.config.js
export default {
  plugins: [
    react({
      babel: {
        plugins: [['babel-plugin-react-compiler', { target: '19' }]]
      }
    })
  ]
}
```

### localStorage Sync Solution

**Custom Hook: `useLocalStorage`**

```javascript
import { useCallback, useSyncExternalStore } from 'react'

const listeners = new Map()

function subscribeToKey(key, callback) {
  if (!listeners.has(key)) {
    listeners.set(key, new Set())
  }

  const callbacks = listeners.get(key)
  callbacks.add(callback)

  return () => {
    callbacks.delete(callback)
    if (callbacks.size === 0) {
      listeners.delete(key)
    }
  }
}

function notifyKey(key) {
  const callbacks = listeners.get(key)
  if (callbacks) {
    callbacks.forEach((callback) => callback())
  }
}

function useLocalStorage(key, defaultValue) {
  const getSnapshot = useCallback(() => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch {
      return defaultValue
    }
  }, [key, defaultValue])

  const subscribe = useCallback((callback) => subscribeToKey(key, callback), [key])

  const value = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  const setValue = useCallback((newValue) => {
    try {
      const previous = getSnapshot()
      const valueToStore = typeof newValue === 'function'
        ? newValue(previous)
        : newValue

      localStorage.setItem(key, JSON.stringify(valueToStore))
      notifyKey(key)
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
    }
  }, [key, getSnapshot])

  const remove = useCallback(() => {
    localStorage.removeItem(key)
    notifyKey(key)
  }, [key])

  return [value, setValue, remove]
}
```

**Why `useSyncExternalStore`?**
1. Built for exactly this use case (syncing with external state)
2. Handles concurrent rendering correctly
3. Built-in support for hydration
4. Works with React 18+ and React 19

### Article State Management Solution

**Custom Hook: `useArticleState`**

```javascript
function useArticleState(date, url) {
  const storageKey = `newsletters:scrapes:${date}`
  const [payload, setPayload] = useLocalStorage(storageKey, null)

  // Find article in payload
  const article = payload?.articles?.find(a => a.url === url) || null

  // Derived state (React Compiler will memoize these)
  const isRead = article?.read?.isRead ?? false
  const isRemoved = article?.removed ?? false
  const isTldrHidden = article?.tldrHidden ?? false

  const state = !article ? 0
    : article.removed ? 3
    : article.tldrHidden ? 2
    : article.read?.isRead ? 1
    : 0

  // Mutation functions
  const updateArticle = useCallback((updater) => {
    if (!article) return

    setPayload(current => {
      if (!current) return current

      return {
        ...current,
        articles: current.articles.map(a =>
          a.url === url ? { ...a, ...updater(a) } : a
        )
      }
    })
  }, [article, url, setPayload])

  const markAsRead = useCallback(() => {
    updateArticle(() => ({
      read: { isRead: true, markedAt: new Date().toISOString() }
    }))
  }, [updateArticle])

  const markAsUnread = useCallback(() => {
    updateArticle(() => ({
      read: { isRead: false, markedAt: null }
    }))
  }, [updateArticle])

  const toggleRead = useCallback(() => {
    if (isRead) markAsUnread()
    else markAsRead()
  }, [isRead, markAsRead, markAsUnread])

  const setRemoved = useCallback((removed) => {
    updateArticle(() => ({ removed: Boolean(removed) }))
  }, [updateArticle])

  const toggleRemove = useCallback(() => {
    setRemoved(!isRemoved)
  }, [isRemoved, setRemoved])

  const setTldrHidden = useCallback((hidden) => {
    updateArticle(() => ({ tldrHidden: Boolean(hidden) }))
  }, [updateArticle])

  return {
    article,
    isRead,
    isRemoved,
    isTldrHidden,
    state,
    markAsRead,
    markAsUnread,
    toggleRead,
    setRemoved,
    toggleRemove,
    setTldrHidden,
    updateArticle
  }
}
```

---

## Component-by-Component Migration Map

### 1. App Component

**Current: `App.vue`**
```vue
<script setup>
import { ref, onMounted } from 'vue'
import CacheToggle from './components/CacheToggle.vue'
import ScrapeForm from './components/ScrapeForm.vue'
import ResultsDisplay from './components/ResultsDisplay.vue'
import { useScraper } from './composables/useScraper'

const results = ref(null)
const { loadFromCache } = useScraper()

onMounted(() => {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  const endDate = today.toISOString().split('T')[0]
  const startDate = threeDaysAgo.toISOString().split('T')[0]

  const cached = loadFromCache(startDate, endDate)
  if (cached) {
    results.value = cached
  }
})

function handleResults(data) {
  results.value = data
}
</script>
```

**React 19: `App.jsx`**
```javascript
import { useState, useEffect } from 'react'
import CacheToggle from './components/CacheToggle'
import ScrapeForm from './components/ScrapeForm'
import ResultsDisplay from './components/ResultsDisplay'
import { loadFromCache } from './lib/scraper'

function App() {
  const [results, setResults] = useState(null)

  // Load cache on mount
  useEffect(() => {
    const today = new Date()
    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)

    const endDate = today.toISOString().split('T')[0]
    const startDate = threeDaysAgo.toISOString().split('T')[0]

    const cached = loadFromCache(startDate, endDate)
    if (cached) {
      setResults(cached)
    }
  }, [])

  return (
    <div className="container">
      <h1>Newsletter Aggregator</h1>
      <CacheToggle />
      <ScrapeForm onResults={setResults} />
      {results && <ResultsDisplay results={results} />}
    </div>
  )
}

export default App
```

**Changes:**
- `ref()` → `useState()`
- `onMounted()` → `useEffect(() => {}, [])`
- `@results` event → `onResults` prop
- Template syntax → JSX
- No reactivity system needed (React Compiler handles it)

---

### 2. CacheToggle Component

**Current: `CacheToggle.vue`**
```vue
<script setup>
import { useCacheSettings } from '@/composables/useCacheSettings'

const { enabled, statusText } = useCacheSettings()
</script>

<template>
  <div class="cache-toggle-container">
    <label class="cache-toggle-label" for="cacheToggle">
      <input
        id="cacheToggle"
        v-model="enabled"
        type="checkbox"
        class="cache-toggle-input"
      >
      <span class="cache-toggle-checkbox" />
      <span class="cache-toggle-text">Cache</span>
      <span class="cache-toggle-status">{{ statusText }}</span>
    </label>
  </div>
</template>
```

**React 19: `CacheToggle.jsx`**
```javascript
import { useLocalStorage } from '../hooks/useLocalStorage'

function CacheToggle() {
  const [enabled, setEnabled] = useLocalStorage('cache:enabled', true)

  const statusText = enabled ? '(enabled)' : '(disabled)'

  return (
    <div className="cache-toggle-container">
      <label className="cache-toggle-label" htmlFor="cacheToggle">
        <input
          id="cacheToggle"
          type="checkbox"
          className="cache-toggle-input"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          aria-label="Enable cache"
        />
        <span className="cache-toggle-checkbox" />
        <span className="cache-toggle-text">Cache</span>
        <span className="cache-toggle-status">{statusText}</span>
      </label>
    </div>
  )
}

export default CacheToggle
```

**Changes:**
- Inline `useCacheSettings` logic into component (simpler)
- `v-model` → `checked` + `onChange`
- Computed `statusText` becomes inline expression
- React Compiler auto-memoizes `statusText`

---

### 3. ScrapeForm Component

**Current: `ScrapeForm.vue`**
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useScraper } from '@/composables/useScraper'

const emit = defineEmits(['results'])

const startDate = ref('')
const endDate = ref('')

const { scrape, loading, error, progress } = useScraper()

const daysDiff = computed(() => {
  if (!startDate.value || !endDate.value) return 0
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  return Math.ceil((end - start) / (1000 * 60 * 60 * 24))
})

const validationError = computed(() => {
  if (!startDate.value || !endDate.value) return null
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  if (start > end) {
    return 'Start date must be before or equal to end date.'
  }
  if (daysDiff.value >= 31) {
    return 'Date range cannot exceed 31 days.'
  }
  return null
})

const isDisabled = computed(() => loading.value || !!validationError.value)

onMounted(() => {
  setDefaultDates()
})

function setDefaultDates() {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  endDate.value = today.toISOString().split('T')[0]
  startDate.value = threeDaysAgo.toISOString().split('T')[0]
}

async function handleSubmit() {
  if (validationError.value) return

  const results = await scrape(startDate.value, endDate.value)
  if (results) {
    emit('results', results)
  }
}
</script>
```

**React 19: `ScrapeForm.jsx`**
```javascript
import { useState, useEffect, useCallback } from 'react'
import { scrapeNewsletters } from '../lib/scraper'

function ScrapeForm({ onResults }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const today = new Date()
    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)

    setEndDate(today.toISOString().split('T')[0])
    setStartDate(threeDaysAgo.toISOString().split('T')[0])
  }, [])

  const daysDiff = !startDate || !endDate ? 0 :
    Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24))

  const validationError = !startDate || !endDate ? null :
    new Date(startDate) > new Date(endDate)
      ? 'Start date must be before or equal to end date.'
      : daysDiff >= 31
      ? 'Date range cannot exceed 31 days.'
      : null

  const handleSubmit = useCallback(async (event) => {
    event.preventDefault()
    if (validationError) {
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const results = await scrapeNewsletters(startDate, endDate)
      onResults(results)
    } catch (err) {
      setError(err.message ?? 'Failed to scrape newsletters')
    } finally {
      setIsSubmitting(false)
    }
  }, [validationError, startDate, endDate, onResults])

  const isDisabled = isSubmitting || !!validationError

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="startDate">Start Date:</label>
          <input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="endDate">End Date:</label>
          <input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          disabled={isDisabled}
        >
          {isSubmitting ? 'Scraping...' : 'Scrape Newsletters'}
        </button>
      </form>

      {isSubmitting && (
        <div className="progress">
          <div>Scraping newsletters... This may take several minutes.</div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: '50%' }} />
          </div>
        </div>
      )}

      {validationError && (
        <div className="error" role="alert">{validationError}</div>
      )}

      {error && (
        <div className="error" role="alert">Error: {error}</div>
      )}
    </div>
  )
}

export default ScrapeForm
```

**Changes:**
- `useScraper()` → local `handleSubmit` that delegates to `scrapeNewsletters`
- Pending/error feedback managed with component state (`useState`)
- `computed()` → inline calculations (React Compiler memoizes)
- `emit('results')` → `onResults(results)` callback prop
- Form submission handled with a controlled `onSubmit` function

**Note**: Progress tracking simplified. In React 19, we can enhance this with streaming if needed.

---

### 4. ResultsDisplay Component

**Current: `ResultsDisplay.vue`**
```vue
<script setup>
import { computed, ref } from 'vue'
import ArticleList from './ArticleList.vue'

const props = defineProps({
  results: {
    type: Object,
    required: true
  }
})

const showToast = ref(false)
let toastTimeout = null

const statsLines = computed(() => {
  const stats = props.results.stats
  return [
    `📊 Stats: ${stats.total_articles} articles, ${stats.unique_urls} unique URLs`,
    `📅 Dates: ${stats.dates_with_content}/${stats.dates_processed} with content`,
    props.results.source && `Source: ${props.results.source}`
  ].filter(Boolean)
})

const articlesByDate = computed(() => {
  const payloads = props.results.payloads || []
  return payloads.map(payload => ({
    date: payload.date,
    articles: payload.articles.map((article, index) => ({
      ...article,
      originalOrder: index
    })),
    issues: payload.issues || []
  }))
})

const debugLogs = computed(() => props.results.debugLogs || [])

function handleCopySummary() {
  clearTimeout(toastTimeout)
  showToast.value = true
  toastTimeout = setTimeout(() => {
    showToast.value = false
  }, 2000)
}
</script>
```

**React 19: `ResultsDisplay.jsx`**
```javascript
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocalStorage } from '../hooks/useLocalStorage'
import ArticleList from './ArticleList'

function ResultsDisplay({ results }) {
  const [showToast, setShowToast] = useState(false)

  const statsLines = [
    `📊 Stats: ${results.stats.total_articles} articles, ${results.stats.unique_urls} unique URLs`,
    `📅 Dates: ${results.stats.dates_with_content}/${results.stats.dates_processed} with content`,
    results.source && `Source: ${results.source}`
  ].filter(Boolean)

  const debugLogs = results.debugLogs || []

  const handleCopySummary = () => {
    setShowToast(true)
    setTimeout(() => setShowToast(false), 2000)
  }

  return (
    <div className="result success">
      <div className="stats">
        {statsLines.map((line, index) => (
          <div key={index}>{line}</div>
        ))}
      </div>

      {debugLogs.length > 0 && (
        <div className="logs-slot">
          <details>
            <summary>Debug logs</summary>
            <pre>{debugLogs.join('\n')}</pre>
          </details>
        </div>
      )}

      <main id="write">
        {(results.payloads || []).map((payload) => (
          <DailyResults
            key={payload.date}
            payload={payload}
            onCopySummary={handleCopySummary}
          />
        ))}
      </main>

      {createPortal(
        <div className={`copy-toast ${showToast ? 'show' : ''}`}>
          Copied to clipboard
        </div>,
        document.body
      )}
    </div>
  )
}

function DailyResults({ payload, onCopySummary }) {
  const [livePayload] = useLocalStorage(
    `newsletters:scrapes:${payload.date}`,
    payload
  )

  const date = livePayload?.date ?? payload.date
  const articles = (livePayload?.articles ?? payload.articles).map((article, index) => ({
    ...article,
    originalOrder: index
  }))
  const issues = livePayload?.issues ?? payload.issues ?? []

  return (
    <div className="date-group">
      <div className="date-header-container" data-date={date}>
        <h2>{date}</h2>
      </div>

      {issues.map((issue) => (
        <div
          key={`${date}-${issue.category}`}
          className="issue-section"
        >
          <div className="issue-header-container">
            <h4>{issue.category}</h4>
          </div>

          {(issue.title || issue.subtitle) && (
            <div className="issue-title-block">
              {issue.title && (
                <div className="issue-title-line">{issue.title}</div>
              )}
              {issue.subtitle && issue.subtitle !== issue.title && (
                <div className="issue-title-line">{issue.subtitle}</div>
              )}
            </div>
          )}

          <ArticleList
            articles={articles.filter((article) => article.category === issue.category)}
            onCopySummary={onCopySummary}
          />
        </div>
      ))}

      {articles.some((article) => !article.category) && (
        <ArticleList
          articles={articles.filter((article) => !article.category)}
          onCopySummary={onCopySummary}
        />
      )}
    </div>
  )
}

export default ResultsDisplay
```

**Changes:**
- `computed()` → inline calculations (React Compiler memoizes)
- Daily storage sync handled inside `DailyResults` with `useLocalStorage`, no custom DOM events
- `Teleport` → `createPortal()` from `react-dom`
- `v-for` → `.map()`
- `v-if` → `&&` or ternary

---

### 5. ArticleList Component

**Current: `ArticleList.vue`**
```vue
<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import ArticleCard from './ArticleCard.vue'

const props = defineProps({
  articles: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['copy-summary'])

// Force re-computation trigger for storage changes
const storageVersion = ref(0)

function handleStorageChange() {
  storageVersion.value++
}

onMounted(() => {
  window.addEventListener('local-storage-change', handleStorageChange)
})

onUnmounted(() => {
  window.removeEventListener('local-storage-change', handleStorageChange)
})

function getArticleState(article) {
  // Access storageVersion to make this reactive
  storageVersion.value

  const storageKey = `newsletters:scrapes:${article.issueDate}`
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw) {
      const payload = JSON.parse(raw)
      const liveArticle = payload.articles?.find(a => a.url === article.url)
      if (liveArticle) {
        if (liveArticle.removed) return 3
        if (liveArticle.tldrHidden) return 2
        if (liveArticle.read?.isRead) return 1
        return 0
      }
    }
  } catch (err) {
    console.error('Failed to read from localStorage:', err)
  }

  if (article.removed) return 3
  if (article.tldrHidden) return 2
  if (article.read?.isRead) return 1
  return 0
}

const sortedArticles = computed(() => {
  return [...props.articles].sort((a, b) => {
    const stateDiff = getArticleState(a) - getArticleState(b)
    if (stateDiff !== 0) return stateDiff

    const orderA = a.originalOrder ?? 0
    const orderB = b.originalOrder ?? 0
    return orderA - orderB
  })
})

const sectionsWithArticles = computed(() => {
  const sections = []
  let currentSection = null

  sortedArticles.value.forEach((article, index) => {
    const sectionTitle = article.section
    const sectionEmoji = article.sectionEmoji
    const sectionKey = sectionTitle ? `${sectionEmoji || ''} ${sectionTitle}`.trim() : null

    if (sectionKey && sectionKey !== currentSection) {
      sections.push({
        type: 'section',
        key: sectionKey,
        label: sectionKey
      })
      currentSection = sectionKey
    } else if (!sectionTitle && currentSection !== null) {
      currentSection = null
    }

    sections.push({
      type: 'article',
      key: article.url,
      article: article,
      index: index
    })
  })

  return sections
})
</script>
```

**React 19: `ArticleList.jsx`**
```javascript
import { useMemo } from 'react'
import ArticleCard from './ArticleCard'

function ArticleList({ articles, onCopySummary }) {
  const sortedArticles = useMemo(() => {
    return [...articles].sort((a, b) => {
      const stateA = a.removed ? 3 : a.tldrHidden ? 2 : a.read?.isRead ? 1 : 0
      const stateB = b.removed ? 3 : b.tldrHidden ? 2 : b.read?.isRead ? 1 : 0

      if (stateA !== stateB) {
        return stateA - stateB
      }

      const orderA = a.originalOrder ?? 0
      const orderB = b.originalOrder ?? 0
      return orderA - orderB
    })
  }, [articles])

  const sectionsWithArticles = useMemo(() => {
    const sections = []
    let currentSection = null

    sortedArticles.forEach((article, index) => {
      const sectionTitle = article.section
      const sectionEmoji = article.sectionEmoji
      const sectionKey = sectionTitle ? `${sectionEmoji || ''} ${sectionTitle}`.trim() : null

      if (sectionKey && sectionKey !== currentSection) {
        sections.push({
          type: 'section',
          key: sectionKey,
          label: sectionKey
        })
        currentSection = sectionKey
      } else if (!sectionTitle && currentSection !== null) {
        currentSection = null
      }

      sections.push({
        type: 'article',
        key: article.url,
        article,
        index
      })
    })

    return sections
  }, [sortedArticles])

  return (
    <div className="article-list">
      {sectionsWithArticles.map((item) => (
        item.type === 'section' ? (
          <div key={item.key} className="section-title">
            {item.label}
          </div>
        ) : (
          <ArticleCard
            key={item.key}
            article={item.article}
            index={item.index}
            onCopySummary={onCopySummary}
          />
        )
      ))}
    </div>
  )
}

export default ArticleList
```

**Changes:**
- Sorting handled with `useMemo`, using article state passed in from `DailyResults`
- No direct `localStorage` access; parent hook keeps the data fresh
- Section assembly remains declarative with memoized derivations

**Note**: The parent subscription ensures article arrays stay current, so this component can stay purely presentational.

---

### 6. ArticleCard Component

**Current: `ArticleCard.vue` (excerpt)**
```vue
<script setup>
import { computed } from 'vue'
import { useArticleState } from '@/composables/useArticleState'
import { useSummary } from '@/composables/useSummary'

const props = defineProps({
  article: { type: Object, required: true },
  index: { type: Number, required: true }
})

const emit = defineEmits(['copy-summary'])

const {
  isRead, isRemoved, isTldrHidden,
  toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden
} = useArticleState(props.article.issueDate, props.article.url)

const summary = useSummary(props.article.issueDate, props.article.url, 'summary')
const tldr = useSummary(props.article.issueDate, props.article.url, 'tldr')

// ... rest of component
</script>
```

**React 19: `ArticleCard.jsx`**
```javascript
import { useArticleState } from '../hooks/useArticleState'
import { useSummary } from '../hooks/useSummary'

function ArticleCard({ article, index, onCopySummary }) {
  const {
    isRead, isRemoved, isTldrHidden,
    toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden
  } = useArticleState(article.issueDate, article.url)

  const summary = useSummary(article.issueDate, article.url, 'summary')
  const tldr = useSummary(article.issueDate, article.url, 'tldr')

  // Card classes (React Compiler auto-memoizes)
  const cardClasses = [
    'article-card',
    !isRead && 'unread',
    isRead && 'read',
    isRemoved && 'removed',
    isTldrHidden && 'tldr-hidden'
  ].filter(Boolean).join(' ')

  // Favicon URL
  const faviconUrl = (() => {
    try {
      const url = new URL(article.url)
      return `${url.origin}/favicon.ico`
    } catch {
      return null
    }
  })()

  const handleLinkClick = (e) => {
    if (isRemoved) return
    if (e.ctrlKey || e.metaKey) return

    e.preventDefault()
    summary.toggle()
    if (!isRead) {
      toggleRead()
    }
  }

  const copyToClipboard = async () => {
    const text = `---
title: ${article.title}
url: ${article.url}
---
${summary.markdown}`

    try {
      await navigator.clipboard.writeText(text)
      onCopySummary()
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleTldrClick = () => {
    if (isRemoved) return

    const wasExpanded = tldr.expanded
    tldr.toggle()

    if (!isRead && tldr.expanded) {
      toggleRead()
    }

    if (wasExpanded && !tldr.expanded) {
      markTldrHidden()
    } else if (tldr.expanded) {
      unmarkTldrHidden()
    }
  }

  return (
    <div className={cardClasses} data-original-order={index}>
      <div className="article-header">
        {/* Article number */}
        <div className="article-number">{index + 1}</div>

        {/* Article link */}
        <div className="article-content">
          <a
            href={article.url}
            className="article-link"
            target="_blank"
            rel="noopener noreferrer"
            data-url={article.url}
            tabIndex={isRemoved ? -1 : 0}
            onClick={handleLinkClick}
          >
            {faviconUrl && (
              <img
                src={faviconUrl}
                className="article-favicon"
                loading="lazy"
                alt=""
                onError={(e) => e.target.style.display = 'none'}
              />
            )}
            <span className="article-link-text">{article.title}</span>
          </a>
        </div>

        {/* Article actions */}
        <div className="article-actions">
          {/* Summary button */}
          <div className="expand-btn-container">
            <button
              className={`article-btn expand-btn ${summary.isAvailable ? 'loaded' : ''} ${summary.expanded ? 'expanded' : ''}`}
              disabled={summary.loading}
              type="button"
              onClick={() => summary.toggle()}
            >
              {summary.buttonLabel}
            </button>
            <button
              className="article-btn expand-chevron-btn"
              type="button"
              title="Choose reasoning effort level"
            >
              ▾
            </button>
          </div>

          {/* TLDR button */}
          <button
            className={`article-btn tldr-btn ${tldr.isAvailable ? 'loaded' : ''} ${tldr.expanded ? 'expanded' : ''}`}
            disabled={tldr.loading}
            type="button"
            onClick={handleTldrClick}
          >
            {tldr.buttonLabel}
          </button>

          {/* Copy button */}
          {summary.isAvailable && (
            <button
              className="article-btn copy-summary-btn visible"
              type="button"
              title="Copy summary"
              onClick={copyToClipboard}
            >
              <svg
                aria-hidden="true"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            </button>
          )}

          {/* Remove/Restore button */}
          <button
            className="article-btn remove-article-btn"
            type="button"
            onClick={toggleRemove}
          >
            {isRemoved ? 'Restore' : 'Remove'}
          </button>
        </div>
      </div>

      {/* Inline summary */}
      {summary.expanded && summary.html && (
        <div className="inline-summary">
          <strong>Summary</strong>
          <div dangerouslySetInnerHTML={{ __html: summary.html }} />
        </div>
      )}

      {/* Inline TLDR */}
      {tldr.expanded && tldr.html && (
        <div className="inline-tldr">
          <strong>TLDR</strong>
          <div dangerouslySetInnerHTML={{ __html: tldr.html }} />
        </div>
      )}
    </div>
  )
}

export default ArticleCard
```

**Changes:**
- `computed()` → inline calculations (React Compiler memoizes)
- `v-if` → `&&` or ternary
- `v-html` → `dangerouslySetInnerHTML` (still sanitized by DOMPurify in `useSummary`)
- `:class` → `className` with conditional logic
- `@click` → `onClick`
- Event emits → callback props

---

## Build System Changes

### 1. Package.json Updates

**Remove:**
```json
{
  "dependencies": {
    "vue": "^3.x.x"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.x.x"
  }
}
```

**Add:**
```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "marked": "^x.x.x",
    "dompurify": "^x.x.x"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^x.x.x",
    "babel-plugin-react-compiler": "^1.0.0",
    "eslint-plugin-react-hooks": "^6.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

### 2. Vite Configuration

**Current: `vite.config.js`**
```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
})
```

**New: `vite.config.js`**
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [
          ['babel-plugin-react-compiler', {
            target: '19'
          }]
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
})
```

### 3. Index.html Updates

**Current:**
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Aggregator</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

**New:**
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Aggregator</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

**Changes:**
- `#app` → `#root` (React convention)
- `main.js` → `main.jsx`

### 4. Entry Point

**Current: `src/main.js`**
```javascript
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

**New: `src/main.jsx`**
```javascript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

### 5. ESLint Configuration

**Add React hooks linting:**

```javascript
// eslint.config.js
import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  js.configs.recommended,
  {
    plugins: {
      'react-hooks': reactHooks
    },
    rules: {
      ...reactHooks.configs.recommended.rules
    }
  }
]
```

### 6. CSS Migration

Vue scoped styles need to become CSS modules or regular CSS:

**Option 1: CSS Modules**
```javascript
// Component.jsx
import styles from './Component.module.css'

function Component() {
  return <div className={styles.container}>...</div>
}
```

**Option 2: Global CSS**
```css
/* All styles in src/App.css or component-specific files */
```

---

## Testing Strategy

### 1. Unit Testing Migration

**Vue Test Utils → React Testing Library**

**Before (Vue):**
```javascript
import { mount } from '@vue/test-utils'
import ArticleCard from '@/components/ArticleCard.vue'

describe('ArticleCard', () => {
  it('marks article as read when clicked', async () => {
    const wrapper = mount(ArticleCard, {
      props: {
        article: { url: 'https://example.com', title: 'Test' },
        index: 0
      }
    })

    await wrapper.find('.article-link').trigger('click')

    expect(wrapper.classes()).toContain('read')
  })
})
```

**After (React):**
```javascript
import { render, screen, fireEvent } from '@testing-library/react'
import ArticleCard from './ArticleCard'

describe('ArticleCard', () => {
  it('marks article as read when clicked', () => {
    const article = { url: 'https://example.com', title: 'Test' }

    render(<ArticleCard article={article} index={0} />)

    const link = screen.getByText('Test')
    fireEvent.click(link)

    expect(link.parentElement).toHaveClass('read')
  })
})
```

### 2. Integration Testing

**Test localStorage sync:**

```javascript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

describe('localStorage sync', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('persists article state to localStorage', async () => {
    render(<App />)

    // Scrape articles
    await userEvent.type(screen.getByLabelText('Start Date'), '2024-01-01')
    await userEvent.type(screen.getByLabelText('End Date'), '2024-01-03')
    await userEvent.click(screen.getByText('Scrape Newsletters'))

    // Wait for results
    await waitFor(() => screen.getByText(/Stats:/))

    // Mark article as read
    const article = screen.getAllByRole('link')[0]
    await userEvent.click(article)

    // Check localStorage
    const stored = JSON.parse(localStorage.getItem('newsletters:scrapes:2024-01-01'))
    expect(stored.articles[0].read.isRead).toBe(true)
  })

})
```

### 3. E2E Testing

No changes needed if using Playwright or Cypress (they interact with DOM, not framework-specific).

### 4. Visual Regression Testing

Use tools like Percy or Chromatic to catch CSS issues during migration.

---

## Implementation Order

### Phase 1: Foundation (Week 1)

**Goal**: Set up React 19 infrastructure and migrate non-state components.

1. **Day 1-2: Setup**
   - Update package.json dependencies
   - Update vite.config.js
   - Update index.html
   - Create src/main.jsx
   - Install React Compiler
   - Configure ESLint

2. **Day 3-4: Core Hooks**
   - Create `hooks/useLocalStorage.js`
   - Create `hooks/useArticleState.js`
   - Create `hooks/useCacheSettings.js`
   - Create `hooks/useScraper.js`
   - Create `hooks/useSummary.js`
   - Write unit tests for each hook

3. **Day 5: Simple Components**
   - Migrate CacheToggle
   - Migrate CSS to CSS modules or global
   - Test localStorage sync

**Checkpoint**: Cache toggle works, localStorage syncs correctly.

---

### Phase 2: Core Components (Week 2)

**Goal**: Migrate main UI components.

1. **Day 1-2: App & ScrapeForm**
   - Migrate App.jsx
   - Migrate ScrapeForm.jsx with controlled submit handling
   - Test scraping flow
   - Test date validation

2. **Day 3: ResultsDisplay**
   - Migrate ResultsDisplay.jsx
   - Test stats display
   - Test debug logs

3. **Day 4-5: ArticleList**
   - Migrate ArticleList.jsx
   - Test sorting logic (CRITICAL)
   - Test storage change reactivity
   - Test section grouping

**Checkpoint**: Can scrape, view results, articles sort correctly.

---

### Phase 3: Complex Features (Week 3)

**Goal**: Migrate article interactions.

1. **Day 1-3: ArticleCard**
   - Migrate ArticleCard.jsx
   - Test read/unread toggle
   - Test remove/restore
   - Test TLDR hidden state
   - Test summary/TLDR fetching

2. **Day 4: Summary Integration**
   - Test markdown rendering
   - Test DOMPurify sanitization
   - Test copy to clipboard

3. **Day 5: Testing & Bug Fixes**
   - Run full integration tests
   - Fix any state sync issues
   - Performance testing

**Checkpoint**: All features work, state syncs correctly.

---

### Phase 4: Polish & Testing (Week 4)

**Goal**: Ensure production readiness.

1. **Day 1-2: E2E Testing**
   - Write comprehensive E2E tests
   - Test cache merge logic
   - Test error handling

2. **Day 3: Performance**
   - Run React Compiler analysis
   - Optimize re-renders
   - Test with large datasets

3. **Day 4: Documentation**
   - Update README
   - Document new patterns
   - Migration notes

4. **Day 5: Deployment**
   - Build for production
   - Test production build
   - Deploy

**Checkpoint**: Production-ready React 19 app.

---

## Risk Mitigation

### Risk 1: localStorage Sync Bugs

**Probability**: HIGH (historical bugs: commit 16bd653, 3bfceee)

**Mitigation:**
1. Use `useSyncExternalStore` for proper React integration
2. Extensive testing of same-tab storage events
3. Test merge logic with edge cases
4. Add logging to detect sync issues early

**Tests:**
- Mark article as read in one component, verify sort in ArticleList
- Mutate localStorage entries and confirm the subscription map notifies consumers
- Test cache merge with partial data

---

### Risk 2: Sorting Regression

**Probability**: MEDIUM

**Mitigation:**
1. Port exact sorting algorithm from Vue
2. Test with various article states
3. Test with large datasets
4. Visual regression testing
5. Compare side-by-side with Vue version

**Tests:**
- Articles in all 4 states (unread, read, tldrHidden, removed)
- Multiple articles with same state (preserve original order)
- Dynamic state changes (mark read, then hide TLDR)

---

### Risk 3: React Compiler Issues

**Probability**: LOW-MEDIUM

**Mitigation:**
1. Keep `useMemo` for complex calculations
2. Test with compiler disabled first
3. Use compiler diagnostics
4. Gradual rollout

---

### Risk 4: CSS Breakage

**Probability**: MEDIUM

**Mitigation:**
1. Keep same class names
2. Use CSS modules for scoping
3. Visual regression testing
4. Test all interactive states

---

### Risk 5: Async State Updates

**Probability**: MEDIUM

**Mitigation:**
1. Use explicit submit handlers and keep storage writes atomic
2. Test race conditions
3. Rapidly toggle article state to exercise subscription updates
4. Test error recovery

**Tests:**
- Rapid clicking (summary, TLDR, remove)
- Slow network simulation
- API errors
- Concurrent updates

---

## Key Insights Summary

### Vue → React Patterns

1. **No Direct `computed()` Equivalent**: React Compiler auto-memoizes, but for effect dependencies, use `useMemo`

2. **No Deep Watchers**: Must explicitly update nested objects with `setState` updater functions

3. **Custom Events → Shared Store**: Replace DOM events with a module-level subscription map exposed through hooks

4. **Reactivity System**: Vue tracks dependencies automatically, React needs explicit subscriptions (`useSyncExternalStore`)

### React 19 Advantages

1. **Controlled forms stay predictable**: Local `useState` keeps async flows explicit, with `useTransition` available if we need to defer UI updates

2. **Compiler > Manual Memoization**: No need to think about `useMemo` / `useCallback` in most cases

3. **Cleaner Code**: Less "magic", more explicit

4. **External stores fit naturally**: `useSyncExternalStore` keeps localStorage-backed state in sync without DOM events

### Critical Gotchas

1. **localStorage Sync**: The shared subscription map must notify every key write; missing it will desync components

2. **Sorting Logic**: Article order depends on up-to-date arrays; ensure parents subscribe per day so lists re-render

3. **Merge Logic**: Easy to forget properties when merging cache (bug #1), be exhaustive

4. **Effect Dependencies**: React Compiler doesn't eliminate useEffect dependencies, be careful

---

## Success Criteria

### Functional
- [ ] All features work identically to Vue version
- [ ] localStorage sync is reliable
- [ ] Article sorting matches Vue behavior
- [ ] Summary/TLDR fetching works
- [ ] Cache merge preserves all user state
- [ ] Error handling is robust

### Performance
- [ ] Initial load ≤ Vue version
- [ ] Re-renders are minimal (React Compiler)
- [ ] Memory usage comparable
- [ ] No layout thrashing

### Code Quality
- [ ] No console errors/warnings
- [ ] ESLint passes
- [ ] TypeScript (if added) compiles
- [ ] Tests pass
- [ ] Code coverage ≥ 80%

### Documentation
- [ ] Migration guide written
- [ ] New patterns documented
- [ ] Breaking changes noted
- [ ] Deployment checklist complete

---

## Conclusion

This migration plan translates TLDRScraper's Vue 3 architecture to React 19 while leveraging modern primitives such as the `use` hook, `useTransition`, and the React Compiler. The most critical aspects are:

1. **localStorage sync** using `useSyncExternalStore`
2. **Article sorting** driven by up-to-date arrays supplied from subscribed parents
3. **Cache merging** with complete property preservation

By following this plan systematically and testing thoroughly, the migration should be smooth and result in a more maintainable, performant application.
