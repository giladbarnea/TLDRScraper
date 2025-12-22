---
last_updated: 2025-12-22 20:42
---
# Plan A: Zen Overlay Header Redesign & Actions

## Overview

Redesign the ZenModeOverlay header from a title-focused navigation bar to an organic control center with source context metadata and dual actions (collapse vs. mark done).

## Current State Analysis

**Current Header** (`ArticleCard.jsx:45-60`):
```
[ < ChevronLeft ]  [ Article Title (link) ]
```
- Left: Back button with `ChevronLeft` icon → calls `onClose()` (collapse)
- Center/Right: Article title as external link
- Background: Static `bg-slate-50/80` with hard `border-b border-slate-100`

**Issues with Current Design**:
1. Title duplicates the H1 in content
2. No "mark done" action
3. Static header appearance lacks organic feel
4. No source context (which newsletter/source)

## Desired End State

**New Header**:
```
[ ⌄ ChevronDown ]    [ (favicon) Source • N min ]    [ ✓ Check ]
```
- Left: Down chevron → collapse overlay (save for later)
- Center: Source favicon + name + reading time from `articleMeta`
- Right: Checkmark → mark article as removed, close overlay
- Background: Dynamic transparency based on scroll position

**Verification**:
1. Header shows source favicon and name (not article title)
2. Down chevron collapses without changing article state
3. Checkmark marks article as removed AND closes overlay
4. Header background transitions from transparent (top) to frosted glass (scrolled)

## What We're NOT Doing

- Swipe-down gesture (Plan B)
- Overscroll-up gesture (Plan C)
- Changing the content area styling
- Modifying the progress bar

## Implementation Approach

Single-phase change to `ZenModeOverlay` component with supporting CSS. The component is self-contained, so changes are isolated.

## Phase 1: Header Redesign

### Overview
Replace header content and add scroll-based transparency.

### Changes Required:

#### 1. Update ZenModeOverlay Props
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add new props for source context and mark-done action

```jsx
// Line 26: Update function signature
function ZenModeOverlay({ url, html, hostname, displayDomain, articleMeta, onClose, onMarkDone }) {
```

#### 2. Add Scroll State Tracking
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Track whether user has scrolled for header transparency

```jsx
// Inside ZenModeOverlay, after line 28 (useScrollProgress)
const [hasScrolled, setHasScrolled] = useState(false)

// Inside the existing useEffect (around line 30), add scroll detection
useEffect(() => {
  document.body.style.overflow = 'hidden'
  const handleEscape = (e) => {
    if (e.key === 'Escape') onClose()
  }
  document.addEventListener('keydown', handleEscape)

  // Track scroll for header transparency
  const scrollEl = scrollRef.current
  const handleScroll = () => {
    setHasScrolled(scrollEl.scrollTop > 10)
  }
  scrollEl?.addEventListener('scroll', handleScroll, { passive: true })

  return () => {
    document.body.style.overflow = ''
    document.removeEventListener('keydown', handleEscape)
    scrollEl?.removeEventListener('scroll', handleScroll)
  }
}, [onClose])
```

#### 3. Replace Header Content
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Replace lines 45-60 with new header structure

```jsx
{/* Header with dynamic transparency */}
<div className={`
  flex items-center justify-between px-5 py-4 shrink-0 transition-all duration-200
  ${hasScrolled
    ? 'bg-white/80 backdrop-blur-md border-b border-slate-100'
    : 'bg-transparent border-b border-transparent'}
`}>
  {/* Left: Collapse (Down Chevron) */}
  <button
    onClick={onClose}
    className="p-2 -ml-2 rounded-full hover:bg-slate-200/60 text-slate-500 hover:text-slate-700 transition-colors"
    aria-label="Close and save for later"
  >
    <ChevronDown size={20} />
  </button>

  {/* Center: Source Context */}
  <div className="flex items-center gap-2">
    {hostname && (
      <div className="w-[18px] h-[18px] rounded-full bg-white border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
        <img
          src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
          alt={displayDomain}
          className="w-full h-full object-cover"
          onError={(e) => { e.target.style.display = 'none' }}
        />
      </div>
    )}
    <span className="text-sm text-slate-500 font-medium">
      {displayDomain}
      {articleMeta && <span className="text-slate-400"> · {articleMeta}</span>}
    </span>
  </div>

  {/* Right: Mark Done (Checkmark) */}
  <button
    onClick={onMarkDone}
    className="p-2 -mr-2 rounded-full hover:bg-green-100 text-slate-400 hover:text-green-600 transition-colors"
    aria-label="Mark as done and remove"
  >
    <Check size={20} />
  </button>
</div>
```

#### 4. Update ZenModeOverlay Invocation
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Pass new props at the render site (around line 249-256)

```jsx
{!isRemoved && tldr.expanded && tldr.html && (
  <ZenModeOverlay
    url={fullUrl}
    html={tldr.html}
    hostname={hostname}
    displayDomain={displayDomain}
    articleMeta={article.articleMeta}
    onClose={() => tldr.collapse()}
    onMarkDone={() => {
      tldr.collapse()
      toggleRemove()
    }}
  />
)}
```

#### 5. Add Icon Import
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Import `ChevronDown` and `Check` icons

```jsx
// Line 2: Update import
import { AlertCircle, Check, CheckCircle, ChevronDown, ChevronLeft, Loader2, Trash2 } from 'lucide-react'
```

#### 6. Add useState Import
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Add useState to the React import (if not already present)

```jsx
// Line 3: Ensure useState is imported
import { useEffect, useRef, useState } from 'react'
```

### Success Criteria:

#### Automated Verification:
- [ ] Client builds without errors: `cd client && npm run build`
- [ ] Linter passes: `cd client && npm run lint`

#### Manual Verification:
- [ ] Open a TLDR overlay → header shows source favicon + domain + articleMeta (not title)
- [ ] Click down chevron (left) → overlay closes, article remains in list unchanged
- [ ] Click checkmark (right) → overlay closes AND article is marked as removed
- [ ] Scroll down in overlay → header background transitions to frosted glass
- [ ] Scroll back to top → header becomes transparent again
- [ ] Escape key still closes the overlay (collapse behavior)
- [ ] External link to article is no longer in header (title removed)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Plan B.

---

## References

- Original discussion: `thoughts/25-12-22-zen-overlay-header-and-swipe-interactions/discussion.md`
- Current ZenModeOverlay: `client/src/components/ArticleCard.jsx:26-77`
- Favicon pattern: `client/src/components/ArticleCard.jsx:97-106`
- Article state management: `client/src/hooks/useArticleState.js`
