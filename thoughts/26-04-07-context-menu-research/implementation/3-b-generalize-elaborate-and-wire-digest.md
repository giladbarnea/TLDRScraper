---
name: Generalize Elaborate Endpoint And Wire Digest As Menu Consumer
implements: plans/3-b-generalize-elaborate-and-wire-digest.plan.md
last_updated: 2026-04-26 12:29
---

# Generalize Elaborate Endpoint And Wire Digest As Menu Consumer

## Summary

Generalized `/api/elaborate` end-to-end so it accepts a list of source-article URLs, extracted Zen's elaboration lifecycle into a shared `useElaboration` hook, migrated `ZenModeOverlay` onto it, and wired `DigestOverlay` as a second consumer of the overlay-menu contract with the same `Elaborate` action.

## Key changes

### Backend (Phase 1)

- `serve.py`: `/api/elaborate` now reads `selected_text`, `source_markdown`, and `article_urls` (non-empty list of strings). Legacy field names (`url`, `summary_markdown`) are gone. Validation failures return 400; missing fields return 400 via the service-layer `ValueError` path.
- `tldr_app.py`: `elaborate_url` → `elaborate(selected_text, source_markdown, article_urls, *, model)`. Response now returns `canonical_urls` (plural list, in input order).
- `tldr_service.py`: `elaborate_url_content` → `elaborate_content`. Validates non-empty `selected_text` and `source_markdown`; validates `article_urls` is a non-empty list of non-empty strings; canonicalizes each URL; scrapes all of them via a new sibling helper `_fetch_article_markdowns_parallel` (built on the same `ThreadPoolExecutor(max_workers=5)` shape as `_fetch_articles_content_parallel`). The new helper raises `RuntimeError` if any URL fails — partial-context elaborations are intentionally rejected.
- `summarizer.py`: `elaborate_url` → `elaborate(selected_text, source_markdown, article_bodies: list[str], *, model)`. `_build_elaborate_prompt` keeps its three-section shape; the third section is renamed `<original-article>` → `<source-articles>`. Single-body lists are inlined directly; multi-body lists wrap each body in `<article index="N">...</article>` with no other prompt structural change. Doctest covers both N=1 and N>1.

### Frontend (Phases 2–4)

- New shared hook `client/src/hooks/useElaboration.js` owns the elaboration state machine (`idle | loading | available | error`), the `AbortController`, abort-on-unmount, the trim-then-no-op-on-empty check, and the POST to `/api/elaborate`. Exposes `{ elaboration, runElaboration, closeElaboration }`. It is the only client-side caller of `/api/elaborate`.
- `ZenModeOverlay.jsx`: replaced inline `IDLE_ELABORATION` / `useState` / `abortControllerRef` / `runElaboration` / `closeElaboration` / unmount-abort `useEffect` with one `useElaboration({ sourceMarkdown: summaryMarkdown, articleUrls: [url] })` call. The `Elaborate` action's `onSelect` is now a direct reference to `runElaboration`. Visible behavior unchanged.
- `useDigest.js`: now exposes `markdown` and `articleUrls` alongside `html`. Both already existed as local computations on `data`.
- `App.jsx`: forwards `markdown` and `articleUrls` from `digest` into `<DigestOverlay />`.
- `DigestOverlay.jsx`: composes `useOverlayContextMenu(true)` and `useElaboration({ sourceMarkdown: markdown, articleUrls })`. Defines a single `Elaborate` action with the same key/label/icon/handler shape as Zen's (intentional copy, not abstracted). Passes the `overlayMenu` contract to `BaseOverlay`. Renders `<ElaborationPreview>` against the shared hook's state.

### Documentation (Phase 5)

- `client/ARCHITECTURE.md`: "Overlay Context Menu" section now describes both Zen and Digest as consumers; `useElaboration` is listed in Key modules. Call graph adds the `useElaboration` line under `ZenModeOverlay` and adds the parallel `DigestOverlay` branch.
- `client/STATE_MACHINES.md`: §11 (Zen Mode Overlay) and §12 (Digest Overlay) updated to reflect identical menu-consumer wiring; §19 (Overlay Context Menu) Actions table now lists both consumers; topology diagram updated; coupling notes updated.
- `thoughts/26-04-07-context-menu-research/0-b-feature-map.md`: rewritten to reflect two consumers, the parallel-scrape backend, and the renamed `<source-articles>` prompt section.

## Deliberate choices preserved from the plan

- The `Elaborate` action is copy-pasted between `ZenModeOverlay` and `DigestOverlay`. With only two callers, an `actionFactory` abstraction is premature; the duplication signals action portability.
- `useElaboration` lives in `client/src/hooks/`, not next to `OverlayContextMenu`. Elaboration is one possible action; the hook is independent of the menu's existence.
- `articleUrls` is a required prop on `useElaboration`. Both consumers always have URLs to send; allowing absence would re-introduce the optional-field branch the backend just removed.
- The backend always scrapes; partial-context elaborations are rejected. This keeps the prompt shape uniform and the quality story symmetric across consumers.
- No prompt structural redesign. Only the section rename `<original-article>` → `<source-articles>` and per-article `<article index="N">` wrappers when the list has more than one entry.
- No backwards-compatibility shim. The frontend and backend ship together; old field names (`url`, `summary_markdown`) are gone end-to-end.

## Verification

### Backend

- Doctest on `_build_elaborate_prompt` passes for both N=1 and N>1.
- Heredoc validation tests confirm `tldr_service.elaborate_content` raises `ValueError` on missing/empty `selected_text`, missing/empty `source_markdown`, missing/empty/non-list `article_urls`, non-string entries, and empty-string entries.
- Heredoc plumbing test confirms `_fetch_article_markdowns_parallel` is called once per URL, `summarizer.elaborate` receives bodies in the same canonical-URL order, and the response contains `canonical_urls` (plural).
- Heredoc test confirms `_fetch_article_markdowns_parallel` raises `RuntimeError` listing the failed URL and reason if any individual scrape fails.
- HTTP-level Flask `test_client` confirms 400 for empty/missing `article_urls`, missing `selected_text`, legacy field names alone, non-string entries, and empty-string entries; 200 with `success: true`, `elaboration_markdown`, and `canonical_urls` for both single-URL (Zen-shaped) and multi-URL (Digest-shaped) bodies.

### Frontend

- `npm run build` passes after Phase 3 and again after Phase 4.

### Acceptance criteria search results

- `rg -n "summary_markdown" .` — only matches in summary-feature code (`tldr_service.summarize_url_content`, `useSummary.js`, `tldr_app.summarize_url`, `ARCHITECTURE.md` summary section) and historical thought files. No production-code references in the elaborate path.
- `rg -nw "elaborate_url" .` — no production-code matches (only historical plan files).
- `rg -n "useElaboration" client/src` — three matches: the hook, `ZenModeOverlay.jsx`, `DigestOverlay.jsx`.
- `rg -n "useOverlayContextMenu\(" client/src/components` — `ZenModeOverlay.jsx` and `DigestOverlay.jsx`.
- `rg -n "/api/elaborate" client/src` — single caller: `client/src/hooks/useElaboration.js`.

## Non-goals reaffirmed

- No streaming response support for elaboration.
- No backend rate limiting, quota, or per-user gating.
- No prompt caching.
- No multi-action expansion of the menu beyond `Elaborate`.
- No reuse of digest-cached elaborations across renders. Each `Elaborate` triggers a fresh fetch.
- No Floating UI / BaseUI / focus-stack work.
- No `BaseOverlay` involvement in elaboration. The shell's contract surface stays the single `overlayMenu` prop introduced in plan 3.
