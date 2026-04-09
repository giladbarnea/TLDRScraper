---
last_updated: 2026-04-09 09:14, 81662be
---
# Overlays & Gestures Domain — Code Quality Findings

**Scope:** ZenModeOverlay (ArticleCard.jsx), DigestOverlay.jsx, useScrollProgress.js, usePullToClose.js, useOverscrollUp.js

**Analysis Date:** 2026-04-08

---

## Executive Summary

The Overlays & Gestures domain exhibits significant code duplication (~70% overlap between ZenModeOverlay and DigestOverlay), mixed concerns, and several maintenance anti-patterns. The primary opportunity is to extract a shared overlay foundation that would eliminate duplication and centralize overlay behavior.

---

## HIGH VALUE OPPORTUNITIES

### 1. **Massive Code Duplication Between Overlays** ⭐⭐⭐

**Location:**
- `client/src/components/ArticleCard.jsx:31-122` (ZenModeOverlay)
- `client/src/components/DigestOverlay.jsx:7-108`

**Finding:**

ZenModeOverlay and DigestOverlay share ~70% identical code:

**Identical structures:**
1. **Header layout** — same flex layout, padding, transition classes
2. **Scroll detection** — both track `hasScrolled` with identical `scrollTop > 10` check
3. **Escape key handler** — identical `document.addEventListener('keydown', handleEscape)`
4. **Body scroll lock** — both set `document.body.style.overflow = 'hidden'`
5. **Progress bar rendering** — same 2px bar with `scaleX(${progress})` transform
6. **Overscroll completion zone** — identical CheckCircle icon with same opacity/scale transforms
7. **Content transform** — same `translateY(-${overscrollOffset * 0.4}px)` calculation
8. **Prose styling classes** — identical 15+ class string on content div

**Duplication metrics:**
- ZenModeOverlay: ~92 lines
- DigestOverlay: ~101 lines
- Shared logic: ~60-70 lines (~65-70%)

**Impact:** Any change to overlay behavior (e.g., new gesture, header redesign) requires updating two files identically. High risk of divergence bugs.

**Recommendation:** Extract a `BaseOverlay` component or `useOverlayFoundation` hook that encapsulates:
- Body scroll lock management
- Escape key handling
- Scroll progress tracking
- hasScrolled state
- Header scaffolding
- Progress bar rendering
- Overscroll completion zone rendering

---

### 2. **ZenModeOverlay Embedded in ArticleCard.jsx** ⭐⭐

**Location:** `client/src/components/ArticleCard.jsx:31-122`

**Finding:**

ZenModeOverlay is a 92-line component defined inside ArticleCard.jsx, which is already 250+ lines. This violates single-responsibility principle and makes navigation harder.

**Problems:**
- ArticleCard.jsx handles: card rendering, swipe gestures, selection, AND overlay definition
- DigestOverlay gets its own file, but ZenModeOverlay doesn't — inconsistent
- Searching for "ZenModeOverlay" across the codebase requires looking inside ArticleCard.jsx

**Recommendation:** Move ZenModeOverlay to `client/src/components/ZenModeOverlay.jsx`.

---

### 3. **Ref Syncing Anti-Pattern in Gesture Hooks** ⭐⭐

**Location:**
- `client/src/hooks/usePullToClose.js:9-12`
- `client/src/hooks/useOverscrollUp.js:10-13`

**Finding:**

Both hooks duplicate this pattern:

```javascript
const [pullOffset, setPullOffset] = useState(0)
const pullOffsetRef = useRef(0)

useEffect(() => {
  pullOffsetRef.current = pullOffset
}, [pullOffset])
```

This syncs state to a ref so `handleTouchEnd` can read the current value without being a dependency of the effect.

**Problems:**
- This is a known React anti-pattern (state + ref duplication)
- Both hooks have identical logic — clear opportunity for extraction
- Touch event handlers need the ref, but the rendering needs the state

**Recommendation:** Extract a custom hook:

```javascript
function useTrackedState(initialValue) {
  const [value, setValue] = useState(initialValue)
  const ref = useRef(initialValue)

  useEffect(() => {
    ref.current = value
  }, [value])

  return [value, setValue, ref]
}
```

Or use `useRef` directly with force-updates if the rendering pattern allows.

---

### 4. **Threshold Inconsistency Between Gesture Hooks** ⭐

**Location:**
- `client/src/hooks/usePullToClose.js:45` — uses `threshold` directly (default 80)
- `client/src/hooks/useOverscrollUp.js:54` — uses `threshold * 0.5` (default 60 → triggers at 30)

**Finding:**

Both hooks have a `threshold` prop, but:
- `usePullToClose` triggers when `pullOffset > threshold` (user configures absolute value)
- `useOverscrollUp` triggers when `overscrollOffset >= threshold * 0.5` (user configures 2× the trigger point)

**Problems:**
- Same parameter name, different semantics — confusing API
- The `* 0.5` multiplier is undocumented
- Overscroll threshold of 60 actually triggers at 30px — misleading

**Recommendation:** Standardize threshold semantics:
1. Document what `threshold` means for each hook
2. Consider renaming OverscrollUp's parameter to `triggerAt` or using a consistent interpretation

---

## MEDIUM VALUE OPPORTUNITIES

### 5. **Magic Numbers Without Context**

**Location:** Scattered across all files

**Examples:**
- `scrollEl.scrollTop > 10` — why 10? (ArticleCard.jsx:51, DigestOverlay.jsx:23)
- `threshold = 80` — why 80? (usePullToClose.js:6)
- `threshold = 60` — why 60? (useOverscrollUp.js:6)
- `diff * 0.5` — why 0.5 damping? (usePullToClose.js:32, useOverscrollUp.js:41)
- `threshold * 1.5` — why 1.5? (useOverscrollUp.js:42)
- `translateY(-${overscrollOffset * 0.4}px)` — why 0.4? (ArticleCard.jsx:87, DigestOverlay.jsx:68)

**Recommendation:** Extract to named constants at module top:

```javascript
const SCROLL_HEADER_BLUR_THRESHOLD = 10
const PULL_TO_CLOSE_THRESHOLD = 80
const OVERSCROLL_TRIGGER_THRESHOLD = 60
const GESTURE_DAMPING_FACTOR = 0.5
const CONTENT_SHIFT_DAMPING = 0.4
```

---

### 6. **Inline Styles Mixed with Tailwind Classes**

**Location:**
- ArticleCard.jsx:64-66 (progress bar transform)
- ArticleCard.jsx:87-89 (content transform)
- ArticleCard.jsx:95-97 (overscroll zone transform)
- ArticleCard.jsx:105-107 (CheckCircle opacity/scale)
- DigestOverlay.jsx (same locations)

**Finding:**

Transforms and dynamic values use inline `style` props, while transitions and static styles use Tailwind classes. This creates visual inconsistency in the codebase.

**Example:**
```javascript
<div
  className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 origin-left transition-transform duration-100"
  style={{ transform: `scaleX(${progress})` }}
/>
```

**Recommendation:** For consistency, either:
1. Move all dynamic styles to CSS custom properties + Tailwind
2. Accept that transforms need inline styles and document this pattern

---

### 7. **Prose Styling Class String Duplication**

**Location:**
- ArticleCard.jsx:91-93
- DigestOverlay.jsx:71-73

**Finding:**

Both overlays have this identical 15-class string:
```
"prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900 prose-headings:tracking-tight prose-h1:text-2xl prose-h1:font-bold prose-h2:text-xl prose-h2:font-semibold prose-h3:text-lg prose-h3:font-semibold prose-blockquote:border-slate-200 prose-strong:text-slate-900"
```

**Recommendation:** Extract to a shared CSS module or Tailwind @apply directive:

```css
.overlay-prose {
  @apply prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900 prose-headings:tracking-tight prose-h1:text-2xl prose-h1:font-bold prose-h2:text-xl prose-h2:font-semibold prose-h3:text-lg prose-h3:font-semibold prose-blockquote:border-slate-200 prose-strong:text-slate-900;
}
```

---

### 8. **Error Handling Asymmetry**

**Location:**
- DigestOverlay.jsx:70-72 — has error display
- ZenModeOverlay — no error display

**Finding:**

DigestOverlay renders `{errorMessage && !html ? <div>error</div> : <content>}`, but ZenModeOverlay assumes `html` is always valid.

**Recommendation:** Either:
1. Add error handling to ZenModeOverlay
2. Document that ZenModeOverlay is guaranteed valid HTML by caller

---

## LOW VALUE / NOTES

### 9. **Lifecycle Timing in DigestOverlay**

**Location:** DigestOverlay.jsx:26-42

**Finding:**

The component checks `if (!expanded) return null` at line 26, but the useEffect that sets up event listeners has `expanded` as a dependency. This means:
- When `expanded` changes from `false` to `true`, useEffect runs
- When `expanded` is `false`, component returns `null` before useEffect

**Impact:** Low — React handles this correctly, but it's subtle. The useEffect cleanup will still run correctly.

---

### 10. **Fragile Scroll-Bottom Detection**

**Location:** useOverscrollUp.js:22-24

**Finding:**

```javascript
const isAtBottom = () => {
  const { scrollTop, scrollHeight, clientHeight } = scrollEl
  return scrollHeight - scrollTop - clientHeight < 1
}
```

This uses `< 1` pixel tolerance. Could fail with:
- Browser zoom
- Sub-pixel rendering
- Extremely long content

**Recommendation:** Increase tolerance to `<= 2` or `<= 5` pixels for robustness.

---

### 11. **No Prop Validation or Types**

**Finding:**

Neither overlay validates required props like `html`, `onClose`, `onMarkRemoved`. If these are missing/undefined, runtime errors will occur.

**Recommendation:** Add prop-types or migrate to TypeScript.

---

## Summary Metrics

| Category | Count | Priority |
|----------|-------|----------|
| High-value duplication opportunities | 4 | ⭐⭐⭐ |
| Medium-value improvements | 4 | ⭐⭐ |
| Low-value / notes | 3 | ⭐ |
| **Total lines duplicated between overlays** | ~65 | — |
| **Estimated reduction if refactored** | ~100-150 lines | — |

---

## Recommended Refactor Sequence

1. **Extract ZenModeOverlay** to its own file (low risk, immediate clarity)
2. **Create BaseOverlay component** that handles common overlay behavior
3. **Extract useTrackedState hook** for ref-syncing pattern
4. **Extract prose class string** to shared CSS
5. **Document threshold semantics** for gesture hooks
6. **Extract magic numbers** to named constants

---

## Files Analyzed

```
client/src/components/ArticleCard.jsx       (ZenModeOverlay: lines 31-122)
client/src/components/DigestOverlay.jsx     (full file)
client/src/hooks/useScrollProgress.js       (full file)
client/src/hooks/usePullToClose.js          (full file)
client/src/hooks/useOverscrollUp.js         (full file)
```
