---
last_updated: 2026-01-23 09:46, a38c993
---
# Scrape-First Source of Truth (Option 1) Implementation Plan

## Two-Layer Brainstorm

### Layer 1: End-to-end behavioral nodes
1. **App bootstrap**: Decide the date range, load the feed dataset for that range from the canonical source, then render the feed.
2. **Scrape endpoint**: Assemble authoritative daily payloads for the range by merging cache + live scrape (today), and return the payloads as the canonical dataset.
3. **Storage persistence**: Persist daily payloads as a side effect of scrape (cache), but never used for immediate UI hydration in this mode.
4. **Client state hydration**: The feed uses the scrape response as authoritative; CalendarDay does not re-fetch storage for the same dates.
5. **State updates (read/tldr/removed)**: User actions update server-side state and local state; the next scrape response returns updated canonical payloads.
6. **Cross-tab consistency**: Optional broadcast or periodic refresh uses the same scrape-first read path to converge state.

### Layer 2: Fill in the details between lines
1. **App bootstrap details**
   - Session storage is only a short-term cache of the canonical scrape response.
   - The cache TTL can remain; it simply memoizes scrape responses, not a different data source.
2. **Scrape endpoint details**
   - For each date: if not today and cached, return cached; if today, merge cached + live scrape.
   - The returned payload list is already the authoritative state, including merged read/tldr/removed flags.
3. **Storage persistence details**
   - Storage is still written for caching and historical reads, but not used as a post-render rehydration source.
   - Storage endpoints remain for admin tools or future offline use but are not in the critical client render path.
4. **Client hydration details**
   - `CalendarDay` consumes the payload it is given and does not call storage reads on mount.
   - Local edits are optimistic and persisted by the existing write path; they do not trigger storage re-reads.
5. **State update details**
   - Read/TLDR/removed updates propagate via storage write and local state update.
   - When a user refreshes (or a periodic refresh occurs), `/api/scrape` returns the authoritative state with those updates incorporated from storage.
6. **Cross-tab consistency details**
   - Optional: listen for a shared event and trigger a range refresh via `/api/scrape`.
   - The refresh is always the same path; no conditional bypass or “just scraped” special casing.

---

# Scrape-First Source of Truth (Option 1) Implementation Plan

## Overview
Make `/api/scrape` the canonical read path for daily payloads and remove per-day storage rehydration from the client. Storage remains a persistence and cache layer, but no longer drives initial or per-day client hydration. This removes redundant fan-out reads without introducing timing-based flags or exceptions.

## Current State Analysis
- The app renders feed payloads from `/api/scrape` but then each `CalendarDay` triggers a storage read for the same date, resulting in a per-day fan-out.
- The `useSupabaseStorage` hook always rehydrates from storage for `newsletters:scrapes:<date>` keys, ignoring the initial payload as authoritative data.
- Server-side scrape logic already merges cached payloads and live results, then persists updated payloads for each date.

## Desired End State
- `/api/scrape` responses are treated as the authoritative dataset for the date range.
- The feed renders directly from scrape payloads without any immediate per-day storage reads.
- Storage endpoints remain as persistence and future read paths, but are not used for first render or per-day rehydration.
- The only read path for day payloads during refresh is `/api/scrape` (and optionally session storage of the same response).

### Key Discoveries
- The current client flow rehydrates each day via `/api/storage/daily/<date>` despite already having the payload from `/api/scrape`.
- The storage hook always fetches from storage for newsletter scrape keys, meaning the default payload is not treated as canonical.
- The server already merges cached and live results during scrape, meaning the response can be authoritative if the contract is updated.

## What We’re NOT Doing
- No “skip rehydration if just scraped” flags or timing-based exceptions.
- No new cache layers or speculative fallbacks.
- No redesign of storage persistence or schema.
- No API or UI changes unrelated to the scrape-first read path.

## Implementation Approach
Make the scrape response the single authoritative read source for the feed. Remove per-day storage rehydration from `CalendarDay` and keep storage writes for persistence. Any future consistency refresh uses the same scrape-first read path (optionally batched).

## Phase 1: Reframe canonical read source to `/api/scrape`

### Overview
Align the client contract so that the scrape response is the authoritative dataset used for initial render and subsequent refreshes.

### Changes Required

#### 1. Calendar day hydration
**File**: `client/src/components/CalendarDay.jsx`
**Changes**: Remove `useSupabaseStorage` for daily payloads; render directly from the provided payload.

```
- Remove: useSupabaseStorage(getNewsletterScrapeKey(payload.date), payload)
- Use: payload directly for articles/issues/date
```

#### 2. Storage hook usage for daily payloads
**File**: `client/src/hooks/useSupabaseStorage.js`
**Changes**: Leave functionality in place for non-scrape keys; remove usage for per-day feed hydration.

```
- No changes required if CalendarDay no longer uses daily storage keys
```

#### 3. Client data flow alignment
**File**: `client/src/App.jsx`
**Changes**: Ensure the feed consumes scrape results as authoritative and avoid any post-render data-source swaps.

```
- Keep scrape results as single source for render
- Session storage cache remains as memoized scrape response
```

### Success Criteria

#### Automated Verification
- [ ] `source ./setup.sh` (environment validation)
- [ ] `source ./setup.sh && start_server_and_watchdog` (server start)
- [ ] `curl http://localhost:5001/api/scrape` (API responds)

#### Manual Verification
- [ ] Refresh the app and verify only the initial `/api/scrape` request occurs (no per-day `/api/storage/daily/<date>` fan-out).
- [ ] Read/tldr/removed toggles persist and remain visible after refresh.
- [ ] No regressions in feed rendering or day grouping.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before any additional changes.

---

## Phase 2: Optional convergence path (if needed)

### Overview
If cross-tab or external updates require convergence, use a single range refresh from `/api/scrape` instead of per-day storage reads.

### Changes Required

#### 1. Refresh trigger strategy
**File**: `client/src/App.jsx` (or a top-level hook)
**Changes**: Add an explicit refresh trigger that re-runs `/api/scrape` for the active range (no per-day reads).

```
- Add: explicit refresh pathway that re-fetches scrape range
- Keep: no per-day storage rehydration
```

### Success Criteria

#### Automated Verification
- [ ] Same as Phase 1

#### Manual Verification
- [ ] Trigger refresh and confirm a single `/api/scrape` request updates the feed.
- [ ] No per-day storage reads occur during refresh.

---

## Testing Strategy

### Unit Tests
- None required unless existing coverage requires updates.

### Integration Tests
- Verify `/api/scrape` returns expected payloads for a date range and continues to merge cached + live data.

### Manual Testing Steps
1. Refresh the app and observe network: only `/api/scrape` is called for data, with no per-day `/api/storage/daily/<date>` requests.
2. Toggle read/tldr/removed states, refresh, and confirm persistence through scrape.
3. Confirm no UI regressions in CalendarDay rendering (headers, badges, fold state).

## References
- Related research: `26-01-22-speed-up-app-refresh/research.md`
- Key files: `client/src/App.jsx`, `client/src/components/CalendarDay.jsx`, `client/src/hooks/useSupabaseStorage.js`, `tldr_service.py`
