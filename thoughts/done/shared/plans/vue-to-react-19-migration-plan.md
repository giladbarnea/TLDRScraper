---
last-updated: 2025-11-02 06:52, 046336f
created: 2025-10-31
status: draft
---
# Vue 3 to React 19 Migration Plan

## Executive Summary

This document outlines a plan to migrate TLDRScraper from Vue 3 to React 19. The migration uses React 19's `useActionState` for form handling while keeping state management straightforward. The focus is on preserving the existing behavior while simplifying the implementation.

## Table of Contents

1. [Current Vue Architecture Analysis](#current-vue-architecture-analysis)
2. [React 19 State Management Strategy](#react-19-state-management-strategy)
3. [Component-by-Component Migration Map](#component-by-component-migration-map)
4. [Build System Changes](#build-system-changes)

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
| `computed()` | Inline calculations | No memoization needed for simple derivations |
| `computed()` (complex) | `useMemo()` | Only when computation is expensive |
| `watch()` | `useEffect()` | For side effects |
| `useLocalStorage()` deep watch | Custom hook with explicit updates | Need manual sync |

### React 19 Features to Leverage

#### 1. Form Submission with `useActionState`

**Use for:**
- Scrape form submission

**Example:**
```javascript
import { useActionState } from 'react'

function ScrapeForm({ onResults }) {
  const [state, formAction, isPending] = useActionState(
    async (previousState, formData) => {
      try {
        const startDate = formData.get('startDate')
        const endDate = formData.get('endDate')
        const results = await scrapeNewsletters(startDate, endDate)
        onResults(results)
        return { success: true }
      } catch (error) {
        return { success: false, error: error.message }
      }
    },
    { success: true }
  )

  return (
    <form action={formAction}>
      <input name="startDate" type="date" required />
      <input name="endDate" type="date" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Scraping...' : 'Scrape Newsletters'}
      </button>
      {state.error && <div className="error">{state.error}</div>}
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

#### 3. Avoiding Over-Optimization

Use `useMemo` only when calculations are genuinely expensive. For simple derivations (like `statusText = enabled ? '(enabled)' : '(disabled)'`), inline calculations are clearer and sufficient.

### localStorage Sync Solution

**Custom Hook: `useLocalStorage`**

```javascript
import { useState, useEffect } from 'react'

function useLocalStorage(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
    }
  }, [key, value])

  const remove = () => {
    localStorage.removeItem(key)
    setValue(defaultValue)
  }

  return [value, setValue, remove]
}
```

### Article State Management Solution

**Custom Hook: `useArticleState`**

```javascript
function useArticleState(date, url) {
  const storageKey = `newsletters:scrapes:${date}`
  const [payload, setPayload] = useLocalStorage(storageKey, null)

  // Find article in payload
  const article = payload?.articles?.find(a => a.url === url) || null

  // Derived state
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

  return (
    <div className="cache-toggle-container">
      <label className="cache-toggle-label" htmlFor="cacheToggle">
        <input
          id="cacheToggle"
          type="checkbox"
          className="cache-toggle-input"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        <span className="cache-toggle-checkbox" />
        <span className="cache-toggle-text">Cache</span>
        <span className="cache-toggle-status">
          {enabled ? '(enabled)' : '(disabled)'}
        </span>
      </label>
    </div>
  )
}

export default CacheToggle
```

**Changes:**
- `v-model` → `checked` + `onChange`
- Inline status text (no need for separate variable)

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
import { useActionState, useState, useEffect } from 'react'
import { scrapeNewsletters } from '../lib/scraper'

function ScrapeForm({ onResults }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    const today = new Date()
    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)
    setEndDate(today.toISOString().split('T')[0])
    setStartDate(threeDaysAgo.toISOString().split('T')[0])
  }, [])

  const [state, formAction, isPending] = useActionState(
    async (previousState, formData) => {
      const start = formData.get('startDate')
      const end = formData.get('endDate')
      
      const daysDiff = Math.ceil((new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24))
      
      if (new Date(start) > new Date(end)) {
        return { error: 'Start date must be before or equal to end date.' }
      }
      if (daysDiff >= 31) {
        return { error: 'Date range cannot exceed 31 days.' }
      }

      try {
        const results = await scrapeNewsletters(start, end)
        onResults(results)
        return { success: true }
      } catch (err) {
        return { error: err.message }
      }
    },
    { success: false }
  )

  return (
    <div>
      <form action={formAction}>
        <div className="form-group">
          <label htmlFor="startDate">Start Date:</label>
          <input
            id="startDate"
            name="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="endDate">End Date:</label>
          <input
            id="endDate"
            name="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={isPending}>
          {isPending ? 'Scraping...' : 'Scrape Newsletters'}
        </button>
      </form>

      {isPending && (
        <div className="progress">
          <div>Scraping newsletters... This may take several minutes.</div>
        </div>
      )}

      {state.error && (
        <div className="error" role="alert">{state.error}</div>
      )}
    </div>
  )
}

export default ScrapeForm
```

**Changes:**
- Uses `useActionState` for form handling
- Validation moved into action
- `emit('results')` → `onResults(results)` callback prop

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
- `computed()` → inline calculations
- Daily storage sync handled inside `DailyResults` with `useLocalStorage`
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
- Sorting handled with `useMemo`
- No direct `localStorage` access; parent hook keeps the data fresh
- Section assembly remains declarative

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
- `computed()` → inline calculations
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
  plugins: [react()],
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

Convert Vue scoped styles to regular CSS files with component-specific class names.


---

## Key Insights

### Vue → React Patterns

1. **No Direct `computed()` Equivalent**: Use inline calculations for simple derivations, `useMemo` only when expensive

2. **No Deep Watchers**: Must explicitly update nested objects with `setState` updater functions

3. **Reactivity System**: Vue tracks dependencies automatically, React needs explicit state updates

### React 19 Advantages

1. **`useActionState` for forms**: Handles pending/error states automatically, cleaner than manual state management

2. **Cleaner Code**: Less "magic", more explicit

3. **Simpler mental model**: State flows in one direction

### Critical Gotchas

1. **localStorage Sync**: Must trigger re-renders when localStorage changes

2. **Sorting Logic**: Article order depends on current state from localStorage

3. **Merge Logic**: Easy to forget properties when merging cache (historical bug in commit 3bfceee), be exhaustive
