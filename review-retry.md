---
last_updated: 2025-12-26 07:54
---
Findings
- [High] `summarizer.py:153-196` – The new `@util.retry()` wrapper never triggers a second run. `util.retry` only retries on `requests.Timeout`/`ConnectionError`/`IOError`, but `scrape_url` catches those inside its loop, aggregates them, then raises a `RuntimeError` or `HTTPError`. None of those are in `RETRIABLE_EXCEPTIONS`, so the decorator sees no retriable exceptions and behavior is unchanged. To actually retry, let those transport exceptions bubble, or include the raised exception types in `RETRIABLE_EXCEPTIONS`, or move the retry to the individual fetch calls.

Open questions
- Should HTTP status failures (e.g., 429/5xx from Jina/Firecrawl) also retry, or only transport-level failures?

Notes
- No tests run (not requested).
