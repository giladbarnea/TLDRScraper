---
last_updated: 2026-05-02 10:48
---

# Server: Articles and Data Structures

[→ Client: Articles & Lifecycle](../client/articles-and-lifecycle.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

## Data Structures

Client payload shape, embedded article state, and client-side persistence tiers are documented in `client/STATE_MACHINES.md`.

### Issue

```typescript
{
  date: string,              // "2024-01-01"
  source_id: string,         // "tldr_tech"
  category: string,          // "TLDR Tech"
  title: string | null,      // Issue title
  subtitle: string | null    // Issue subtitle
}
```

### ScrapeRequest (POST /api/scrape)

```typescript
{
  start_date: string,        // "2024-01-01"
  end_date: string,          // "2024-01-03"
  sources?: string[],        // ["tldr_tech", "hackernews"] (optional)
  excluded_urls?: string[]   // canonical URLs to exclude (optional)
}
```

### ScrapeResponse (API response)

```typescript
{
  success: boolean,
  articles: Article[],       // All articles (flattened); see client/STATE_MACHINES.md for shape
  issues: Issue[],           // All issues
  stats: {
    total_articles: number,
    unique_urls: number,
    dates_processed: number,
    dates_with_content: number,
    network_fetches: number,
    cache_mode: string
  },
  output: string             // Markdown formatted output
}
```

---

## Key Algorithms

### 1. URL Deduplication (newsletter_scraper.py:231)

**Same-day dedup** — applied across all sources within a single scrape run:

```python
# Deduplicate articles across sources using canonical URLs
url_set = set()
all_articles = []

for article in scraped_articles:
    canonical_url = util.canonicalize_url(article['url'])
    article['url'] = canonical_url

    if canonical_url not in url_set:
        url_set.add(canonical_url)
        all_articles.append(article)
```

**History dedup** — opt-in per source via `NewsletterSourceConfig.deduplicate_across_history = True` (currently enabled for trendshift). Filters articles already seen on any previous date, persisting new URLs into the `seen_urls` DB table:

```python
# After adapter.scrape_date(), before appending to result
if config.deduplicate_across_history:
    canonical_urls = [util.canonicalize_url(a["url"]) for a in scrape_result["articles"]]
    history_deduplicated_urls = storage_service.filter_new_urls_for_history_dedup(
        source_id=config.source_id,
        first_seen_date=date_str,
        canonical_urls=canonical_urls,
    )
# filter_new_urls_for_history_dedup: queries seen_urls, returns new-only set, upserts them
# Falls back to pass-through if seen_urls table is unavailable (probe retries every 30s)
```

---
