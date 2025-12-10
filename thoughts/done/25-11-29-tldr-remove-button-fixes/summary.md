---
status: completed
last_updated: 2025-12-10 12:50, 9b5c65e
---
# TLDR & Remove Button Fixes

Fixed unresponsive TLDR/Remove buttons in ArticleCard. Root causes: collapsed content used opacity/height animations without `visibility: hidden`, making elements "visible" to Playwright; test selectors used fragile `nth(0)` on mutable lists. Solutions: added Tailwind `invisible` class to collapsed states; instrumented cards with stable `data-testid="article-card-{url}"`. Restored `markTldrHidden`/`unmarkTldrHidden` calls in toggle handler. Cleaned up duplicate test scripts, issueDate workaround duplication, debug logging in hooks, and dangerous `clean_today.py` script with no env guards.

COMPLETED SUCCESSFULLY.
