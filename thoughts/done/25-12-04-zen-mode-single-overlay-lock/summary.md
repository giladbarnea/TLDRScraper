---
status: completed
last_updated: 2025-12-17 06:47
---
# Zen Mode Single Overlay Lock

Prevented multiple zen mode overlays from stacking when multiple TLDR requests completed while user was viewing an expanded modal. Added module-level lock (`zenLockOwner`) in useSummary.js with URL-based ownership tracking. Gated all `setExpanded(true)` calls (lines 80, 109, 120, 125) on `acquireZenLock(url)` success. Added `releaseZenLock(url)` to `collapse()`, `toggle()`, `toggleVisibility()`, and unmount cleanup. At most one zen modal can be open at any time—blocked requests cache content silently for later viewing.

COMPLETED SUCCESSFULLY.
