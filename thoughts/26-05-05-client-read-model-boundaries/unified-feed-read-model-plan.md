---
last_updated: 2026-05-09 17:17
status: completed
implementation: summary.md
todos: unified-feed-read-model-todos.md
---

# Unified Feed Read Model Plan

## Diagnosis

This is one problem with several symptoms: the client has more than one authority for the same feed.

Current authorities:

- `useFeedLoader.results.payloads` owns the rendered article inventory.
- `articleStore.articleSlices` owns live per-article state after an article is known to the store.
- `dayArticleSummaries`, `dayLifecycleListeners`, and grouped URL selectors own partial grouped derivations.
- `sessionStorage` owns a per-origin feed snapshot that can bypass Supabase and scrape refresh for 30 minutes.
- `urlToArticleKey` treats URL as a global lookup key even though the durable row key is really date plus URL.

That split explains the surprising behavior. An article can exist in Supabase, be returned by `/api/scrape`, or even be merged into `articleStore`, while the current React tree still does not render it because the rendered tree is driven by an older `results.payloads` snapshot.

The root fix is not to make every copy synchronize harder. The root fix is to remove the copies.

## Target Shape

One client-side feed store should own the visible feed document and the live article state.

The loader should orchestrate network work only. It should not own article data.

Components should render store keys and store selectors only. Transport payloads should enter the client through one ingestion boundary and should not flow down the component tree as article props.

The resulting model:

- Supabase remains the durable cross-device source.
- `articleStore` becomes the only same-tab read model for visible feed inventory and live state.
- `useFeedLoader` becomes a command hook: start load, report status, ingest payloads.
- `sessionStorage` no longer stores feed payloads.
- Component props carry dates, group IDs, and article keys, not payload-shaped article objects.

## Store State

Keep this state small and explicit:

- `feed`: active date range, load status, stats, error, ordered visible dates.
- `daysByDate`: issue metadata, digest, ordered article keys, storage metadata.
- `articlesByKey`: article entities keyed by `date::url`.
- `selection`: selected article keys.
- `expandedContainers`: local UI expansion state.

The article entity may contain both server-origin fields and mutable fields internally, but external reads should go through named selectors that describe intent.

External selectors should expose view models, not raw transport payloads:

- `useFeedStatus()` returns load status, active range, stats, and error.
- `useVisibleDates()` returns ordered dates.
- `useDayView(date)` returns the day title data, issues, and grouped article keys.
- `useNewsletterView(date, sourceId)` or equivalent returns section groups and article keys.
- `useArticleCard(articleKey)` returns the article card view model.
- `useArticleLifecycle(articleKey)` returns read/removed state and lifecycle commands.
- `useSelectedArticles()` returns selected article descriptors keyed by article key.
- `useDigestState(date)` returns digest state for one date.

Avoid selectors that take ad-hoc URL arrays from render props. Group selectors should derive membership from the store's day inventory.

## Identity

Use one article identity everywhere in the client: `date::url`.

Consequences:

- Remove `article-${url}` as the article component ID shape.
- Remove `urlToArticleKey` as an authority for actions.
- Selection stores article keys, not URLs.
- Digest and bulk actions receive article keys, then read date and URL from the store.
- Duplicate URLs across dates become boring instead of dangerous.

URL is still the external article address. It should not be the client row identity.

## Ingestion Boundary

All payload ingestion should go through one store action.

Pseudocode:

Ingest feed payloads for a range by ordering the payload dates, upserting every day into `daysByDate`, upserting every article into `articlesByKey`, replacing each day's ordered article key list with the payload order, preserving client-owned mutable fields from existing article entities, deleting stale article keys for that day, then notifying date and article subscribers once.

The same ingestion action should handle:

- Supabase cached payloads.
- Fresh scrape payloads.
- Server-confirmed mutation payloads.
- Rollback payloads after failed optimistic writes.

The merge policy stays simple:

- Server-origin fields come from the incoming payload.
- Client-owned mutable fields survive when the article key already exists.
- New articles get incoming mutable defaults.
- Stale articles for a refreshed day are removed from that day's inventory and from selection.

This makes "fresh scrape found a new article for an existing date" update the same store inventory that `Feed` renders.

## Loader Flow

`useFeedLoader` should stop returning `results.payloads`.

Pseudocode:

Load a date range by claiming a request token, marking the feed as fetching, reading Supabase daily-range, ingesting cached payloads if present, then running scrape, ingesting fresh payloads through the same store action, and finally marking the feed ready with scrape stats.

If cached payloads are present, the UI can render after the Supabase read. The later scrape still updates the same visible inventory, including new articles for existing dates.

If scrape fails after cached payloads rendered, keep the cached feed visible and mark the load as degraded or error-visible in feed status. Do not replace the feed with empty results.

If the request is aborted or superseded, ignore late payloads before ingestion.

## Cache Policy

Delete the `sessionStorage` feed payload cache.

Reason: it is a second per-origin article inventory. It can make preview and production diverge while both share the same Supabase database. It also skips the Supabase and scrape phases entirely on default load.

The server and Supabase already provide the useful cache:

- Supabase `daily_cache` gives fast cached render.
- `/api/scrape` owns freshness policy and unions today's cached data with fresh scrape data.

Keep `localStorage` only for expansion state. That is UI preference state, not feed inventory.

If a same-tab acceleration cache is reintroduced later, it must hydrate through the same store ingestion path and must not short-circuit the Supabase/scrape refresh. The simplest correct version is no payload cache.

## Rendering Flow

The component tree should become key-driven.

Pseudocode:

`App` reads feed status and renders `Feed`.

`Feed` reads visible dates from the store and renders `CalendarDay` for each date.

`CalendarDay` reads its day view from the store and renders newsletter groups.

`NewsletterDay` reads or receives group IDs and renders section groups.

`ArticleList` receives article keys.

`ArticleCard` receives one article key and reads its full view model from the store.

No component should call `hydrateDay`. Hydration is a loader/store responsibility.

No component should receive a payload-shaped article prop unless it is at the ingestion boundary.

## Grouped UI

Collapse grouped lifecycle logic into date-level derived selectors.

Current grouped UI has too many mechanisms:

- `dayArticleSummaries` cached all-removed state.
- `dayLifecycleListeners` for grouped lifecycle changes.
- URL arrays passed through `ReadStatsBadge` and `RemovedOrderSlot`.
- Components still derive group membership from payload props.

Simpler replacement:

- Store day inventory includes ordered article keys.
- Store selectors derive day, newsletter, and section groups from current day inventory.
- Group badges and all-removed state subscribe to the day.
- Any article lifecycle change in a day notifies the day.

This is less granular, but it is much harder to get wrong. A day usually has a small article count, and correctness is worth more than fine-grained listener maps here.

Remove `dayArticleSummaries` and `dayLifecycleListeners` unless profiling proves they are needed. They are optimization-shaped complexity currently carrying correctness risk.

## Digest And Selection

Digest should not accept `results`.

Pseudocode:

Trigger digest from selected article keys, derive article descriptors from the store, choose the target date from the selected articles, write digest state through the day store slice, and consume selected article lifecycle through article-key mutations.

Selection should store article keys and expose selected article descriptors from the store.

This removes:

- `findMostRecentDate(articleDescriptors, payloads)`.
- `getSnapshotArticleByUrl`.
- Result-payload dependency from `useDigest`.
- The need to guess which date owns a selected URL.

## Mutation Queue

Keep the current mutation queue direction, but let it depend on the unified store.

Pseudocode:

Resolve mutation intent against the latest store article at queue apply-time, optimistically patch the store entity, persist the narrow server patch, then ingest the server-confirmed day payload through the same ingestion boundary.

For batch mutations, group by article key date, not by descriptors reconstructed through URL lookup.

`composePayloadFromStore(date)` can become cheaper and clearer because the store will already own each day's ordered article keys. It should not scan every article in the global map.

## What To Remove

Remove these concepts as first-class feed read models:

- `results.payloads`.
- `sessionStorage` `scrapeResults:{start}:{end}` payload cache.
- `CalendarDay` calling `hydrateDay`.
- Article object props below the ingestion boundary.
- URL-only selection IDs.
- `urlToArticleKey`.
- `dayArticleSummaries`.
- `dayLifecycleListeners`.
- Group selectors that receive arbitrary URL arrays from render props.

Each removal reduces the number of places that can be "almost right".

## What Not To Do

Do not only patch `mergeFreshPayloadsIntoRenderedCache()` to replace existing `results.payloads` dates. That would fix the observed missing-article symptom while keeping two read models alive.

Do not add a cross-origin cache invalidation trick. The per-origin cache is the wrong abstraction for feed inventory.

Do not add another event bus between `results` and `articleStore`. The problem is that both exist as authorities.

Do not preserve fine-grained grouped subscriptions unless a measured performance issue forces it back. The current correctness bugs are more expensive than a few extra day-level renders.

## Migration Plan

1. Add feed inventory to `articleStore`.

Add `feed`, `daysByDate`, and ordered article keys per day. Keep existing article slices initially. Add selectors for visible dates, day view, article keys by group, article card view, and feed status.

2. Move ingestion into the store.

Replace `hydrateResultPayloads`, `hydrateDay`, `mergeDayFromServer`, and `replaceDayFromServer` with a smaller public ingestion surface. All incoming payloads go through the same merge and notification policy.

3. Convert rendering to keys.

Change `Feed`, `CalendarDay`, `NewsletterDay`, `ArticleList`, and `ArticleCard` so they receive dates, group IDs, and article keys. Remove payload-shaped article props from the render tree.

4. Simplify `useFeedLoader`.

Make it a network command hook that updates store feed status and ingests payloads. Remove `results` state and remove `sessionStorage` payload reads/writes.

5. Convert selection and digest to article keys.

Replace URL-only selection IDs with article keys. Update bulk lifecycle actions, summarize-each, browse, and digest trigger/consume flows to derive descriptors from selected store entities.

6. Collapse grouped derivations.

Remove `dayArticleSummaries`, `dayLifecycleListeners`, and URL-array group selectors. Use date-level store notifications and derived selectors over the current day inventory.

7. Tighten names after behavior is stable.

Rename remaining payload-oriented helpers so payload vocabulary exists only at API and ingestion boundaries.

## Verification Plan

Unit-level checks should focus on pure ingestion behavior:

- Cached day payload ingests visible date and article keys.
- Fresh scrape payload for an existing date adds a new article key to the rendered inventory.
- Existing article mutable fields survive a fresh scrape merge.
- Stale articles are removed from day inventory and selection.
- Two identical URLs on different dates remain distinct article keys.

Interaction checks:

- Mark read updates article card, badge count, selected dock state, and day/group all-removed derivations.
- Remove and restore update ordering, disabled state, badge count, and group collapse.
- Digest trigger works from selected article keys without `results.payloads`.

Regression checks for this incident:

- Load default range on two deployment origins with empty browser storage and confirm both render the article returned by shared Supabase/scrape state.
- Reload one origin repeatedly and confirm no per-origin payload cache can preserve an older article inventory.
- Run a cache-first load where fresh scrape adds an article to an existing date and confirm it appears without user interaction.

Minimum local verification after implementation:

- `cd client && npm run build`
- Manual browser run against the default feed range.
- Targeted browser inspection of article data attributes for the previously missing URL.

## Expected End State

After this change, the question "why does this article render here but not there?" has only a small number of possible answers:

- The store never ingested it.
- The store ingested it but a selector intentionally filtered it.
- The component for its article key failed.

It should no longer be possible for the article to be present in one client read model and absent from another equally authoritative read model.

That is the unprobleming move: make the wrong architecture unavailable.
