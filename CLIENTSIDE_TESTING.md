# Client-side Testing Notes

## LocalStorage-focused coverage

- **Baseline assumption**: each Playwright test begins with an empty `localStorage`. Tests explicitly verify this at startup so hidden persisted state does not mask regressions.
- **Scrape result caching**: submitting the "Scrape TLDR Newsletters" form issues a `POST /api/scrape` request. On success the UI normalizes the requested date, serializes the returned issues and articles, and writes them to `localStorage` under the key pattern `tldr:scrapes:<ISO date>`. Tests provide a mocked API payload, trigger the scrape action, and assert the stored payload contains the expected issue/article data for that date.
- **Issue read state**: pressing "Mark as Read" on an issue collapses it and records the read status in `localStorage` using the `tldr-read-issues` map keyed by `<ISO date>-<category>`. Tests reuse the mocked scrape payload, activate the control, and confirm the map reflects the newly read issue.

## Debug-first Playwright philosophy

Playwright flows can be difficult to troubleshoot. Each scenario is wrapped in `test.step` phases with descriptive messages so failures report where the run was before the assertion. When inspecting artifacts or CI output these step names, coupled with explicit logging of the target date, issue key, and stored payload, make it clear which stage mutated `localStorage` and what data the browser held at that moment.
