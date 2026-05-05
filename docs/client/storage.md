---
name: client/storage
description: Client-side article store, optimistic mutation queues, and persistence tiers.
last_updated: 2026-05-04 16:28
---
# Client: Storage

[→ Server: Storage](../server/storage.md) | [→ State Machines: Feed & Storage](../state-machines/feed-and-storage.md)

The client storage boundary is split into a live in-memory article store and a narrow network mutation layer.

## Live Store

`store/articleStore.js` is the source of truth for rendered client article state. It exposes `useSyncExternalStore` selectors for article slices, day slices, selected descriptors, select mode, and container expansion.

Feed payloads hydrate or merge into the store before rendering. Components subscribe to the smallest useful slice, so article mutations no longer force whole-day UI subscribers to re-render.

## Mutation Layer

`lib/dailyPayloadMutations.js` owns optimistic persistence. It applies local store patches first, then writes through `lib/storageApi.js` using daily payload endpoints.

Single-article writes use `queueDailyArticlePatch()`. Batch article writes use `queueBatchArticlePatches()`, grouped into one payload patch per date. Digest-level writes use `queueDailyPayloadPatch()`.

Server writes send the expected `storage_updated_at` metadata when available. On conflict, the mutation queue refreshes the server payload and retries once. On failure, it restores the day from the server payload so the client fails back to durable state rather than keeping an unpersisted optimistic edit.

## Persistence Tiers

1. `articleStore`: instant same-tab live state for articles, days, summaries, selection, and expanded containers.
2. `sessionStorage`: short-lived feed result cache keyed by date range.
3. `localStorage`: `expandedContainers:v1` only.
4. Supabase PostgreSQL: durable `daily_cache` payloads and metadata.
