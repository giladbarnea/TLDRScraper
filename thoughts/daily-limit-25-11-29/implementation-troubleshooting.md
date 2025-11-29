# Troubleshooting Log: Remove & TLDR Button Functionality

**Date:** 2025-11-29
**Focus:** Fixing bugs where "Remove" and "TLDR" buttons do not work as expected.

## 1. Remove Button (Resolved)

### Actions
- **Instrumentation:** Added `data-testid` attributes to `ArticleCard.jsx` (`article-card-{url}`, `article-title-{url}`, `remove-button-{url}`) to enable stable testing selectors.
- **Data Cleanup:** Created `clean_today.py` to wipe `daily_cache` for the current date in Supabase, ensuring clean test runs.
- **Testing:** Developed `test_remove_button.py` using Playwright.
  - **Initial Failures:** Test failed because the article list re-sorted immediately upon removal (moving the removed article to the bottom), causing the `nth(0)` selector to target a different, non-removed article.
  - **Fix:** Updated test to use stable selectors based on the specific Article URL.
- **Verification:** The test now consistently passes. It verifies:
  1.  Clicking "Remove" adds the `opacity-50` class.
  2.  The "Remove" button disappears.
  3.  State persists after a page reload.
  4.  Clicking the card body restores the article (removes `opacity-50` and shows the button).

### Status
✅ **Fixed & Verified.**

## 2. TLDR Button (In Progress)

### Actions
- **Testing:** Created `test_tldr_button.py` to verify the "TLDR" -> "Close" flow.
- **Debugging:**
  - Added extensive logging to `ArticleCard.jsx` and `useSummary.js` to track `expanded`, `isAvailable`, and `status` states.
  - Logs confirm `handleExpand` and `toggleTldrWithTracking` are called.
  - Logs show `expanded` toggling from `false` to `true`.
- **Issue:** The test fails at the final step: `expect(content_div).not_to_be_visible()`.
  - The "Close" button is successfully clicked (verified via logs).
  - However, the content `div` (with class `.prose`) remains visible in the DOM.
- **Attempts:**
  - Used `force=True` on Playwright clicks.
  - Used `element.evaluate("el => el.click()")` to bypass potential overlays.
  - Added debug prints for the container's class list. Curiously, `container.get_attribute('class')` returned an empty string or null in some attempts, which is unexpected given the conditional rendering logic:
    ```jsx
    className={`
      transition-all duration-500 ...
      ${tldr.expanded && tldr.html ? 'opacity-100 ...' : 'max-h-0 opacity-0 ...'}
    `}
    ```

### Open Questions
1.  **State Sync:** Why does the UI not reflect the `expanded: false` state after the "Close" click, despite logs suggesting the toggle logic runs?
2.  **Missing Classes:** Why did the debug probe for the container's class attributes return empty? This suggests either a locator issue or a fundamental rendering issue where the classes aren't being applied.
3.  **Visibility Transition:** The visibility toggle relies on CSS classes (`max-h-0`, `opacity-0`). If these aren't applied, Playwright correctly reports the element as still visible.

### Current State
❌ **Failing.** The "Close" action does not hide the TLDR content in the test environment.