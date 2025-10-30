---
last-updated: 2025-10-25 06:42, eea904d
---

# Client-side Testing Notes

## LocalStorage-focused coverage

- **Baseline assumption**: each Playwright test begins with an empty `localStorage`. Tests explicitly verify this at startup so hidden persisted state does not mask regressions.
- **Scrape result caching**: submitting the "Scrape TLDR Newsletters" form issues a `POST /api/scrape` request. On success the UI normalizes the requested date, serializes the returned issues and articles, and writes them to `localStorage` under the key pattern `tldr:scrapes:<ISO date>`. Tests provide a mocked API payload, trigger the scrape action, and assert the stored payload contains the expected issue/article data for that date.

## Debug-first Playwright philosophy

Playwright flows can be difficult to troubleshoot. Each scenario is wrapped in `test.step` phases with descriptive messages so failures report where the run was before the assertion. When inspecting artifacts or CI output these step names, coupled with explicit logging of the target date, issue key, and stored payload, make it clear which stage mutated `localStorage` and what data the browser held at that moment.
