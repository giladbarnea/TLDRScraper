---
status: completed
plan: unified-feed-read-model-plan.md
todos: unified-feed-read-model-todos.md
last_updated: 2026-05-10 18:02, f1f2f31
---

# Unified Feed Read Model — Implementation Notes

## Cutover vs phased migration

The plan sketched a 9-step migration that kept legacy exports (`hydrateDay`, `mergeDayFromServer`, `replaceDayFromServer`, `composePayloadFromStore`) alive as shims during the transition. I cut over in one pass instead. Rationale: the plan's own warning — "two read models alive at once" is the anti-pattern we're removing — applies just as much to migration scaffolding as to production code. A single coordinated rewrite of `articleStore.js`, `useFeedLoader.js`, and the component tree was less risk than living in shim-land.

## Identity migration was wider than expected

`Selectable`'s opaque-string `id` propagated further than the plan suggested. Article-level selectables now use article keys directly; container IDs (`calendar-${date}`, `newsletter-${date}-${source}`, `section-${date}-${source}-${key}`) stayed as opaque strings because they aren't article identities. The interaction reducer didn't need changes since it treats IDs opaquely.

## Group derivations live on `useDayView` / `useNewsletterView`

The plan called for collapsing `dayArticleSummaries` and `dayLifecycleListeners` into date-level notifications. Implemented as derived view shapes that include per-section and per-newsletter `allRemoved` / `completedCount` (see `buildDayView`, `buildNewsletterView` in `articleStore.js`). Per-section ordering moved from `RemovedOrderSlot` (deleted) into the parents (`CalendarDay`, `NewsletterDay`) using `motion.div` `order` style — same visual behavior, no per-group selector needed.

## Drift: server-side summary persistence

The plan didn't cover summary persistence. After the unified read model landed, manual testing surfaced that summaries vanished on refresh while lifecycle changes persisted. The first fix added a client-side `queueDailyArticlePatch` in `summaryActions.fetch`. The user pushed back on the architecture — durable writes belong on the server. Final design: `/api/summarize-url` now accepts `issue_date`, calls `persist_article_summary` (in `serve.py`) with conflict-retry against `patch_daily_article`, and returns the canonical payload alongside the markdown. Client ingests the returned payload via `ingestDayPayload`. This both fixes the bug and aligns with the read-model thesis: there's now no path where the client thinks a summary exists but Supabase doesn't.

The bug pre-existed the refactor — the original `articleStore.js` also wrote summaries only to memory. Inheriting it during the cutover made it visible.

## Manual-test scaffolding (out of scope of plan)

Built as a side-effect of validating Tests 4/6 from the plan's verification section. `DebugPanel` + `YamlView` + `yamlTokens` + `apiError` cover store inspection, store-clearing, scrape request/response logging, and a uniform API-error surface (`readApiResponse` → `console.error`). The YAML view uses a hand-written tokenizer instead of a syntax highlighter library — the user accepted up to 3x complexity for highlighting; the actual cost was closer to 1.5x because `yaml.stringify` did the structural work and the tokenizer only had to classify per-line content. Smart pruning happens in `DebugPanel`'s `compactArticle`/`compactDay` before YAML — keeps the renderer dumb and the output information-dense.

## Per-article fold heuristic

Folds wrap `<details>` around any `- url: <value>` line and its more-indented continuation. Articles whose pruned form is just `url:` render as plain lines, not empty `<details>` widgets — avoiding affordance-without-payoff.
