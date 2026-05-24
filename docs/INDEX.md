---
last_updated: 2026-05-24 05:46, be365c0
---

# Documentation Index

This index provides a directory tree of the `docs/` folder along with a brief description and representative keywords for each file to guide context gathering.

## Server

- **[scraping-pipeline.md](server/scraping-pipeline.md)**
  - *Description*: Server-side scraping pipeline, cache policies, and merge steps.
  - *Keywords*: scrape, cache-first, merge, union, daily payload, deduplication, URL

- **[adapters.md](server/adapters.md)**
  - *Description*: Adapter factory and logic for individual newsletter sources.
  - *Keywords*: TLDRAdapter, HackerNewsAdapter, Factory, HTML parsing, source

- **[storage.md](server/storage.md)**
  - *Description*: Server-side database schema and storage flow.
  - *Keywords*: Supabase, PostgreSQL, daily_cache, cached_at, payload

- **[articles-and-data.md](server/articles-and-data.md)**
  - *Description*: Data structures for Articles and Issues, and history deduplication algorithms.
  - *Keywords*: Article, Issue, history deduplication, schema, canonical URL

- **[summaries.md](server/summaries.md)**
  - *Description*: Backend summary generation pipeline and LLM prompt templates.
  - *Keywords*: Gemini, LLM, summarize-url, prompt template, effort

## Client

- **[feed-loading.md](client/feed-loading.md)**
  - *Description*: Client-side two-phase feed loading and merge algorithm.
  - *Keywords*: useFeedLoader, two-phase, merge algorithm, session cache, loadFeed

- **[storage.md](client/storage.md)**
  - *Description*: Client-side article store, optimistic mutation queues, and persistence tiers.
  - *Keywords*: articleStore, dailyPayloadMutations, optimistic write, persistence tiers, storage_updated_at

- **[articles-and-lifecycle.md](client/articles-and-lifecycle.md)**
  - *Description*: Client article lifecycle domain and reducer pattern.
  - *Keywords*: read, removed, toggle, unread, lifecycle reducer

- **[summaries-and-digests.md](client/summaries-and-digests.md)**
  - *Description*: Client-side summary and digest data vs view state management.
  - *Keywords*: useSummary, useDigest, data state, view state, markdown to html

- **[interaction-and-selection.md](client/interaction-and-selection.md)**
  - *Description*: Client-side interaction architecture, selection modes, and foldable containers.
  - *Keywords*: select mode, long press, suppress latch, Selectable, FoldableContainer

- **[reading-overlays.md](client/reading-overlays.md)**
  - *Description*: Client architecture for reading overlays including ZenMode and Digest.
  - *Keywords*: ZenModeOverlay, DigestOverlay, BaseOverlay, floating node, reader

- **[gestures.md](client/gestures.md)**
  - *Description*: Client-side gesture handling, specifically swipe-to-remove.
  - *Keywords*: swipe, remove, drag, Framer Motion, threshold

- **[context-menu.md](client/context-menu.md)**
  - *Description*: Client overlay context menu architecture and DOM/layer contracts.
  - *Keywords*: context menu, elaboration, Floating UI, mobile selection, right-click

## State-machines

- **[feed-and-storage.md](state-machines/feed-and-storage.md)**
  - *Description*: State machines for feed loading, scrape form, the client article store, and mutation persistence.
  - *Keywords*: states, transitions, scraping, articleStore, mutation queue, optimistic updates, tiers

- **[articles-and-summaries.md](state-machines/articles-and-summaries.md)**
  - *Description*: State machines for article lifecycle, summary data, digest, and the Zen lock.
  - *Keywords*: article lifecycle, summary reducer, digest, zen lock, shared object

- **[interaction-and-gestures.md](state-machines/interaction-and-gestures.md)**
  - *Description*: State machines for selection interaction, container expansion, and swipe gestures.
  - *Keywords*: interaction reducer, container expansion, swipe-to-remove, suppress latch

- **[reading-overlays.md](state-machines/reading-overlays.md)**
  - *Description*: State machines for Zen mode, digest overlay, and base overlay gesture primitives.
  - *Keywords*: zen mode, digest overlay, pull-to-close, overscroll, scroll progress

- **[context-menu.md](state-machines/context-menu.md)**
  - *Description*: State machine for the overlay context menu, including mobile selection reducers.
  - *Keywords*: context menu, mobile selection reducer, touching, selection observed

- **[toast.md](state-machines/toast.md)**
  - *Description*: State machine for toast notifications and global pub/sub.
  - *Keywords*: toast, exiting, toastBus, summary notification

- **[add-url.md](state-machines/add-url.md)**
  - *Description*: State machine for the URL-to-article modal and auto-submit on paste.
  - *Keywords*: add URL, auto-submit, isLikelyUrl, AddUrlOverlay, pseudo-source

- **[tracked-state.md](state-machines/tracked-state.md)**
  - *Description*: Internal utility state machine for tracked values in gestures.
  - *Keywords*: tracked state, useTrackedState, ref sync

- **[architecture-and-flows.md](state-machines/architecture-and-flows.md)**
  - *Description*: Cross-cutting topology, coupling matrices, and cross-machine user flows.
  - *Keywords*: topology, coupling matrix, flow, cross-machine, persistence round-trip

## Features

- **[digest.md](features/digest.md)**
  - *Description*: End-to-end architecture of the Digest feature including elaboration and caching.
  - *Keywords*: digest, elaboration, useElaboration, API contract, caching, end-to-end
