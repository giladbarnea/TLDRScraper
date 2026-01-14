---
status: completed
last_updated: 2026-01-14
---
# Zen Overlay Header and Swipe Interactions

Redesigned the Zen reading overlay with three touch-first interaction improvements:

**Plan A - Header Redesign**: Replaced title with contextual source info (favicon, domain, reading time). Header floats absolutely over content with dynamic transparency on scroll. Actions: ChevronDown (collapse), Check (mark done). Progress bar attached to header bottom.

**Plan B - Pull-to-Close**: Native touch gesture using `usePullToClose` hook. Swipe down from header or top of content (when scrollTop=0) to dismiss overlay. Uses `addEventListener` with `{passive: false}` to suppress iOS rubber-banding. Applies 0.5x resistance and 80px threshold. Entire overlay translates with gesture.

**Plan C - Overscroll-Up Completion**: Pull-up gesture at scroll bottom using `useOverscrollUp` hook. When at bottom, dragging up reveals CheckCircle icon that fills with progress. 30px effective threshold (60px with 0.5x resistance). Content applies 0.4x resistance transform for kinetic feedback. Triggers mark-done action on release.

Key technical decisions: Avoided Framer Motion drag (conflicts with native scroll). Used refs for gesture state to prevent listener thrashing. Both hooks use stable `useEffect` dependencies (scrollRef, onClose/onComplete, threshold).

Files: `client/src/components/ArticleCard.jsx`, `client/src/hooks/usePullToClose.js`, `client/src/hooks/useOverscrollUp.js`.

COMPLETED SUCCESSFULLY.
