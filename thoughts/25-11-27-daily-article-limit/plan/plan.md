---
last_updated: 2025-11-27 20:53, 28f11ac
---
# Plan: Daily Article Limit & Smart Distribution Strategy

**Status:** Proposed  
**Date:** 2025-11-21 (Updated)  
**Goal:** Implement a daily cap on displayed articles (default: 50) using a Max-Min Fairness algorithm.  
**Key Architecture Shift:** "Store Super-Set, Serve Sub-Set". The database stores all scraped candidates. The API filters and trims them on-the-fly for the client.

## 1. Problem Statement

Currently, the scraper fetches all available articles for a given date range. This leads to:

1. **Cognitive Overload:** Users are overwhelmed by too many articles.
2. **Uneven Distribution:** Naive limits fail on unequal source distributions.
3. **Persistence of Noise:** "Removed" articles clutter the pipeline.
4. **Inefficiency:** Changing limits or backfilling removed articles currently requires re-scraping the web.

## 2. The Solution: Max-Min Fairness + Super-Set Storage

We will implement a per-day limit (default 50) using Max-Min Fairness. Crucially, we will decouple **Storage** from **Presentation**.

- **Storage:** Saves 100% of scraped articles. Acts as a "Raw Candidate Store".
- **Presentation:** Reads the store, filters "removed" items, applies the limit algorithm, and returns the "Top K" to the user.

### Algorithm Logic (Max-Min Fairness)

Given a `TotalLimit` (e.g., 50) and a set of sources with available article counts $[C_{1}, C_{2}, \ldots C_{n}]$:

1. **Filter:** Exclude articles marked as `removed`.
2. **Iterate:** Calculate `FairShare`. Identify "Fewers" (Count $\le$ FairShare). Allocate full count to Fewers. Distribute remainder to "Morers".

## 3. Ranking Strategies (Per-Source Top-K)

When trimming the Super-Set to the Display-Set, we rely on specific sorting priorities enforced by Adapters:

| Source Type       | Sorting Signal  | Implementation Strategy           |
| :---------------- | :-------------- | :-------------------------------- |
| Hacker News       | Score           | `(points * 2) + comments` (Desc). |
| TLDR              | Editorial Order | Preserve original section order.  |
| Blogs/Aggregators | Date/Score      | Reverse Chronological or Score.   |

## 4. Architecture Changes

### New Flow: "Sync & Serve"

1. **Scrape Candidates:** Fetch all available articles from external sources (Raw).
2. **Load Context:** Fetch existing `daily_cache` from Supabase (to preserve user states like `read`, `removed`, `tldr`).
3. **Merge:** Combine Raw + Context.
    - **Rule:** Keep existing objects (preserve IDs/States), add new ones.
4. **Save Super-Set:** UPSERT the full merged list to Supabase. (This is the "Quick Win" - we now have a cache of everything).
5. **Filter:** In memory, exclude `removed=True` items.
6. **Distribute:** Run Max-Min Fairness on remaining counts.
7. **Trim:** Slice lists to calculated quotas.
8. **Return:** Send only the trimmed list to the client.

## 5. Implementation Phases

### Phase 1: The Distributor (Pure Logic)

- **File:** `newsletter_limiter.py`
- **Function:** `calculate_quotas(counts, limit)`
- **Task:** Implement the waterfilling algorithm.

### Phase 2: Adapter Standardization

- **Task:** Ensure `scrape_date` in all adapters returns lists sorted by priority.

### Phase 3: Integration (The Sync Engine)

- **File:** `newsletter_scraper.py`
- **Function:** `scrape_date_range`
- **Logic:** Implement the Merge -> Save Super-Set -> Limit -> Return flow.

## 6. Technical Considerations

- **Latency:** The "Scrape" endpoint might take slightly longer due to the DB upsert before return, but subsequent "Load" requests are instant.
- **Rate Limits:** We effectively snapshot the web state. If we change the limit to 100 later, we serve it from DB, zero external calls.
- **Backfilling:** If a user removes an article, the next refresh can instantly pull the "next best" from the DB Super-Set without re-scraping.

## 7. Next Steps

1. Implement `newsletter_limiter.py`.
2. Refactor `newsletter_scraper.py` to handle the Merge-Save-Limit flow.
