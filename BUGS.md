---
last-updated: 2025-11-14 11:00, 2c729d0
---
# Bugs Encountered

## Configuration

- [ ] `section_emoji_enabled` config field never checked. Emoji parsing always active in tldr_adapter.py:_parse_markdown_structure()

## Scraping

### Failed fetching content
- [ ] https://olmocr.allen.ai/blog. Content was returned with no error but empty-ish. Needs JS enabled (25-10-26 7:45AM IST)
- [ ] https://www.gatesnotes.com/home/home-page-topic/reader/three-tough-truths-about-climate Empty content