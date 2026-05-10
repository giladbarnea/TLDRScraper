---
last_updated: 2026-05-06 19:47
companion_to: unified-feed-read-model-plan.md
---

# Unified Feed Read Model — Concrete Todos

Read in tandem with `unified-feed-read-model-plan.md`. This file zooms one level in: file paths, function signatures, store shapes, and the concrete migration order. The plan owns the *why*; this file owns the *what* and *where*.

## Identity

```ts
type ArticleKey = string  // `${date}::${url}`

function articleKey(date: string, url: string): ArticleKey
function parseArticleKey(key: ArticleKey): { date: string, url: string }
```

Every public store API takes `ArticleKey`. Components only build it via `articleKey(date, url)` or receive it from a store selector. URL is no longer a global lookup key.

## Store Shape (`store/articleStore.js`)

```ts
type LoadStatus = 'idle' | 'fetching' | 'cached' | 'ready' | 'error'

type FeedState = {
  startDate: string | null
  endDate: string | null
  status: LoadStatus
  stats: { /* freshResults.stats */ } | null
  error: string | null
  visibleDates: string[]   // ordered ascending; mirrors keys of daysByDate
}

type DaySlice = {
  date: string
  issues: Issue[]
  digest: SummaryData | null
  storage_updated_at: string | null
  articleKeys: ArticleKey[]   // ordered as the payload defines
}

type ArticleSlice = {
  // server-origin (set by ingestion, never mutated by client actions)
  url: string
  title: string
  articleMeta: string
  issueDate: string
  category: string
  sourceId: string
  section?: string
  sectionEmoji?: string
  sectionOrder?: number
  newsletterType?: string
  originalOrder: number

  // client-owned mutable
  read?: { isRead: boolean, markedAt: string | null }
  removed?: boolean
  summary?: SummaryData | null
  expandedView: boolean
  selected: boolean
}

// Module-private state:
const feed: FeedState
const daysByDate: Map<string, DaySlice>
const articlesByKey: Map<ArticleKey, ArticleSlice>
const expandedContainerIds: Set<string>           // already exists, keep
const suppressNextShortPress: { id, untilMs }     // already exists, keep
```

Removed module state (was authority, becomes obsolete):
- `urlToArticleKey`
- `hydratedDates` (replaced by `daysByDate.has(date)`)
- `dayArticleSummaries`
- `dayArticleSummaryListeners`

## Listener Channels

Keep the small set; collapse the noisy ones:

```ts
articleListeners:   Map<ArticleKey, Set<() => void>>
dayListeners:       Map<string, Set<() => void>>      // any change in DaySlice OR its articles
feedListeners:      Set<() => void>                    // FeedState changes
selectedListeners:  Set<() => void>                    // selection set changes
containerListeners: Map<string, Set<() => void>>       // expansion (unchanged)
```

Note: `dayListeners` subsumes the previous `dayLifecycleListeners` and `dayArticleSummaryListeners`. A day-level lifecycle/inventory change fires `notifyDay(date)` once and any per-article notifications it implies. Group-level UI subscribes to the day, derives its own slice.

## Ingestion API (single boundary)

```ts
/**
 * Single ingestion path for any payload coming from Supabase, scrape, or server-confirmed mutation.
 * Upserts dates and articles; replaces day inventory order; preserves client-owned mutable fields.
 * Notifies article and day subscribers exactly once per affected key.
 */
export function ingestFeedPayloads(payloads: DailyPayload[]): void

/**
 * Ingest a single day. Same semantics as ingestFeedPayloads([payload]).
 * Used by the mutation queue after server-confirmed writes.
 */
export function ingestDayPayload(payload: DailyPayload): void
```

Removed exports:
- `hydrateDay`
- `mergeDayFromServer`
- `replaceDayFromServer`
- `composePayloadFromStore` (callers move to `composeDayPayloadForServer`, internal-only)

Added internal helpers:
```ts
function upsertArticle(date, article, originalOrder): { key, changedFields }
function diffDayInventory(date, nextKeys): { stale: ArticleKey[] }
function pruneSelectionForStaleArticles(staleKeys): { delta: number }
```

Merge policy (already documented in plan §"Ingestion Boundary"):
- Server-origin fields from `SERVER_ORIGIN_FIELDS` overwrite.
- `read`, `removed`, `summary`, `expandedView`, `selected` survive when the article key existed.
- New articles get default mutable values.

`feedMerge.js` — keep `SERVER_ORIGIN_FIELDS` constant; inline the merge into the store and delete `mergePreservingLocalState` once `dailyPayloadMutations.js` no longer composes payloads via the legacy path. (Step happens in migration phase 7.)

## Feed Status & Visible Dates

```ts
export function setFeedStatus(patch: Partial<FeedState>): void
export function setFeedRange(startDate: string, endDate: string): void
export function setFeedError(message: string): void
export function clearFeed(): void   // resets to idle (only for explicit reset; not used by reload)

export function useFeedStatus(): {
  status: LoadStatus
  startDate: string | null
  endDate: string | null
  stats: any | null
  error: string | null
}

export function useVisibleDates(): string[]
```

`visibleDates` is recomputed inside the ingestion path: sort all `daysByDate` keys ascending and slice to `[feed.startDate, feed.endDate]` if set, otherwise all keys. The previous loader-side ordering moves into the store.

## Day & Group Selectors

```ts
export function useDayView(date: string): {
  date: string
  displayText: string         // 'Today' or formatted weekday
  isToday: boolean
  issues: Issue[]
  articleKeys: ArticleKey[]
  allRemoved: boolean
  completedCount: number
  totalCount: number
} | null

export function useNewsletterView(date: string, sourceId: string): {
  title: string
  subtitle: string | null
  articleKeys: ArticleKey[]
  sections: Array<{ key: string, emoji?: string, order: number, articleKeys: ArticleKey[] }>
  hasSections: boolean
  allRemoved: boolean
  completedCount: number
  totalCount: number
} | null
```

Implementation: both subscribe to `subscribeDay(date)`. Each rebuilds its derived shape from `daysByDate.get(date)` plus `articlesByKey` reads. The `useSyncExternalStore` `getSnapshot` must return the same object identity when data is unchanged — keep a per-(date, sourceId) memo cache keyed by `(daySliceRef, articleKeysSignature)` so React's bailout works.

Removed selectors (deleted once components migrate):
- `useDayArticlesSummary(date)`
- `useCompletedArticlesCount(date, urls)`
- `useAllArticlesRemoved(date, urls)`

## Article Card Selector

```ts
export function useArticleCard(key: ArticleKey): {
  url: string
  title: string
  articleMeta: string
  category: string
  sourceId: string
  section?: string
  isRead: boolean
  isRemoved: boolean
  summary: SummaryData | null
  expandedView: boolean
  originalOrder: number
} | null
```

Stable identity: same key → same returned object reference unless underlying slice changed. Use a small per-key memo so consumers can rely on it for `useMemo` deps.

## Lifecycle Selector

```ts
export function useArticleLifecycle(key: ArticleKey): {
  isRead: boolean
  isRemoved: boolean
  state: 'unread' | 'read' | 'removed'
  markAsRead(): void
  markAsUnread(): void
  toggleRead(): void
  markAsRemoved(): void
  toggleRemove(): void
}
```

Replaces `useArticleState(date, url)`. Internally delegates to `articleLifecycleReducer.reduceArticleLifecycle` and `queueDailyArticlePatch({ key, buildPatch })` (mutation queue updated to take `key` directly — see below).

## Selection Surface

```ts
type SelectedArticleDescriptor = {
  key: ArticleKey
  date: string
  url: string
  title: string
  summary: SummaryData | null
}

export function useIsSelected(key: ArticleKey): boolean
export function useIsSelectMode(): boolean
export function useSelectedArticles(): SelectedArticleDescriptor[]
```

`Selectable` and `interactionActions` migrate from `article-${url}` ID strings to `ArticleKey`. Container IDs (`calendar-${date}`, `newsletter-${date}-${source}`, `section-${date}-${source}-${key}`) stay as opaque strings — they're not article identities.

`interactionReducer.js` keeps its shape; `selectedIds` becomes a `Set<ArticleKey>`. `commitInteractionState` (in store) updates `articleSlices[key].selected` directly — already key-keyed, only the ID derivation changes.

## Digest Surface

```ts
export function useDigestState(date: string): SummaryData | null

export function triggerDigest(keys: ArticleKey[]): Promise<void>
export function collapseDigest(keys: ArticleKey[], shouldRemove: boolean): Promise<void>
```

`useDigest` becomes a thin wrapper that owns only `expanded` view state. It receives `selectedKeys` (from `useSelectedArticles`) and:
1. Picks target date as `max(date for date::url in keys)`.
2. Calls `triggerDigest(keys)` which posts `/api/digest` with descriptors derived from the store and `queueDailyPayloadPatch({ date, payloadPatch })`.
3. Reads digest data via `useDigestState(date)`.

Deletes:
- `findMostRecentDate(articleDescriptors, payloads)`
- `groupDescriptorsByDate(articleDescriptors)` based on `getSnapshotArticleByUrl`
- `useDigest(results)` parameter (becomes parameter-less or `useDigest()`)

## Loader Surface (`hooks/useFeedLoader.js`)

```ts
type LoadFeedArgs = {
  startDate: string
  endDate: string
  signal?: AbortSignal
}

export function useFeedLoader(): {
  loadFeed(args: LoadFeedArgs): Promise<void>
}

export function getDefaultFeedDateRange(): { startDate: string, endDate: string }
```

Implementation:
1. Mark feed `fetching` via `setFeedStatus`. Set `setFeedRange(start, end)`.
2. `getDailyPayloadsRange` → `ingestFeedPayloads(cachedPayloads)` → `setFeedStatus({ status: 'cached' })` if any.
3. `scrapeNewsletters` → `ingestFeedPayloads(freshResults.payloads)` → `setFeedStatus({ status: 'ready', stats })`.
4. On scrape failure after cache: `setFeedStatus({ status: 'error', error })` but keep cached inventory.
5. Token gate every async transition (existing `requestTokenRef` pattern).

Removed:
- `useState(null)` for `results`
- `setResults` exposed to callers
- `SESSION_CACHE_TTL_MS`, `getSessionCacheKey`, `readSessionCachedResults`, `writeSessionCachedResults`
- `useSessionCache` arg (and all its callers)
- `hydrateResultPayloads`, `mergeFreshPayloadsIntoRenderedCache`

`App.jsx` replaces `if (!results) ... <Feed payloads={results.payloads}/>` with `useFeedStatus()` + `useVisibleDates()` and renders `<Feed />` (no props).

## Component Tree

`Feed.jsx`
```ts
function Feed(): JSX.Element        // reads useVisibleDates(), maps to <CalendarDay date={...}/>
```

`CalendarDay.jsx`
```ts
function CalendarDay({ date }: { date: string }): JSX.Element
```
Reads `useDayView(date)`. No `hydrateDay` call. No `payload` prop. Builds `descendantIds` from `articleKeys`. Renders `<NewsletterList date={date} issueIds={view.issues.map(i => i.source_id)} />`.

`NewsletterList`
```ts
function NewsletterList({ date, issueIds }: { date, issueIds: string[] }): JSX.Element
// renders one <NewsletterDay date={date} sourceId={id}/> per issue
```

`NewsletterDay.jsx`
```ts
function NewsletterDay({ date, sourceId }: { date: string, sourceId: string }): JSX.Element
```
Reads `useNewsletterView(date, sourceId)`. Renders `<ArticleList articleKeys={...}/>` or per-section `<Section />`.

`ArticleList.jsx`
```ts
function ArticleList({ articleKeys }: { articleKeys: ArticleKey[] }): JSX.Element
```
Renders one `<ArticleCard articleKey={key}/>` per key. The `order` style for removed-tail moves into `ArticleCard` itself, since it already subscribes to the slice.

`ArticleCard.jsx`
```ts
function ArticleCard({ articleKey }: { articleKey: ArticleKey }): JSX.Element
```
Reads `useArticleCard(key)`, `useArticleLifecycle(key)`, `useSummary(key)`, `useIsSelectMode()`. No `article` prop. `componentId` becomes the `articleKey`.

`ReadStatsBadge.jsx`
```ts
function ReadStatsBadge({ date }: { date: string }): JSX.Element | null
```
Reads `useDayView(date)` for `(completedCount, totalCount)`. (Newsletter-level badge takes `{ date, sourceId }` and reads `useNewsletterView` — small overload via two components or one branch.)

`RemovedOrderSlot.jsx`
- Replaced. Group-level `allRemoved` is on the view model, not a per-`(date, urls)` selector. Consumers that need ordering-on-removed compute `order = view.allRemoved ? 10_000 + originalOrder : originalOrder` inline.
- Delete file once last consumer migrates.

`Selectable.jsx`
- `id` becomes `ArticleKey` for article-level selectables. Container selectables keep their string IDs.
- `descendantIds: ArticleKey[]` for article descendants.

## Mutation Queue (`lib/dailyPayloadMutations.js`)

```ts
type ArticlePatchInput = {
  key: ArticleKey
  buildPatch?: (article: ArticleSlice) => Partial<ArticleSlice>
  patch?: Partial<ArticleSlice>
}

export function queueDailyArticlePatch(input: ArticlePatchInput): Promise<DailyPayload>
export function queueBatchArticlePatches(inputs: ArticlePatchInput[]): Promise<void>
export function queueDailyPayloadPatch(input: { date: string, payloadPatch: any }): Promise<DailyPayload | null>
```

Internal:
- Replace `composePayloadFromStore` callsite with internal `composeDayPayloadForServer(date)` that walks `daysByDate.get(date).articleKeys` (declarative, no global scan).
- `replaceDayFromServer(date, payload)` → `ingestDayPayload(payload)`.
- `applyArticlePatch`, `applyArticlePatches`, `applyDayPatch` stay as private store actions; the mutation queue calls them via narrow exports.

`storageKey` argument and `previousPayload` parameter are dropped: queue keys by `date`, fallback payload is unused after store becomes the authority.

## App.jsx Surface After

```jsx
function AppContent({ loadFeed, showSettings, setShowSettings }) {
  const feedStatus = useFeedStatus()
  const visibleDates = useVisibleDates()
  const isSelectMode = useIsSelectMode()
  const selectedArticles = useSelectedArticles()
  const digest = useDigest()
  // batch lifecycle helpers operate on selectedArticles[].key
}
```

`applyBatchLifecyclePatch` becomes:
```ts
async function applyBatchLifecyclePatch(
  selected: SelectedArticleDescriptor[],
  eventFactory: (article) => LifecycleEvent
): Promise<void> {
  await queueBatchArticlePatches(selected.map(({ key }) => ({
    key,
    buildPatch: (article) => reduceArticleLifecycle(article, eventFactory(article)).patch
  })))
}
```

## Verification Hooks

After implementation:
- `cd client && npm run build` (must pass).
- Browser smoke: load default range with empty `localStorage` and `sessionStorage`.
- Repro of incident: confirm article that exists only in fresh scrape (not cache) renders without manual interaction.
- Selection + batch mark-read across two dates writes one payload per date.
- Digest from selection of 2+ articles across 2 dates uses the most-recent date.

## Migration Order (concrete steps)

1. **Extend store with feed + day inventory.**
   - Add `feed`, mutate ingestion to track `articleKeys` per day, add `feedListeners`.
   - Keep legacy exports temporarily (re-implement them as thin wrappers).

2. **Add new selectors:** `useFeedStatus`, `useVisibleDates`, `useDayView`, `useNewsletterView`, `useArticleCard`, `useArticleLifecycle`, `useSelectedArticles`, `useDigestState`.

3. **Single ingestion path.** Introduce `ingestFeedPayloads`/`ingestDayPayload`. Reroute `hydrateDay`, `mergeDayFromServer`, `replaceDayFromServer` through it as thin shims (still callable for one commit, then deleted).

4. **Loader becomes command-only.** Drop `results`, `sessionStorage`, `useSessionCache`. `App.jsx` calls `loadFeed` then renders driven by store.

5. **Component rendering switches to keys.** `Feed → CalendarDay → NewsletterDay → ArticleList → ArticleCard` migrate one at a time. Delete `RemovedOrderSlot` once unused.

6. **Selection migrates to article keys.** Update `Selectable`, `interactionReducer`/`commitInteractionState`, `useSelectedDescriptors` → `useSelectedArticles`.

7. **Digest moves off `results`.** `useDigest` reads `useSelectedArticles`/`useDigestState`.

8. **Mutation queue migrates to keys.** Drop `storageKey`/`previousPayload`/`url+date` params.

9. **Remove dead code.**
   - `urlToArticleKey`, `getSnapshotArticleByUrl`
   - `dayArticleSummaries`, `dayArticleSummaryListeners`, `dayLifecycleListeners`
   - `useDayArticlesSummary`, `useCompletedArticlesCount`, `useAllArticlesRemoved`
   - `RemovedOrderSlot.jsx`
   - `mergePreservingLocalState` (inline into store ingestion)
   - `findMostRecentDate`, `groupDescriptorsByDate` in `useDigest`

10. **Doc sync.** Update `docs/client/feed-loading.md`, `docs/client/storage.md`, `docs/state-machines/feed-and-storage.md` to reflect single read model.
