---
created: 2025-12-19
status: FINALIZED
last_updated: 2025-12-18 23:35
---
# Verdict: Fix Cache-Scrape Edge Case

After analyzing the [Original Plan](plan.md), the [Review](plan.review.md), and the relevant codebase (`client/src/lib/scraper.js`, `tldr_service.py`, `newsletter_scraper.py`), I have concluded that the **Review** provides the correct assessment and the **Original Plan** is fundamentally flawed and dangerous.

## Decision
**Adopt the Review's recommendations.**

The Original Plan must **NOT** be implemented as written.

## Rationale

### 1. Critical Data Loss (Verified)
The Original Plan proposes that the server return "only new articles" for "today".
Analysis of `client/src/lib/scraper.js` confirms that `mergeWithCache(payloads)` iterates over the *incoming* (new) articles and tries to match them with existing ones to preserve state.
Crucially, it **does not** retain existing articles that are missing from the incoming payload.
**Consequence:** If the server returns only new articles, **all previously scraped articles for today will be deleted** from the client's cache, taking their `read` / `removed` / `tldr` state with them.

### 2. Incorrect Statistics (Verified)
The server calculates `stats` based on the `all_articles` list it collected during the scrape.
If `excluded_urls` prevents existing articles from being added to `all_articles`, the `stats` returned to the client will reflect only the *delta* (e.g., "1 article found") rather than the day's total.
**Consequence:** The UI will display incorrect article counts and "dates processed" stats.

### 3. Inefficient Re-scraping (Verified)
The Original Plan's client modification (`isRangeCached` returns `false` if "today" is included) forces the server to re-scrape the entire date range.
The server currently has no logic to skip scraping for dates that are already cached.
**Consequence:** Requesting a range like `[Yesterday, Today]` will re-scrape `Yesterday` unnecessarily, wasting resources and potentially hitting rate limits, even if `Yesterday` is fully cached.

## Finalized Implementation Path

The implementation should follow the Review's "Server-Side Union" approach:

### 1. Server-Side (`tldr_service.py` / `newsletter_scraper.py`)
- **Smart Scrape Orchestration:**
    - For **Past Dates** in the requested range: Check `storage_service` first. If a payload exists, use it directly instead of triggering a live scrape.
    - For **Today**:
        1.  Fetch the existing daily payload from `storage_service` (if any).
        2.  Extract existing URLs to a set.
        3.  Pass these URLs as `excluded_urls` to the adapters (to save bandwidth/processing).
        4.  Perform the live scrape for today.
        5.  **Union the results:** Combine the `existing articles` (from storage) with the `new articles` (from the live scrape).
        6.  Recalculate `stats` based on the combined set.
        7.  Return the **full** payload (cached + new) to the client.

### 2. Client-Side (`client/src/lib/scraper.js`)
- **Force Server Call for Today:**
    - Update `isRangeCached` to return `false` if "today" is in the range (handling timezone normalization carefully).
- **No Merge Logic Changes Needed:**
    - Because the server now returns the *full* complete list for today, the existing `mergeWithCache` logic (which overwrites the payload while preserving metadata for matching URLs) will work correctly without modification. It will see the old articles (and preserve their state) and see the new articles (and add them).

### 3. Normalization
- Ensure "Today" detection uses strict date-only comparison (YYYY-MM-DD) to avoid timezone bugs where "today" on the client differs from "today" on the server.
