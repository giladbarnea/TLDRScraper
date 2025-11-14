---
last_updated: 2025-11-14 13:25, ff36273
---
# Bugs Encountered

## Configuration

### `section_emoji_enabled` field not wired up
- `newsletter_config.py:NewsletterSourceConfig.section_emoji_enabled` exists but is never accessed. Emoji parsing in `tldr_adapter.py:_parse_markdown_structure()` runs unconditionally regardless of config value.

## Scraping

### Failed fetching content
- [ ] https://olmocr.allen.ai/blog. Content was returned with no error but empty-ish. Needs JS enabled (25-10-26 7:45AM IST)
- [ ] https://www.gatesnotes.com/home/home-page-topic/reader/three-tough-truths-about-climate Empty content