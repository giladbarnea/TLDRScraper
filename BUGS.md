---
last-updated: 2025-10-31 18:58, c08559f
---
# Bugs Encountered

## Scraping

### Failed fetching content
- [ ] https://olmocr.allen.ai/blog. Content was returned with no error but empty-ish. Needs JS enabled (25-10-26 7:45AM IST)
- [x] https://www.wsj.com/tech/ai/ai-race-tech-workers-schedule-1ea9a116. WSJ consistently errors when scraped even with Jina AI. (25-10-26 7:45AM IST) **FIXED**: Added Firecrawl as conditional fallback in scraping cascade. Tries free methods first (curl_cffi, jina_reader), then falls back to Firecrawl only when needed. (25-10-31)
- [ ] https://www.gatesnotes.com/home/home-page-topic/reader/three-tough-truths-about-climate Empty content