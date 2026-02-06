# Rescrape “Today” in Background (Non-Blocking Feed Hydration)

## Problem statement

On page refresh, the client blocks initial render on `POST /api/scrape`. This is **correct-but-bad UX** because the server intentionally rescrapes “today” (more precisely: any date whose `daily_cache.cached_at` is before the next midnight in `America/Los_Angeles`) via `util.should_rescrape()` + `tldr_service.scrape_newsletters_in_date_range()`. For “today”, `should_rescrape()` is effectively always `True` until next midnight Pacific, so refresh often triggers network scraping work and delays first paint.

**Goal:** show any already-cached articles immediately, then rescrape in the background and merge new entries into the already-rendered feed—without clobbering local optimistic user state (read/removed/TLDR) and without reintroducing “API hammering” anti-patterns.

## Current system snapshot (relevant parts)

### Server

- `POST /api/scrape` → `tldr_service.scrape_newsletters_in_date_range()`
  - Pulls cached rows for the whole range in one query (`storage_service.get_daily_payloads_range`).
  - Decides per-date whether to rescrape using `util.should_rescrape(date_str, cached_at_epoch_seconds)`.
  - For rescraped dates, scrapes with cached URLs excluded and then merges with cached payload via `_merge_payloads()` to preserve `tldr`, `read`, and `removed`.
  - Writes scrape results through `storage_service.set_daily_payload_from_scrape()` to advance `cached_at` (scrape freshness signal).
- `POST /api/storage/daily-range` returns cached payloads only (fast DB read).

### Client

- `App.jsx` loads default range (today → 2 days ago) and calls `scrapeNewsletters()` on mount.
- `CalendarDay.jsx` uses `useSupabaseStorage(getNewsletterScrapeKey(date), payload)` and relies on **scrape-first hydration**: the `payload` prop seeds `useSupabaseStorage`’s module-level `readCache` for instant reads.
- `useSupabaseStorage.js` intentionally does **not** overwrite `readCache` when the same key is already present (“seed only if empty”).

This last point is the core coupling: once a day’s key is seeded, **passing a new `payload` prop does not update subscribers** unless something explicitly updates `readCache` and calls `emitChange(key)` (this is also documented in `GOTCHAS.md`).

## Root cause

1. The first paint depends on `/api/scrape`, which can be slow due to “today” rescrape.
2. The current “scrape-first hydration” caching model makes it non-trivial to “just swap in new payloads” later: `useSupabaseStorage` will keep serving the already-seeded value for a given key until `emitChange(key)` happens.

## Design goals

1. **Non-blocking initial render:** show cached feed as soon as the DB can return it.
2. **Background freshness:** always trigger a background scrape for the current range (or at minimum for the rescrapable dates) and merge in new entries.
3. **Never clobber optimistic user state:** if the user removes/reads an article while the scrape is in-flight, UI state must not “jump backwards” when background results arrive.
4. **Minimal surface area + reuse existing primitives:** lean on the existing `useSupabaseStorage` cache+pubsub design and the server’s merge semantics.
5. **Deterministic, race-safe orchestration:** cancel/ignore stale responses (request tokens + abort), mirroring `useSummary`’s pattern.

## Proposed approach (high level)

Introduce a small “bootstrap + background refresh” orchestrator that does:

1. **Hydrate immediately from server cache:**
   - `POST /api/storage/daily-range` for the desired range (fast).
   - Render those payloads right away.
2. **Rescrape in background:**
   - Trigger `POST /api/scrape` for the same range (or just the rescrapable dates).
   - When it returns, **merge the scrape result into the client’s current local state** (not just into the server’s cached payload) and publish updates into the `useSupabaseStorage` cache so already-mounted `CalendarDay` components re-render with new articles.

The key is step (2): treat the `useSupabaseStorage` cache as the in-browser source of truth for “what the UI currently believes”, and apply background scrape results as a pure merge onto that state.

## Minimal “plumbing” needed in the client

### 1) A public way to push authoritative updates into `useSupabaseStorage`

Today, only hook instances can call `setValueAsync()`, and seeding is “only-if-empty”. Background rescrape needs an explicit “push update for this key” API.

Recommended minimal change:

- Export two tiny helpers from `client/src/hooks/useSupabaseStorage.js`:
  - `getCachedStorageValue(key): any | undefined` (read from module-level `readCache`)
  - `setCachedStorageValue(key, value, { emit = true, overwrite = true }): void`
    - Writes to `readCache`
    - Calls `emitChange(key)` if `emit`

This is directly aligned with the “shared readCache + emitChange” invariant described in `GOTCHAS.md` and avoids introducing a new store abstraction.

### 2) A pure merge function on the client (payload in, payload out)

Even though the server already merges scrape results with its cached payload, we must merge against the **client’s current local payload** to preserve optimistic user interactions that may not have reached the server yet.

Add a pure helper (shape mirrors `tldr_service._merge_payloads`):

- `mergeDailyPayloads(scrapedPayload, localPayload) -> mergedPayload`
  - Article identity: `url`
  - Prefer `localPayload` values for user-owned fields: `tldr`, `read`, `removed`
  - Keep scraped ordering for scraped articles; append any local-only articles not present in scraped (robust to transient scrape regressions)
  - Issues: union by `(date, source_id, category)` (same key as server)

### 3) A small orchestrator hook for App + ScrapeForm

Create a hook with a tiny state machine (or plain state + request tokens) that supports:

- `hydrateFromCache(startDate, endDate)` (fast, sets initial feed)
- `refreshInBackground(startDate, endDate)` (slow, merges updates into storage cache)
- Request token + abort controller so “new range selected” cancels prior work

The hook returns:

- `payloads` (for initial rendering / day list)
- `isSyncing` + `lastSyncError` (optional UX polish)

## Concrete flow (default refresh)

### Phase A — show cached immediately

1. App computes `startDate/endDate` (current behavior).
2. App calls `storageApi.getDailyPayloadsRange(startDate, endDate)`:
   - If it returns payloads:
     - `setResults({ payloads, source: 'cache', stats: null })`
     - (Optional) For each payload: `setCachedStorageValue(newsletters:scrapes:${date}, payload, { overwrite: true })`
       - This is optional because `CalendarDay` will seed anyway, but doing it here makes the contract explicit: “cache hydration is authoritative”.
   - If empty:
     - Render “no cached results yet” (keep existing skeleton/loading UI).

### Phase B — background rescrape and merge

1. Start `scrapeNewsletters(startDate, endDate, signal)` without blocking UI.
2. When it resolves with `scrapedPayloads`:
   - For each `scrapedPayload`:
     - `key = newsletters:scrapes:${scrapedPayload.date}`
     - `local = getCachedStorageValue(key) ?? scrapedPayload`
     - `merged = mergeDailyPayloads(scrapedPayload, local)`
     - `setCachedStorageValue(key, merged, { overwrite: true, emit: true })`
   - Optionally update App-level `results` stats/source labels, but **do not rely on prop-updating `CalendarDay`** for actual data changes; the storage cache is the delivery mechanism.

Result: cached feed shows instantly; new articles appear as soon as background scrape returns; optimistic user state is preserved because merge prefers local `tldr/read/removed`.

## Race-safety / correctness details

### Request tokens (ignore stale responses)

Use the same pattern as `useSummary`:

- Generate `requestToken = `${Date.now()}-${Math.random().toString(16).slice(2)}``
- Store it in a ref.
- When cache hydration or scrape resolves, check token matches current; otherwise ignore.

### AbortController (cancel in-flight work)

- Keep two abort controllers:
  - One for cache hydration request (fast; mostly for hygiene)
  - One for background scrape request (slow; important)
- On range change/unmount, abort both.

### Never bypass the storage abstraction in child components

All updates should go through the `useSupabaseStorage` cache+emit mechanism. Do not reintroduce patterns like “every ArticleCard fetches daily payload directly” (see `GOTCHAS.md`).

## Optional: reduce background scrape scope to just rescrapable dates

If desired later (not required for the first iteration), the orchestrator can:

- Always hydrate the whole requested range via `/api/storage/daily-range`.
- Then call `/api/scrape` for a **minimal rescrape range**:
  - If only “today” is desired: `start=end=today`
  - If you add a lightweight endpoint that returns `{ date, cached_at }` for a range, the client could compute staleness and scrape only stale dates.

This is an optimization; the baseline design already relies on the server to do the right thing per-date.

## Files/modules touched (intended)

- `client/src/hooks/useSupabaseStorage.js`
  - Export `getCachedStorageValue` / `setCachedStorageValue` (thin wrappers over existing module state).
- `client/src/lib/mergeDailyPayloads.js` (new pure helper; name flexible)
- `client/src/hooks/useFeedHydration.js` (new orchestrator hook; or keep in `App.jsx` if you want ultra-minimal surface area)
- `client/src/App.jsx` and `client/src/components/ScrapeForm.jsx`
  - Use orchestrator for “cache-first display, background refresh”

## Acceptance criteria / manual verification checklist

1. Hard refresh with an existing Supabase cache:
   - Feed renders quickly from `/api/storage/daily-range` (no waiting on `/api/scrape`).
   - “Syncing…” indicator can show while background scrape runs, but articles are usable.
2. While background scrape is running:
   - Mark/remove an article; state updates immediately (no waiting on server).
   - When background scrape completes, the user’s just-made changes persist (no regression).
3. After background scrape completes:
   - New articles discovered for “today” appear in the feed without a full page reload.
4. Change range in settings quickly multiple times:
   - Old responses do not overwrite the newest selection (request token works).

## Project tree (generated)

```text
TLDRScraper
├── .claude
│   ├── agents
│   │   ├── codebase-analyzer-multiple-subsystems.md
│   │   ├── codebase-analyzer-single-subsystem.md
│   │   ├── codebase-locator.md
│   │   ├── react-antipattern-auditor.md
│   │   └── web-deep-researcher.md
│   ├── hooks
│   │   ├── block-until-reads.sh
│   │   ├── README.md
│   │   └── require-reads.sh
│   ├── skills
│   │   ├── architecture-create
│   │   │   └── SKILL.md
│   │   ├── architecture-sync-current-changes
│   │   │   └── SKILL.md
│   │   ├── architecture-sync-since-last-updated
│   │   │   └── SKILL.md
│   │   ├── catchup
│   │   │   └── SKILL.md
│   │   ├── implement-plan
│   │   │   └── SKILL.md
│   │   ├── plan
│   │   │   └── SKILL.md
│   │   ├── research-codebase
│   │   │   └── SKILL.md
│   │   ├── review-plan
│   │   │   └── SKILL.md
│   │   ├── to-done
│   │   │   └── SKILL.md
│   │   ├── vercel
│   │   │   └── SKILL.md
│   │   └── FINISH_COMMANDS_MIGRATION.md
│   ├── settings.backup.json
│   └── settings.json
├── .githooks
│   ├── post-checkout
│   ├── post-merge
│   ├── post-rewrite
│   ├── pre-commit
│   ├── pre-merge-commit
│   ├── README.md
│   ├── sync-upstream-suggestions.md
│   └── util.sh
├── .github
│   └── workflows
│       ├── claude.yml
│       ├── GEMINI_REMOTE_AUTH.md
│       ├── maintain-documentation.yml
│       ├── nightly-vercel-cleanup.yml
│       ├── test-gemini-wif.yml
│       ├── weekly-branch-pr-cleanup.yml
│       ├── weekly-supabase-cleanup.yml
│       └── WORKFLOW_DIAGRAM.md
├── adapters
│   ├── __init__.py
│   ├── aiwithmike_adapter.py
│   ├── anthropic_adapter.py
│   ├── anthropic_news_adapter.py
│   ├── bytebytego_adapter.py
│   ├── claude_blog_adapter.py
│   ├── cloudflare_adapter.py
│   ├── danluu_adapter.py
│   ├── deepmind_adapter.py
│   ├── hackernews_adapter.py
│   ├── hillel_wayne_adapter.py
│   ├── infoq_adapter.py
│   ├── jessitron_adapter.py
│   ├── lenny_newsletter_adapter.py
│   ├── lucumr_adapter.py
│   ├── martin_fowler_adapter.py
│   ├── netflix_adapter.py
│   ├── newsletter_adapter.py
│   ├── pointer_adapter.py
│   ├── pragmatic_engineer_adapter.py
│   ├── react_status_adapter.py
│   ├── savannah_adapter.py
│   ├── simon_willison_adapter.py
│   ├── softwareleadweekly_adapter.py
│   ├── stripe_engineering_adapter.py
│   ├── tldr_adapter.py
│   ├── will_larson_adapter.py
│   └── xeiaso_adapter.py
├── api
│   └── index.py
├── client
│   ├── scripts
│   │   └── lint.sh
│   ├── src
│   │   ├── components
│   │   │   ├── ArticleCard.jsx
│   │   │   ├── ArticleList.jsx
│   │   │   ├── CalendarDay.jsx
│   │   │   ├── Feed.jsx
│   │   │   ├── FoldableContainer.jsx
│   │   │   ├── NewsletterDay.jsx
│   │   │   ├── ReadStatsBadge.jsx
│   │   │   ├── ResultsDisplay.jsx
│   │   │   ├── ScrapeForm.jsx
│   │   │   ├── Selectable.jsx
│   │   │   └── SelectionCounterPill.jsx
│   │   ├── contexts
│   │   │   └── InteractionContext.jsx
│   │   ├── hooks
│   │   │   ├── useArticleState.js
│   │   │   ├── useLocalStorage.js
│   │   │   ├── useLongPress.js
│   │   │   ├── useOverscrollUp.js
│   │   │   ├── usePullToClose.js
│   │   │   ├── useScrollProgress.js
│   │   │   ├── useSummary.js
│   │   │   ├── useSupabaseStorage.js
│   │   │   └── useSwipeToRemove.js
│   │   ├── lib
│   │   │   ├── quakeConsole.js
│   │   │   ├── scraper.js
│   │   │   ├── stateTransitionLogger.js
│   │   │   ├── storageApi.js
│   │   │   └── storageKeys.js
│   │   ├── reducers
│   │   │   ├── articleLifecycleReducer.js
│   │   │   ├── gestureReducer.js
│   │   │   ├── interactionReducer.js
│   │   │   └── summaryDataReducer.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .gitignore
│   ├── biome.json
│   ├── CLIENT_ARCHITECTURE.md
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   └── vite.config.js
├── docs
│   ├── react-19
│   │   ├── react-19-2.md
│   │   ├── react-19-release.md
│   │   ├── react-19-upgrade-guide.md
│   │   ├── react-19-use.md
│   │   ├── react-compiler-1-0.md
│   │   ├── react-compiler-debugging.md
│   │   ├── react-compiler-install.md
│   │   ├── react-dom-hooks-useFormStatus.md
│   │   ├── react-separating-events-from-effects.md
│   │   ├── react-useActionState.md
│   │   ├── react-useOptimistic.md
│   │   └── react-useTransition.md
│   └── testing
│       └── headless_playwright_guide.md
├── scripts
│   ├── setup
│   │   ├── build_client.sh
│   │   ├── common.sh
│   │   ├── ensure_tooling.sh
│   │   └── ensure_uv_and_sync.sh
│   ├── auto-pr-merge.sh
│   ├── clean_vercel_deployments.py
│   ├── generate_context.py
│   ├── generate_tree.py
│   ├── install-codex-cli.sh
│   ├── install-gemini-cli.sh
│   ├── markdown_frontmatter.py
│   ├── print_root_markdown_files.sh
│   ├── resolve_quiet_setting.sh
│   ├── run-codex.sh
│   ├── run-gemini.sh
│   └── update_doc_frontmatter.py
├── tests
│   ├── unit
│   │   ├── test_canonicalize_url.py
│   │   └── test_should_rescrape.py
│   ├── test_google_adk_smoke.py
│   ├── test_scrape_cache_server.py
│   └── test_some_server_functionalities.py
├── thoughts
│   ├── 25-12-21-failed-scrapes-are-retryable
│   │   └── discussion.md
│   ├── 26-01-25-scrape-parallelize-everything
│   │   ├── plans
│   │   │   └── flattened-parallelism.md
│   │   ├── followup.md
│   │   └── followup.plan.review.md
│   ├── 26-01-29-google-photos-selection
│   │   └── plans
│   │       └── plan.md
│   ├── 26-02-05-rescrape-in-background
│   │   ├── codex-prompt.txt
│   │   └── plan-2.md
│   └── done
│       ├── 2025-11-08-migrate-client-localstorage-to-server-supabase
│       │   ├── implementation.md
│       │   ├── manual-browser-testing.md
│       │   ├── plan.md
│       │   └── research.md
│       ├── 25-10-27-hackernews-integration
│       │   ├── plan.md
│       │   └── research.md
│       ├── 25-10-28-fix-cache-ui-state-sync
│       │   └── plan.md
│       ├── 25-10-30-multi-newsletter
│       │   └── plan.md
│       ├── 25-10-31-vue-to-react-19-migration
│       │   └── plan.md
│       ├── 25-11-04-code-duplication
│       │   ├── plan-issue-a-section-parsing.md
│       │   ├── plan-issue-b-localstorage-keys.md
│       │   ├── plan-issue-c-article-normalization.md
│       │   └── plan.md
│       ├── 25-11-04-mixed-concerns-refactor
│       │   ├── plan-issue-b-extract-build-scrape-response.md
│       │   ├── plan-issue-c-eliminate-duplicate-parsing.md
│       │   └── plan.md
│       ├── 25-11-04-remove-summarize
│       │   └── plan.md
│       ├── 25-11-29-tldr-remove-button-fixes
│       │   └── summary.md
│       ├── 25-12-04-zen-mode-single-overlay-lock
│       │   └── summary.md
│       ├── 25-12-09-react-modernization
│       │   └── summary.md
│       ├── 25-12-15-component-refactoring-priority
│       │   └── summary.md
│       ├── 25-12-16-fix-cache-scrape-today-edge-case
│       │   └── summary.md
│       ├── 25-12-22-zen-overlay-header-and-swipe-interactions
│       │   └── summary.md
│       ├── 26-01-11-cache-logic-only-in-server
│       │   ├── plan.md
│       │   └── summary.md
│       ├── 25-12-22-zen-overlay-header-and-swipe-interactions.md
│       ├── 25-12-25-aiwithmike-adapter.md
│       ├── 26-01-10-improve-fetch-range-speed.md
│       ├── 26-01-22-speed-up-app-refresh.md
│       ├── 26-01-24-rescrape-full-days.md
│       └── 26-01-30-migrate-to-reducer-pattern.md
├── .gitattributes
├── .gitignore
├── .vercelignore
├── AGENTS.md
├── ARCHITECTURE.md
├── BUGS.md
├── CLAUDE.md
├── CODEX.md
├── GEMINI.md
├── GOTCHAS.md
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── serve.py
├── setup-hooks.sh
├── setup.sh
├── source_routes.py
├── storage_service.py
├── summarizer.py
├── supabase_client.py
├── test_anthropic_sources_full_pipeline.py
├── tldr_app.py
├── tldr_service.py
├── TLDRScraper.code-workspace
├── util.py
├── uv.lock
└── vercel.json
```
