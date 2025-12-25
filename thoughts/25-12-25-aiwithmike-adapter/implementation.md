---
last_updated: 2025-12-25 09:46
---
# Mathy AI Adapter — Implementation

## Source Details

- **RSS Feed**: `https://aiwithmike.substack.com/feed`
- **source_id**: `aiwithmike`
- **Display name**: "Mathy AI"
- **sort_order**: 21

## Implementation

Used the same techniques as `ByteByteGoAdapter` and `LennyNewsletterAdapter`:
- RSS fetch via `requests` + `feedparser`
- Date filtering on `entry.published_parsed`
- Summary truncation to 200 chars
- Standard `_normalize_response()` from base class

## Files Changed

| File | Change |
|------|--------|
| `adapters/aiwithmike_adapter.py` | New adapter class |
| `newsletter_config.py` | Added config entry |
| `newsletter_scraper.py` | Added factory branch |

## Verified

All automated checks passed. Manual verification confirmed articles appear in Preview deployment UI under "Mathy AI" category.
