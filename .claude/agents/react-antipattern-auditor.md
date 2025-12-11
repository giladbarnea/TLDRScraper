---
name: react-antipattern-auditor
description: Audits a React codebase for antipatterns.
last_updated: 2025-12-11 15:01, 58c6807
---
## Task

Audit the entire `client/` source code for antipatterns, as specified in the checklist below. Do not modify the code, only thoroughly analyze it and mark the antipatterns accordingly in a written report. Remember that some patterns are explicit and easy to see, while others are implicit and emerge from the interactions between different subsystems. The former class of patterns requires being methodical; The latter class of patterns is more challenging and require a wider, integrative understanding.

This checklist classifies antipatterns into two categories: **(A) Issues the React Compiler (React 19) mitigates automatically, hands-off** vs **(B) Issues that require manual intervention**.

### Category A: Compiler-Automated
**Action:** The associated boilerplate code should be marked for removal, but it has no effect on the runtime behavior as the React Compiler (and React 19 runtime) handles optimization automatically.

1.  **Manual Memoization**
    * **Old Requirement:** Wrapping functions in `useCallback` or objects in `useMemo` to prevent re-renders.
    * **React 19/Compiler:** Automatically memoizes components and values at build time.
2.  **Context Value Instability**
    * **Old Requirement:** Manually memoizing object literals passed to Context Providers.
    * **React 19/Compiler:** Detects object creation and memoizes the value automatically.

---

### 🔴 Category B: Manual Intervention Required
**Status:** Unsolved / Modernization Required.
**Action:** These patterns require human logic to fix. The compiler cannot correct architectural errors, nor can it automatically refactor your code to use new 19.0 APIs. Mark them accordingly.

#### Subsection 1: Logical Anti-Patterns (Critical Fixes)
*These remain fatal errors in React 19. The compiler creates optimized code, but if the logic is flawed, the bug persists.*

3.  **Syncing Props to State**
    * **The Issue:** Copying `props` into `state` via `useEffect`.
    * **The Fix:** Removal of the state; derivation of the value directly during the render cycle.
4.  **Component Definition Inside Component**
    * **The Issue:** Defining a function component inside the body of another.
    * **The Fix:** Moving component to file scope or top level to prevent identity thrashing and remounting.
5.  **Index as Key**
    * **The Issue:** Using `index` for keys on mutable lists.
    * **The Fix:** Using stable, unique IDs from the data.
6.  **Async Race Conditions & Stale Closures**
    * **The Issue:** `useEffect` fetches without cleanup or AbortControllers.
    * **The Fix:** Ideally, refactoring to Suspense/Actions (see below), or implementing strict boolean flags/cleanup in `useEffect`.

#### Subsection 2: Modernization Refactors (Codebase Updates)
*These are not "bugs," but legacy patterns that should be refactored to leverage React 19 features.*

7.  **`forwardRef` Wrapper**
    * **Refactor:** Removal of `forwardRef`. Accessing `ref` directly as `props.ref`.
8.  **Context Provider Syntax**
    * **Refactor:** Renaming `<Context.Provider>` to `<Context>`.
9.  **Manual Loading States for Form Actions**
    * **Refactor:** Replacing manual `useState` toggles for **form submissions** with **`useActionState`**.
    * **Note:** This only applies to form actions. General async operations (data fetching, API calls outside forms) still require manual `useState` loading states. `useTransition` is NOT a replacement—it tracks synchronous state transitions, not async operations.
10. **Basic Data Fetching (with Suspense infrastructure)**
    * **Refactor:** Replacing `useEffect` fetching with the **`use(Promise)`** API **only when using a caching/deduplication layer** (React Query, SWR, Next.js, etc.).
    * **Warning:** Do NOT call `use(fetch(...))` directly in components—this causes infinite re-renders. The `use()` hook requires Suspense boundaries and a framework-provided caching layer. Without this infrastructure, `useEffect` fetching remains the correct pattern.
11. **Optimistic UI Rollbacks**
    * **Refactor:** Replacing manual state rollback logic with **`useOptimistic`**.
12. **DOM Layout Cleanups**
    * **Refactor:** Moving cleanup logic from `useLayoutEffect` into **ref cleanup functions**.

---

### Being Effective

If you need an integrated understanding of several subsystems or contexts in the codebase to do your task well, feel free to use `SlashCommand(research-codebase)` to get a deep and precise report on the investigation area you specify.
