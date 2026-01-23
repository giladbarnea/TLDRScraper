---
last_updated: 2026-01-23 15:02, 7543c6c
---
# App refresh flow (client → server → client)

## Client-side flow (page load / refresh)

### Entry point: `App` initial load
1. **`App` mounts** and runs a `useEffect` with an empty dependency array (runs once on first render). The effect computes a date range of `today` and `today - 2 days`, then builds a sessionStorage cache key `scrapeResults:${startDate}:${endDate}` with a TTL of 10 minutes. 【F:client/src/App.jsx†L8-L44】
2. **Session storage fast-path:** if cached data exists and is fresh, `setResults(cached.data)` and **return early** (no network). 【F:client/src/App.jsx†L38-L45】
3. **Otherwise, call `scrapeNewsletters`** which POSTs to `/api/scrape` with `start_date` and `end_date`. The UI stays in the loading skeleton state until `results` is set. 【F:client/src/App.jsx†L47-L70】【F:client/src/lib/scraper.js†L6-L29】
4. **`scrapeNewsletters` resolves** to `{ success, payloads, source, stats }` or throws on failure. On success, `App` updates state and writes to sessionStorage (best-effort). 【F:client/src/App.jsx†L47-L63】【F:client/src/lib/scraper.js†L16-L28】
5. **Rendering after results:**
   - If `results.payloads` has content, render `Feed → CalendarDay` components for each daily payload. 【F:client/src/App.jsx†L95-L112】【F:client/src/components/Feed.jsx†L3-L13】
   - If empty, show “No newsletters found”. 【F:client/src/App.jsx†L113-L120】

### Per-day data refresh inside the rendered feed
6. Each `CalendarDay` calls `useSupabaseStorage(getNewsletterScrapeKey(payload.date), payload)` to hydrate from server-side storage and keep data live. The initial `payload` is used as the default, but the hook performs a **fetch to `/api/storage/daily/<date>`** to load persisted payloads and then updates local state. 【F:client/src/components/CalendarDay.jsx†L45-L69】【F:client/src/hooks/useSupabaseStorage.js†L49-L79】
7. While this storage read is in-flight, the UI shows a “Syncing…” badge in the day header. 【F:client/src/components/CalendarDay.jsx†L14-L24】

**Key client performance implication:** on a cold refresh without sessionStorage, the app waits on `/api/scrape` before rendering any feed content. Even after rendering, each day also independently reads `/api/storage/daily/<date>` for live payload sync. 【F:client/src/App.jsx†L47-L70】【F:client/src/components/CalendarDay.jsx†L45-L69】【F:client/src/hooks/useSupabaseStorage.js†L49-L79】

---

## Server-side flow (request handling)

### `/api/scrape` endpoint
1. **`/api/scrape`** parses JSON, validates optional `sources`, and calls `tldr_app.scrape_newsletters` with `start_date`, `end_date`, optional `sources`, and optional `excluded_urls`. 【F:serve.py†L42-L70】
2. `tldr_app.scrape_newsletters` delegates to `tldr_service.scrape_newsletters_in_date_range`. 【F:tldr_app.py†L10-L29】

### Core scrape + cache logic
3. `tldr_service.scrape_newsletters_in_date_range` parses and validates the date range, builds the inclusive list of dates, and computes `today_str`. 【F:tldr_service.py†L156-L170】
4. It loads **all cached daily payloads in one query** using `storage_service.get_daily_payloads_range(start_date, end_date)` and builds a `cache_map` keyed by date. 【F:tldr_service.py†L174-L176】
5. **Fast-path:** if **every date in range is cached AND none of the dates is today**, it returns cached payloads immediately with `source: "cache"`. 【F:tldr_service.py†L178-L188】
6. **Otherwise** it loops each date:
   - **If date is today:** always performs a live scrape (`scrape_date_range`) even if a cached payload exists; it builds an `excluded_urls` set from cached articles to avoid duplicates. It merges new results with cached state via `_merge_payloads` (preserving read/tldr/removed). 【F:tldr_service.py†L191-L218】
   - **If date is not today:** it uses cached payload if present; otherwise performs live scrape for that date. 【F:tldr_service.py†L221-L230】
7. It **persists** any dates that were freshly scraped to `daily_cache` via `storage_service.set_daily_payload`. 【F:tldr_service.py†L239-L242】
8. It returns `{ success, payloads, stats, source: "live" }` even when most dates are cached, as long as today was involved. 【F:tldr_service.py†L244-L254】

### Storage endpoints used by `useSupabaseStorage`
9. `/api/storage/daily/<date>` returns cached payloads from Supabase `daily_cache`. 【F:serve.py†L150-L165】【F:storage_service.py†L34-L49】

---

## End-to-end page refresh path (high-fidelity)

1. Browser loads `index.html` (React app). 【F:serve.py†L30-L35】
2. React `App` mounts → date range = today & two days ago → check sessionStorage TTL. 【F:client/src/App.jsx†L12-L44】
3. If no valid sessionStorage, client **POSTs** to `/api/scrape` and waits. 【F:client/src/App.jsx†L47-L70】【F:client/src/lib/scraper.js†L6-L15】
4. `/api/scrape` builds a full response by combining cached payloads and live scrapes, **but always live-scrapes today if today is in range**. This is the dominant latency source. 【F:serve.py†L42-L70】【F:tldr_service.py†L191-L218】
5. Once `/api/scrape` responds, the client renders `Feed` with daily payloads. 【F:client/src/App.jsx†L95-L112】【F:client/src/components/Feed.jsx†L3-L13】
6. Each `CalendarDay` **immediately fires** a `/api/storage/daily/<date>` request via `useSupabaseStorage`, even though the payload is already present from `/api/scrape`. This is a second network fan-out on refresh. 【F:client/src/components/CalendarDay.jsx†L45-L69】【F:client/src/hooks/useSupabaseStorage.js†L49-L79】

---

## Current caching behavior summary
- **Client:** 10-minute sessionStorage cache for the 3-day range (`today` and two days prior). If fresh, no `/api/scrape` call. 【F:client/src/App.jsx†L21-L45】
- **Server:** cache is always used for non-today dates, but **today always triggers a live scrape** even when a fresh cache exists. 【F:tldr_service.py†L178-L230】
- **Per-day read:** after initial render, each day requests `/api/storage/daily/<date>` anyway. 【F:client/src/components/CalendarDay.jsx†L45-L69】【F:client/src/hooks/useSupabaseStorage.js†L49-L79】

---

## Places the refresh can block today
- The initial render (feed) blocks on `/api/scrape` unless sessionStorage is warm. 【F:client/src/App.jsx†L47-L112】
- `/api/scrape` blocks on live scraping for today (network + parsing) even if cached data is fresh. 【F:tldr_service.py†L191-L218】
- Additional post-render read fan-out occurs as each `CalendarDay` independently calls `/api/storage/daily/<date>`. 【F:client/src/components/CalendarDay.jsx†L45-L69】【F:client/src/hooks/useSupabaseStorage.js†L49-L79】
