---
name: server/adapters
description: Adapter factory and logic for individual newsletter sources.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Server: Adapters

The `NewsletterScraper` uses adapter classes (e.g., `TLDRAdapter`, `HackerNewsAdapter`) via a factory. 
See the call graph in [Scraping Pipeline](scraping-pipeline.md) for execution details.
