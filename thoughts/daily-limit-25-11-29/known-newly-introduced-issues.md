---
last_updated: 2025-11-30 21:17, b19d703
---
# Known Newly Introduced Issues in `fix/tldr-remove-btns-not-responsing` branch

- TLDR visibility state is no longer persisted. ArticleCard dropped the calls to markTldrHidden / unmarkTldrHidden, so toggling a summary now only flips the
local useSummary flag and never updates Supabase (client/src/components/ArticleCard.jsx:7-58). The hook still exposes the state setters (client/src/hooks/
useArticleState.js:67-76), which means the code now has dead paths and any feature that depends on tldrHidden (sorting, analytics, resume-after-refresh)
silently stops working.
- The “missing issueDate” workaround is duplicated across three layers. The same article.issueDate || article.date normalization now lives in the component
(client/src/components/ArticleCard.jsx:7-24), in every storage read (client/src/lib/storageApi.js:16-62), and again when reading from cache (client/src/lib/
scraper.js:174-187). Instead of fixing the data once when it is written, each consumer has to remember to patch it, which makes future maintenance error-prone
and still leaves corrupted rows in storage.
- Debug logging was left inside the shared useArticleState hook. Every render now emits console.log noise and removal toggles print twice (client/src/hooks/
useArticleState.js:16-65). Shipping dev-only instrumentation inside a hook that runs for every card mixes concerns, bloats the production bundle, and makes
the browser console unusable for real issues.
- The two new Playwright scripts are nearly copy/paste identical through navigation, date entry, button clicks, and locator setup (tests/
test_remove_button.py:1-120, tests/test_tldr_button.py:1-110). Any change to the launch args, selectors, or error handling now has to be applied twice, and
both tests continue to rely on brittle force=True clicks despite the new guide warning against that. Extracting a shared helper (or even a pytest fixture)
would keep the scenarios focused on the behaviors they assert.
- scripts/clean_today.py deletes every row for “today” from the live daily_cache table with no environment guard or confirmation (scripts/clean_today.py:6-
17). That makes it dangerously easy for someone running tests locally to wipe production data, and ties a QA helper directly to production credentials—clearly
a maintenance hazard.