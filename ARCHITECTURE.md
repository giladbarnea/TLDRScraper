# TLDR Scraper Architecture

**Post-Migration Vue.js Architecture (Phases 1-5)**

---

## Executive Summary

The TLDR Scraper operates as a **browser-first application** where the browser is the single source of truth for all persistent state. After migrating from vanilla JavaScript to Vue 3, the core architecture philosophy remains unchanged: all newsletter data, article metadata, summary/TLDR results, and read state live exclusively in `localStorage`. The backend is stateless, serving only as a proxy for scraping and LLM requests.

**Key Architecture Decision**: The migration adopts **composables + localStorage** as the state management solution instead of Pinia/Vuex. This keeps state tightly coupled with storage persistence and eliminates unnecessary abstraction layers.

---

## Table of Contents

1. [Component Architecture](#component-architecture)
2. [State Management & Mutations](#state-management--mutations)
3. [Vue.js Integration Patterns](#vuejs-integration-patterns)
4. [Client Storage Flows](#client-storage-flows)
5. [API Layer](#api-layer)
6. [Migration Comparison](#migration-comparison)

---

## Component Architecture

### Component Hierarchy

```
App.vue (Root)
  ├── CacheToggle.vue          (Settings control)
  ├── ScrapeForm.vue           (Input & triggering)
  └── ResultsDisplay.vue       (Results container)
        └── ArticleList.vue    (Articles by date → section → article)
              └── ArticleCard.vue (Individual article + inline summary/TLDR)
```

### Component Reference

| Component | Path | Responsibility |
|-----------|------|----------------|
| **App.vue** | `client/src/App.vue` | Root component; hydration on mount; top-level state |
| **CacheToggle.vue** | `client/src/components/CacheToggle.vue` | Cache enabled/disabled toggle; persists to localStorage |
| **ScrapeForm.vue** | `client/src/components/ScrapeForm.vue` | Date range input; validation; scraping API trigger |
| **ResultsDisplay.vue** | `client/src/components/ResultsDisplay.vue` | Groups articles by date; renders issues; stats display |
| **ArticleList.vue** | `client/src/components/ArticleList.vue` | Sorts articles by state (unread→read→removed); groups by section |
| **ArticleCard.vue** | `client/src/components/ArticleCard.vue` | Individual article UI; summary/TLDR toggles; read/remove actions |

### Component Details

#### App.vue - Root Container
- **Entry point**: Creates Vue app instance and manages top-level results
- **Hydration**: On mount, loads cached data for default range (3 days ago → today)
- **Data flow**: Receives scrape results from `ScrapeForm` via emit, passes to `ResultsDisplay`

```javascript
// App.vue:11-25
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
```

#### CacheToggle.vue - Settings Control
- **Purpose**: Toggle cache on/off
- **State**: `enabled` (reactive ref managed by `useCacheSettings` composable)
- **Storage**: Persists to `cache:enabled` key in localStorage
- **Effect**: When disabled, subsequent scrapes bypass cache merge

#### ScrapeForm.vue - Input & Triggering
- **Purpose**: Date range input, validation, triggering scrapes
- **Validation**: 31-day limit; start ≤ end; real-time feedback via computed
- **API trigger**: `@submit` → calls `useScraper.scrape()` → emits `results`
- **UX**: Default dates set on mount (3 days ago to today)

#### ResultsDisplay.vue - Results Container
- **Purpose**: Display scrape results; organize by date and issue category
- **Computed**: Groups articles by date; builds stats display
- **Children**: Renders `ArticleList` for each issue category
- **Features**: Copy-to-clipboard toast; collapsible debug logs

#### ArticleList.vue - List Organizer
- **Purpose**: Sort articles by read state; group by section
- **Algorithm**: Unread first → Read → Removed (preserving original order within each group)
- **Computed**: `sortedArticles` (by state + order); `sectionsWithArticles` (group by section)

```javascript
// ArticleList.vue:15-19
function getArticleState(article) {
  if (article.removed) return 2     // Removed articles last
  if (article.read?.isRead) return 1 // Read articles middle
  return 0                           // Unread articles first
}
```

#### ArticleCard.vue - Article Item
- **Purpose**: Render single article; manage summary/TLDR; handle read/remove actions
- **Composables**: `useArticleState()`, `useSummary(type='summary')`, `useSummary(type='tldr')`
- **Features**:
  - Link click: Prevent default, expand summary, mark as read
  - Copy-to-clipboard with YAML front matter
  - Remove/Restore toggle
  - Inline summary/TLDR with markdown rendering

```javascript
// ArticleCard.vue:48-56
function handleLinkClick(e) {
  if (isRemoved.value) return
  if (e.ctrlKey || e.metaKey) return  // Allow cmd/ctrl+click
  e.preventDefault()
  summary.toggle()
  if (!isRead.value) {
    toggleRead()
  }
}
```

---

## State Management & Mutations

### Why Composables Instead of Pinia?

The architecture chooses **composables + localStorage** over Pinia/Vuex because:
- Pinia solves global state sharing across unrelated components
- This app has **linear data flow**: App → ScrapeForm → scrape → localStorage → ResultsDisplay → ArticleCard
- All state mutation is tightly coupled with storage persistence
- Composables are simpler, smaller, and don't add abstraction layers

### The Pattern

1. Composable creates reactive refs with `ref()`
2. Composable uses `useLocalStorage()` to persist/hydrate
3. Component uses composable to access state and mutation methods
4. Mutations directly update refs
5. Vue's reactivity + deep watchers automatically sync ref changes to localStorage

### State Shape

#### Persistent Storage Keys

```javascript
// Key: 'newsletters:scrapes:<ISO-date>'
{
  "date": "2024-10-29",
  "cachedAt": "2024-10-29T15:30:45.123Z",
  "articles": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "issueDate": "2024-10-29",
      "category": "TLDR Tech",
      "section": "Headlines",
      "sectionEmoji": "🚀",
      "sectionOrder": 1,
      "newsletterType": "tech",
      "removed": false,

      "summary": {
        "status": "unknown|creating|available|error",
        "markdown": "## Summary\n...",
        "effort": "low",
        "checkedAt": "2024-10-29T15:35:00.000Z",
        "errorMessage": null
      },

      "tldr": {
        "status": "unknown|creating|available|error",
        "markdown": "## TLDR\n...",
        "effort": "low",
        "checkedAt": null,
        "errorMessage": null
      },

      "read": {
        "isRead": false,
        "markedAt": null
      }
    }
  ],
  "issues": [
    {
      "date": "2024-10-29",
      "category": "TLDR Tech",
      "newsletterType": "tech",
      "title": "TLDR Tech Daily #123",
      "subtitle": "October 29, 2024",
      "sections": [...]
    }
  ]
}

// Key: 'cache:enabled'
// Value: boolean (true/false)
```

### Composable Reference

#### useLocalStorage.js
**Path**: `client/src/composables/useLocalStorage.js`

**Purpose**: Reactive localStorage binding - the backbone of the reactivity model

```javascript
export function useLocalStorage(key, defaultValue) {
  // 1. Initialize from storage or use default
  const data = ref(readFromStorage(key, defaultValue))

  // 2. Watch for changes and persist
  watch(
    data,
    (newValue) => {
      try {
        localStorage.setItem(key, JSON.stringify(newValue))
      } catch (error) {
        console.error(`Failed to persist to localStorage: ${error.message}`)
      }
    },
    { deep: true }  // Watch nested objects/arrays - this is critical!
  )

  return { data, clear }
}
```

**Key Pattern**: `deep: true` watcher means any nested property change triggers persistence. This eliminates the need for explicit write calls.

#### useCacheSettings.js
**Path**: `client/src/composables/useCacheSettings.js`

**Purpose**: Manage cache enabled/disabled setting

```javascript
export function useCacheSettings() {
  const { data: enabled } = useLocalStorage('cache:enabled', true)

  const statusText = computed(() =>
    enabled.value ? '(enabled)' : '(disabled)'
  )

  function toggle() {
    enabled.value = !enabled.value
  }

  return { enabled, statusText, toggle }
}
```

#### useArticleState.js
**Path**: `client/src/composables/useArticleState.js`

**Purpose**: Manage individual article state (read/removed)

```javascript
export function useArticleState(date, url) {
  const storageKey = `newsletters:scrapes:${date}`
  const { data: payload } = useLocalStorage(storageKey, null)

  // Find the article in the payload
  const article = computed(() => {
    if (!payload.value?.articles) return null
    return payload.value.articles.find(a => a.url === url)
  })

  const isRead = computed(() => article.value?.read?.isRead ?? false)
  const isRemoved = computed(() => Boolean(article.value?.removed))

  // Mutation methods - directly update the article object
  function markAsRead() {
    if (!article.value) return
    article.value.read = {
      isRead: true,
      markedAt: new Date().toISOString()
    }
  }

  function toggleRead() {
    isRead.value ? markAsUnread() : markAsRead()
  }

  function setRemoved(removed) {
    if (!article.value) return
    article.value.removed = Boolean(removed)
  }

  return { article, isRead, isRemoved, markAsRead, markAsUnread, toggleRead, setRemoved }
}
```

**Critical Detail**: Mutations directly modify `article.value` properties. Because `payload` is a ref being watched with `deep: true`, changes cascade automatically to localStorage without explicit write calls.

#### useSummary.js
**Path**: `client/src/composables/useSummary.js`

**Purpose**: Manage summary/TLDR fetch, cache, and rendering

```javascript
export function useSummary(date, url, type = 'summary') {
  const { article } = useArticleState(date, url)
  const loading = ref(false)
  const expanded = ref(false)

  const data = computed(() => article.value?.[type])
  const status = computed(() => data.value?.status || 'unknown')
  const markdown = computed(() => data.value?.markdown || '')

  // Convert markdown to sanitized HTML
  const html = computed(() => {
    if (!markdown.value) return ''
    try {
      const rawHtml = marked.parse(markdown.value)
      return DOMPurify.sanitize(rawHtml)
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return ''
    }
  })

  const isAvailable = computed(() => status.value === 'available' && markdown.value)
  const isLoading = computed(() => status.value === 'creating' || loading.value)

  // Fetch from API
  async function fetch(summaryEffort = 'low') {
    if (!article.value) return

    loading.value = true

    // Update status to creating
    if (!article.value[type]) {
      article.value[type] = {}
    }
    article.value[type].status = 'creating'  // Persisted immediately

    const endpoint = type === 'summary' ? '/api/summarize-url' : '/api/tldr-url'

    try {
      const response = await window.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, summary_effort: summaryEffort })
      })

      const result = await response.json()

      if (result.success) {
        article.value[type] = {
          status: 'available',
          markdown: result[`${type}_markdown`] || '',
          effort: summaryEffort,
          checkedAt: new Date().toISOString(),
          errorMessage: null
        }
        expanded.value = true
      } else {
        article.value[type].status = 'error'
        article.value[type].errorMessage = result.error || `Failed to fetch ${type}`
      }
    } catch (error) {
      article.value[type].status = 'error'
      article.value[type].errorMessage = error.message
    } finally {
      loading.value = false
    }
  }

  // Toggle expanded state or fetch if not available
  function toggle(summaryEffort) {
    if (isAvailable.value) {
      expanded.value = !expanded.value
    } else {
      fetch(summaryEffort)
    }
  }

  return {
    status, markdown, html, loading: isLoading, expanded,
    isAvailable, fetch, toggle
  }
}
```

**State Machine**:
```
Status transitions:
  unknown
    ↓ (user clicks Summarize)
  creating (API call in progress, status persisted to storage)
    ↓
  available (markdown received, stored)
    or
  error (API failed, errorMessage stored)
    ↓ (user clicks Retry)
  creating (retry request)
```

#### useScraper.js
**Path**: `client/src/composables/useScraper.js`

**Purpose**: Handle scraping API calls, cache checks, and merging

Key features:
- **Cache-aware**: Checks if date range is fully cached before hitting API
- **Merge logic**: Preserves user state (summary/tldr/read) across re-scrapes
- **Progress tracking**: Updates `progress` ref for UI feedback
- **Normalization**: Converts API response into daily payloads with canonical article shape

```javascript
export function useScraper() {
  const loading = ref(false)
  const error = ref(null)
  const progress = ref(0)

  const { enabled: cacheEnabled } = useCacheSettings()

  // Main scrape function
  async function scrape(startDate, endDate) {
    error.value = null
    loading.value = true
    progress.value = 0

    try {
      // Check if fully cached
      if (isRangeCached(startDate, endDate)) {
        const cached = loadFromCache(startDate, endDate)
        if (cached) {
          progress.value = 100
          return cached
        }
      }

      // Call API
      progress.value = 50
      const response = await window.fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: startDate, end_date: endDate })
      })

      const data = await response.json()

      if (data.success) {
        const payloads = buildDailyPayloadsFromScrape(data)

        // Merge with cache if enabled
        const mergedPayloads = cacheEnabled.value
          ? mergeWithCache(payloads)
          : payloads

        progress.value = 100
        return {
          success: true,
          payloads: mergedPayloads,
          source: 'Live scrape',
          stats: data.stats
        }
      }
    } catch (err) {
      error.value = err.message
      return null
    } finally {
      loading.value = false
    }
  }

  return { loading, error, progress, scrape, isRangeCached, loadFromCache }
}
```

### State Mutation Summary

**Type 1: Article State** (via `useArticleState`)
- `markAsRead()` → updates article.read.isRead and markedAt
- `markAsUnread()` → resets read state
- `toggleRead()` → switches between read/unread
- `setRemoved()` → marks article as removed/restored

**Type 2: Summary State** (via `useSummary`)
- `fetch()` → sets status='creating' → API call → status='available'|'error'
- `toggle()` → expands/collapses inline view or initiates fetch
- Auto-persists via article's reactive properties

**Type 3: Cache Settings** (via `useCacheSettings`)
- `toggle()` → flips cache:enabled boolean

**Type 4: Scraper State** (via `useScraper`)
- `scrape()` → checks cache → API call → merges with stored data → updates storage

---

## Vue.js Integration Patterns

### Reactivity Model

**Core Pattern**: Vue 3 Composition API + deep watchers + localStorage

```javascript
// 1. Initialize ref from storage
const data = ref(readFromStorage(key, defaultValue))

// 2. Watch for changes and persist
watch(data, (newValue) => {
  localStorage.setItem(key, JSON.stringify(newValue))
}, { deep: true })

// 3. Component updates ref → Vue updates DOM → watcher fires → storage updated
```

### Component Lifecycle Usage

#### App.vue - Hydration on Mount
```javascript
// App.vue:11-25
onMounted(() => {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  const endDate = today.toISOString().split('T')[0]
  const startDate = threeDaysAgo.toISOString().split('T')[0]

  // Load from cache for default date range
  const cached = loadFromCache(startDate, endDate)
  if (cached) {
    results.value = cached
  }
})
```

### Props/Emits Patterns

#### Props Flow (Parent → Child)
```
App.vue
  ↓ props: results
ResultsDisplay.vue
  ↓ props: articles
ArticleList.vue
  ↓ props: article
ArticleCard.vue
```

#### Emits Flow (Child → Parent)
```javascript
// ScrapeForm.vue → App.vue
const emit = defineEmits(['results'])
emit('results', results)

// App.vue
<ScrapeForm @results="handleResults" />
```

### Computed Properties

Computed properties derive UI state from article state:

```javascript
// useSummary.js
const html = computed(() => {
  if (!markdown.value) return ''
  try {
    const rawHtml = marked.parse(markdown.value)
    return DOMPurify.sanitize(rawHtml)
  } catch (error) {
    return ''
  }
})

// useArticleState.js
const isRead = computed(() => article.value?.read?.isRead ?? false)
const isRemoved = computed(() => Boolean(article.value?.removed))
```

### Event Handling Patterns

**ArticleCard.vue - Link Click with Multiple Side Effects**:
```javascript
// ArticleCard.vue:48-56
function handleLinkClick(e) {
  if (isRemoved.value) return
  if (e.ctrlKey || e.metaKey) return  // Allow cmd/ctrl+click
  e.preventDefault()
  summary.toggle()  // Expand summary
  if (!isRead.value) {
    toggleRead()  // Mark as read
  }
}
```

### Conditional Styling

```javascript
// ArticleCard.vue
const cardClasses = computed(() => ({
  'article-card': true,
  'unread': !isRead.value,
  'read': isRead.value,
  'removed': isRemoved.value
}))
```

```html
<div :class="cardClasses">
```

### Markdown Rendering

```javascript
// useSummary.js
const html = computed(() => {
  if (!markdown.value) return ''
  const rawHtml = marked.parse(markdown.value)
  return DOMPurify.sanitize(rawHtml)
})
```

```html
<!-- ArticleCard.vue -->
<div v-html="summary.html.value" />
```

---

## Client Storage Flows

### High-Level Flow Architecture

```
User Action (click, form submit)
  ↓
Component Event Handler
  ↓
Composable Method
  ↓
Mutation to Reactive Ref
  ↓
Vue Deep Watcher
  ↓
localStorage.setItem()
  ↓
UI Auto-Updates (via computed/reactivity)
```

### Flow A: Initial App Load & Hydration

```
User navigates to app
  ↓
main.js creates Vue app
  ↓
App.vue mounts
  ↓
onMounted() executes:
  • Compute default range: 3 days ago → today
  • Call useScraper.loadFromCache(startDate, endDate)
    └─ For each date in range:
        • Try localStorage.getItem('newsletters:scrapes:<date>')
        • Parse JSON
        • Return merged payloads
  ↓
If cached data found:
  • results.value = cached data
  ↓
Template renders ResultsDisplay
  • ArticleList → ArticleCard for each article
  ↓
UI shows cached data without network call (time to interactive: ~100ms)
```

### Flow B: User Triggers Scrape

```
User sets date range and clicks "Scrape Newsletters"
  ↓
ScrapeForm.handleSubmit()
  ↓
Calls useScraper.scrape(startDate, endDate)
  ├─ Sets loading.value = true
  ├─ Sets progress.value = 0
  ↓
Check if range is fully cached:
  useScraper.isRangeCached(startDate, endDate)
  ├─ If cacheEnabled.value === false → skip cache
  ├─ Check localStorage for each date
  ↓
If range IS cached:
  • loadFromCache() → returns payloads
  • progress.value = 100
  • Return cached data
  ↓
If range NOT cached:
  • progress.value = 50
  • POST /api/scrape { start_date, end_date }
  ↓
  Build daily payloads from response:
    • Group articles and issues by date
    • Initialize each article with:
      summary: { status: 'unknown', ... }
      tldr: { status: 'unknown', ... }
      read: { isRead: false, ... }
  ↓
  If cacheEnabled === true:
    mergeWithCache(payloads):
      • For each payload:
        • Get useLocalStorage('newsletters:scrapes:<date>')
        • If cached:
          └─ Merge: keep new metadata, preserve stored summary/tldr/read
        • Else:
          └─ Create new
        • Update triggers deep watcher → localStorage persisted
  ↓
  progress.value = 100
  ↓
ScrapeForm emits 'results' event
  ↓
App.vue.results.value = results
  ↓
ResultsDisplay renders articles
```

### Flow C: User Marks Article as Read

```
User clicks article link or summary button
  ↓
ArticleCard.handleLinkClick() / summary.toggle()
  ↓
Calls useArticleState.toggleRead()
  ↓
markAsRead():
  article.value.read = {
    isRead: true,
    markedAt: new Date().toISOString()
  }
  ↓
Because article is part of payload (deep-watched ref):
  ↓
useLocalStorage watcher fires:
  localStorage.setItem('newsletters:scrapes:<date>', JSON.stringify(payload))
  ↓
Storage updated with new read state
  ↓
ArticleCard's computed isRead.value becomes true
  ↓
Template updates:
  • cardClasses applies 'read' class
  • article-link text color becomes muted
  ↓
ArticleList re-sorts articles:
  • Article moves from unread → read section
```

### Flow D: User Requests Summary

```
User clicks "Summarize" button
  ↓
ArticleCard calls useSummary.toggle()
  ├─ If isAvailable.value === true:
  │   └─ Expand/collapse inline view
  └─ Else:
     └─ Call fetch()
  ↓
useSummary.fetch(summaryEffort):
  ├─ loading.value = true
  ├─ article.value[type].status = 'creating'
  │   (Deep watcher → localStorage updated immediately)
  ↓
  POST /api/summarize-url { url, summary_effort }
    ↓
    Response: { success, summary_markdown, ... }
  ↓
  If success:
    • article.value.summary = {
        status: 'available',
        markdown: result.summary_markdown,
        ...
      }
    • expanded.value = true
  Else:
    • article.value.summary.status = 'error'
    • article.value.summary.errorMessage = error
  ↓
  (Deep watcher fires again → persists updated summary)
  ↓
  loading.value = false
  ↓
Computed updates:
  • html = marked.parse(markdown) + DOMPurify.sanitize()
  • buttonLabel changes to "Available"/"Hide"
  ↓
ArticleCard template renders inline-summary:
  <div v-if="summary.expanded && summary.html">
    <div v-html="summary.html.value" />
  </div>
  ↓
Copy button becomes visible
  ↓
If user clicks summary again:
  • toggle() just expands/collapses (no API call)
  • Content already cached
```

### Flow E: Cache Toggle

```
User clicks cache toggle checkbox
  ↓
CacheToggle.vue (v-model bound to enabled)
  ↓
useCacheSettings.toggle():
  enabled.value = !enabled.value
  ↓
useLocalStorage watcher fires:
  localStorage.setItem('cache:enabled', JSON.stringify(false))
  ↓
CacheToggle displays: "(disabled)"
  ↓
Next scrape uses this setting:
  • If cache disabled:
    └─ isRangeCached() returns false
    └─ Always hits /api/scrape
    └─ Fresh data doesn't merge (overwrites)
```

### Complete Data Flow Diagram

```
┌────────────────────────────────────────────────────────────┐
│                   TLDR Scraper Data Flow                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ USER INTERFACE LAYER                                 │ │
│  │                                                      │ │
│  │  CacheToggle  ScrapeForm  ResultsDisplay  ArticleCard │
│  │      │            │              │              │   │ │
│  │      └────────────┴──────────────┴──────────────┘   │ │
│  │               Emits/Props data flow                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                            ↓                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ COMPOSABLE LAYER (State Logic)                       │ │
│  │                                                      │ │
│  │  useArticleState  useSummary  useScraper            │ │
│  │         │              │            │                │ │
│  │    Mutations:     Mutations:   Mutations:           │ │
│  │    • toggleRead   • fetch()    • scrape()           │ │
│  │    • setRemoved   • toggle()   • mergeWithCache     │ │
│  │         │              │            │                │ │
│  │         └──────────────┴────────────┘                │ │
│  │                        │                             │ │
│  │    All consume useLocalStorage(key, defaultValue)   │ │
│  └──────────────────────────────────────────────────────┘ │
│                            ↓                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ REACTIVITY LAYER (useLocalStorage)                   │ │
│  │                                                      │ │
│  │  ref(readFromStorage(key, defaultValue))            │ │
│  │         │                                            │ │
│  │  watch(data, (newValue) => {                        │ │
│  │    localStorage.setItem(key, JSON.stringify(val))   │ │
│  │  }, { deep: true })                                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                            ↓                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ PERSISTENT STORAGE LAYER                             │ │
│  │                                                      │ │
│  │  localStorage:                                       │ │
│  │  • 'cache:enabled' → boolean                         │ │
│  │  • 'newsletters:scrapes:2024-10-29' → Payload       │ │
│  │  • 'newsletters:scrapes:2024-10-28' → Payload       │ │
│  │                                                      │ │
│  │  JSON serialization ←→ deserialization               │ │
│  └──────────────────────────────────────────────────────┘ │
│                            ↓                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ API LAYER (When not fully cached)                    │ │
│  │                                                      │ │
│  │  POST /api/scrape       → articles, issues, stats    │ │
│  │  POST /api/summarize-url → summary_markdown          │ │
│  │  POST /api/tldr-url     → tldr_markdown              │ │
│  │                                                      │ │
│  │  Backend is stateless; all state lives in browser   │ │
│  └──────────────────────────────────────────────────────┘ │
│                            ↓                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ EXTERNAL SERVICES                                    │ │
│  │                                                      │ │
│  │  • TLDR newsletter scraping                          │ │
│  │  • OpenAI API (summary/TLDR generation)              │ │
│  │  • Web scraping (URL content fetch)                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## API Layer

### HTTP Surface

| Route | Method | Handler | Purpose |
|-------|--------|---------|---------|
| `/` | GET | `serve.index` | Serves Vue app |
| `/api/scrape` | POST | `serve.scrape_newsletters_in_date_range` | Scrapes newsletters for date range |
| `/api/prompt` | GET | `serve.get_summarize_prompt_template` | Returns summarize prompt |
| `/api/summarize-url` | POST | `serve.summarize_url` | Generates article summary |
| `/api/tldr-url` | POST | `serve.tldr_url` | Generates article TLDR |

### Request/Response Contracts

#### POST /api/scrape

**Request**:
```json
{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD"
}
```

**Response**:
```json
{
  "success": true,
  "articles": [
    {
      "url": "https://...",
      "title": "Example (2 minute read)",
      "date": "2024-10-29",
      "category": "TLDR Tech",
      "removed": false,
      "section_title": "Headlines",
      "section_emoji": "🚀",
      "section_order": 1,
      "newsletter_type": "tech"
    }
  ],
  "issues": [...],
  "stats": {
    "total_articles": 42,
    "unique_urls": 40,
    "dates_processed": 1,
    "debug_logs": [...]
  }
}
```

#### POST /api/summarize-url

**Request**:
```json
{
  "url": "https://...",
  "summary_effort": "minimal|low|medium|high"
}
```

**Response**:
```json
{
  "success": true,
  "summary_markdown": "## Summary\n...",
  "canonical_url": "https://...",
  "summary_effort": "low"
}
```

#### POST /api/tldr-url

Same shape as `/api/summarize-url`, but response field is `tldr_markdown`.

---

## Migration Comparison

### What Changed

| Aspect | Vanilla JS | Vue.js Composables |
|--------|-----------|-------------------|
| **State container** | `ClientStorage` wrapper + DOM attributes | Composable refs + reactive objects |
| **Persistence** | Explicit `writeDay()`/`updateArticle()` calls | Automatic via `watch(..., { deep: true })` |
| **Mutations** | Functional updates + DOM re-rendering | Direct property assignment + Vue reactivity |
| **Read tracking** | `markArticleAsRead()` → `updateArticle()` → `reapplyArticleState()` | `toggleRead()` → automatic sync |
| **Summary fetching** | `SummaryDelivery.bindSummaryExpansion()` + DOM events | `useSummary.fetch()` + v-on:click |
| **Error handling** | Status flags in DOM attributes | Status flags in ref, computed labels |
| **State shape** | Article/Issue objects in localStorage | Same (backward compatible) |
| **Lines of code** | ~500+ lines vanilla JS modules | ~300 lines across composables |

### What Didn't Change

- **Browser as single source of truth** ✓
- **No server-side state** ✓
- **localStorage as persistent medium** ✓
- **Article status machine** (unknown → creating → available/error) ✓
- **Read/unread tracking** ✓
- **Summary/TLDR fetch logic** ✓
- **API contracts** ✓
- **Markdown rendering** (marked + DOMPurify) ✓

### Architecture Advantages

The Vue.js version is:
- **Smaller**: ~300 lines composables vs ~500+ lines vanilla JS
- **More readable**: Declarative templates vs imperative DOM manipulation
- **More maintainable**: Clear separation - composables (logic) vs components (UI)
- **More reactive**: Change data → UI auto-updates (no manual DOM sync)
- **Better for onboarding**: Vue patterns are industry standard

### Key Insights

#### 1. State Management via Composables + localStorage

The architecture chooses **composables over Pinia** because state is tightly coupled with persistence and the app has linear data flow.

#### 2. Deep Watchers as the Persistence Layer

All state changes go through `watch(data, ..., { deep: true })`. **Any nested mutation automatically persists to localStorage without explicit write calls**.

#### 3. Computed Properties Bridge State and UI

Articles stored in localStorage → Loaded into refs → Computed properties derive UI state → Template uses computed → Automatic re-render when values change.

#### 4. Reactive Refs Don't Need Explicit Syncing

**Old code**: `updateArticle()` → `writeDay()` → `reapplyArticleState()` → update DOM

**New code**: `article.value.read = {...}` → Vue detects change → watcher fires → storage updated → computed re-evaluates → template auto-updates

#### 5. Storage Contract is Backward Compatible

App boots → hydrates from localStorage → uses same keys/shapes as old code → can seamlessly read/write cached data from vanilla JS era.

---

## File Reference

### Vue Components
- `client/src/App.vue` - Root container, hydration
- `client/src/components/CacheToggle.vue` - Cache toggle control
- `client/src/components/ScrapeForm.vue` - Date range input & scraping
- `client/src/components/ResultsDisplay.vue` - Results container
- `client/src/components/ArticleList.vue` - Article list organizer
- `client/src/components/ArticleCard.vue` - Individual article UI

### Composables (State Management)
- `client/src/composables/useLocalStorage.js` - Reactive localStorage binding
- `client/src/composables/useCacheSettings.js` - Cache toggle state
- `client/src/composables/useArticleState.js` - Individual article state
- `client/src/composables/useSummary.js` - Summary/TLDR fetching
- `client/src/composables/useScraper.js` - Scraper orchestration

### Entry Points
- `client/src/main.js` - Vue app bootstrap
- `client/index.html` - HTML template
- `client/vite.config.js` - Build configuration

### Backend
- `serve.py` - Flask HTTP server
- `tldr_app.py` - Application facade
- `tldr_service.py` - Service layer
- `newsletter_scraper.py` - Newsletter scraping
- `summarizer.py` - Summary/TLDR generation

---

## Conclusion

The Vue.js migration preserves the proven storage architecture while modernizing the UI and state management. The result is cleaner, more maintainable code that follows Vue 3 best practices while keeping the browser-centric, localStorage-backed persistence model that makes the app resilient and performant.

**The four pillars**:

1. **Components** render the UI declaratively
2. **Composables** manage state logic and mutations
3. **localStorage + Deep Watchers** automatically persist all changes
4. **API Layer** provides fresh data when cache misses

This architecture is well-suited for continued feature development and provides a solid foundation for future enhancements like offline support, multi-tab sync, or more advanced state management if needed.
