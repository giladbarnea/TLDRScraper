---
last_updated: 2025-11-29 20:26, a7f8876
---
# Troubleshooting Summary: TLDR & Remove Buttons

**Date:** 2025-11-29
**Context:** Debugging and fixing "Remove" and "TLDR" button interactions in a React 19 application, verified with Playwright.

## Key Learnings & Solutions

### 1. Visibility in Tests vs. Visuals
*   **Issue:** Playwright's `expect(locator).not_to_be_visible()` failed even when the element had `opacity-0` and `max-h-0`. While visually hidden to a user, the element remained in the DOM and potentially interactable or "visible" to the test runner.
*   **Solution:** Explicitly added the Tailwind `invisible` class (CSS `visibility: hidden`) to the collapsed state.
    *   *Code:* `'max-h-0 opacity-0 ... invisible'`
*   **Takeaway:** Animation-based hiding (opacity/height) is insufficient for strict automated visibility checks. Always pair with `visibility: hidden` or `display: none` (via `invisible` or `hidden`) once the exit animation completes or as part of the collapsed state.

### 2. Test Stability & Selectors
*   **Issue:** Initial tests using generic selectors like `.first` or `nth(0)` were flaky. Interacting with the list (e.g., removing an article) caused re-sorting, making the `nth(0)` element swap mid-test, leading to "element detached" or "element not visible" errors.
*   **Solution:** Instrumented `ArticleCard` with data-driven test IDs: `data-testid="article-card-{url}"`.
*   **Takeaway:** Never rely on index-based selectors for mutable lists. Use unique, stable identifiers derived from the data itself.

### 3. State Synchronization
*   **Observation:** Extensive logging confirmed that React state (`expanded`, `isRead`) was updating correctly, but the UI test failed.
*   **Resolution:** The discrepancy was purely in how the DOM represented that state to the test runner. Trusting the logic logs helped isolate the problem to the *presentation layer* (CSS/DOM) rather than the *business logic* (React hooks).

## Helpful Techniques

1.  **Deterministic Test Environment:**
    *   Created `clean_today.py` to wipe the specific day's cache in Supabase before every test run. This eliminated "state pollution" from previous aborted runs.

2.  **Lifecycle Tracing:**
    *   Added temporary, high-verbosity console logs (`[ArticleCard] Render`, `[useSummary] toggle`) to map the exact sequence of re-renders and state updates. This proved that the click handlers were firing and state was setting, narrowing the bug scope to the rendering/CSS.

3.  **The "Invisible" Fix:**
    *   Using `invisible` is a robust pattern for collapsible content. It preserves layout structure better than `hidden` (display: none) during transitions if managed correctly, but ensures the element is strictly "gone" for accessibility and testing when collapsed.
