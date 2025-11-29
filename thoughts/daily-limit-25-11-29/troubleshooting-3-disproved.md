# Troubleshooting 3: Correcting False Positives

**Date:** 2025-11-29
**Focus:** Correcting factual errors and "false positive" assumptions found in previous documentation (`headless_playwright_guide.md`, `implementation-troubleshooting.md`) based on new findings.

## 1. Disproved: "Clicking Requires force=True"
*   **Previous Claim:** `headless_playwright_guide.md` (Rule #2) and `implementation-troubleshooting.md` (Actions) suggested that using `.click(force=True)` or `evaluate("el.click()")` was the primary solution for interaction failures in headless mode.
*   **New Reality:** The root cause of the "Close" button failure was not a headless interaction limitation, but a **state/visibility mismatch**. The element was being clicked successfully, but the *result* (hiding the content) wasn't verifiable because `opacity: 0` does not satisfy Playwright's `not_to_be_visible()` assertion.
*   **Correction:** While `force=True` bypasses pointer-events checks (useful for overlays), it is a band-aid. The correct fix is ensuring the DOM state accurately reflects visibility (using `visibility: hidden` or `display: none`), which allows standard `.click()` to work and assertions to pass without hacks.

## 2. Disproved: "Wait for Selector is Enough"
*   **Previous Assumption:** Implicit in the initial tests was that `page.wait_for_selector()` followed by an action is sufficient.
*   **New Reality:** In a dynamic list (like `ArticleList`), removing an item causes the DOM to re-index. A generic selector (`nth(0)`) fetched *before* the re-index becomes stale or points to the wrong element *after* the re-index.
*   **Correction:** Use stable, data-attribute-based selectors (`data-testid="article-{id}"`) that persist regardless of list order or re-rendering.

## 3. Disproved: "Opacity 0 = Invisible"
*   **Previous Assumption:** Transitions using `opacity-0 max-h-0` are sufficient to "hide" an element for test assertions.
*   **New Reality:** Playwright (and screen readers) may still consider an element with `opacity: 0` as "visible" or at least present in the accessibility tree.
*   **Correction:** `expect(locator).not_to_be_visible()` strictly requires `display: none`, `visibility: hidden`, or a detached element. Visual-only hiding (opacity) is a false positive for "invisibility" in automated testing.

## Summary of Updates
1.  **Stop relying on `force=True` as a first resort.** Fix the underlying visibility/overlay issue.
2.  **Stop using index-based selectors** for mutable lists.
3.  **Always pair CSS transitions** (opacity/height) with `visibility: hidden` (`invisible`) for the collapsed state to ensure testability and accessibility.
