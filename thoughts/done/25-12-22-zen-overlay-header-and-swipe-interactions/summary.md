---
status: completed
last_updated: 2025-12-31 10:13, da59643
---
# Zen Overlay Header Redesign

Redesigned ZenModeOverlay header from title-focused navigation to organic control center with source context. Replaced article title (duplicated H1) with source favicon, domain, and reading time. Swapped back button for down chevron (collapse/save for later) and added checkmark button (mark done and close). Made header absolute-positioned with scroll-based transparency—transparent at top, frosted glass (`bg-white/80 backdrop-blur-md`) when scrolled, allowing content to scroll behind. Progress bar repositioned to header bottom edge. Changes isolated to ArticleCard.jsx: updated ZenModeOverlay props (hostname, displayDomain, articleMeta, onMarkDone), added hasScrolled state tracking at 10px threshold, restructured layout with absolute header + content padding.

Shipped in PR #423. Plan B (swipe-down gesture) and Plan C (overscroll-up completion) deferred.

COMPLETED SUCCESSFULLY.
