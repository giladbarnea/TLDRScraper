---
date: 2026-04-07
topic: "Custom Context Menu in Zen/Digest Overlays"
status: complete
last_updated: 2026-04-07 22:28
---
# Research: Custom Context Menu in Zen/Digest Overlays

## Executive Summary

The best place to implement a custom context menu is **in the header area of both `ZenModeOverlay` and `DigestOverlay` components**. The header already contains action buttons (close, mark-removed) and provides a natural anchor point for contextual actions. Adding a "..." menu button next to existing actions would provide quick access to additional operations without cluttering the UI.

---

## Detailed Findings

### 1. ZenModeOverlay (ArticleCard.jsx, lines 31-148)

**Files:**
- `client/src/components/ArticleCard.jsx` (contains ZenModeOverlay inline)
- `client/src/hooks/useSummary.js` (manages overlay state and zen-lock)

**Structure:**
```
Header (z-10, sticky):
├── [Close button] - ChevronDown icon, onClick: onClose()
├── [Link area] - Favicon + domain + meta, opens in new tab
└── [Mark-removed button] - Check icon, onClick: onMarkRemoved()
     │
Content (scrollable):
├── Prose content (dangerouslySetInnerHTML)
└── Overscroll completion zone

Gestures:
├── Pull-to-close (usePullToClose hook)
├── Overscroll-to-complete (useOverscrollUp hook)
└── Escape key to close
```

**Key Implementation Details:**
- Uses `createPortal` to render at `document.body` level
- z-index: 100
- Progress bar tracks scroll position
- Body overflow locked when open
- Zen-lock prevents multiple overlays

**Recommended Context Menu Actions:**
1. Open original URL in new tab
2. Copy URL to clipboard
3. Share via Web Share API
4. Toggle read/unread state
5. View article metadata/source

### 2. DigestOverlay (client/src/components/DigestOverlay.jsx)

**Files:**
- `client/src/components/DigestOverlay.jsx`
- `client/src/hooks/useDigest.js` (manages digest state)

**Structure:**
```
Header (z-10, sticky):
├── [Close button] - ChevronDown icon, onClick: onClose()
├── [Info area] - BookOpen icon + "N articles" count
└── [Mark-removed button] - Check icon, onClick: onMarkRemoved()
     │
Content (scrollable):
├── Prose content OR error message
└── Overscroll completion zone

Gestures: Same as ZenModeOverlay
```

**Key Implementation Details:**
- Nearly identical structure to ZenModeOverlay
- Renders via `createPortal` at body level
- z-index: 100
- Uses same gesture hooks (usePullToClose, useOverscrollUp)
- Zen-lock coordination via `acquireZenLock('digest')`

**Recommended Context Menu Actions:**
1. Regenerate digest
2. Copy digest text to clipboard
3. Share digest
4. Toggle article visibility
5. Adjust digest effort level

### 3. Existing Action Patterns

**SelectionActionDock (client/src/components/SelectionActionDock.jsx)**

Shows the established pattern for action buttons:
- Uses rounded icon buttons with labels below
- Icons from lucide-react
- Accent (brand color), danger (red), and neutral variants
- Disabled states with reduced opacity
- Spring animation on hover

**DockButton structure:**
```jsx
<button className="group flex min-w-16 flex-col items-center gap-1 rounded-xl px-2 py-1">
  <span className="flex h-11 w-11 items-center justify-center rounded-full">
    {icon}
  </span>
  <span className="text-xs font-medium">{label}</span>
</button>
```

### 4. Zen-Lock Mechanism (useSummary.js)

Both overlays use zen-lock to ensure only one is open:
```javascript
let zenLockOwner = null

export function acquireZenLock(owner) {
  if (zenLockOwner === null) {
    zenLockOwner = owner
    return true
  }
  return false
}

export function releaseZenLock(owner) {
  if (zenLockOwner === owner) {
    zenLockOwner = null
  }
}
```

---

## Architecture & Patterns

### Overlay Rendering Pattern
Both overlays use `createPortal` to render outside the React component tree:
```jsx
return createPortal(
  <div className="fixed inset-0 z-[100]">
    {/* content */}
  </div>,
  document.body
)
```

### Gesture Hooks
- `usePullToClose` - Detects pull gesture from top, applies 0.5x resistance, 80px threshold
- `useOverscrollUp` - Detects overscroll at bottom, triggers completion action
- `useScrollProgress` - Tracks scroll position for progress bar

### State Management
- ZenModeOverlay: Controlled via `useSummary` hook (expanded, html, onClose, onMarkRemoved)
- DigestOverlay: Controlled via `useDigest` hook (expanded, html, articleCount, onClose, onMarkRemoved)

---

## Recommended Implementation Approach

### 1. Create ContextMenu Component
Location: `client/src/components/ContextMenu.jsx`

A reusable popover component that:
- Renders as portal at body level
- Anchors to a trigger element
- Positions below/above based on viewport space
- Dismisses on click outside or Escape key
- Supports keyboard navigation

### 2. Add Menu Button to Overlays
In both `ZenModeOverlay` and `DigestOverlay` headers, add:
```jsx
<ContextMenu
  trigger={<button className="shrink-0 p-2 rounded-full hover:bg-slate-200/80 text-slate-500">
    <MoreHorizontal size={20} />
  </button>}
  items={[
    { label: 'Open in new tab', icon: <ExternalLink />, onClick: () => window.open(url, '_blank') },
    { label: 'Copy URL', icon: <Copy />, onClick: () => navigator.clipboard.writeText(url) },
    // ... more items
  ]}
/>
```

### 3. Hook into Existing State
- Read state via `useSummary` or `useDigest` hooks
- Write state via `updateArticle` or `setPayload` (already available)

---

## Open Questions / Risks

- [ ] Should context menu actions persist to storage immediately or batch on overlay close?
- [ ] Should the context menu support nested menus (e.g., "Share" → "Twitter", "Email", etc.)?
- [ ] How to handle Web Share API unavailability on desktop browsers?
- [ ] Should long-press on links/cards also trigger context menu (native vs custom)?

---

## Related Files

| File | Purpose |
|------|---------|
| `client/src/components/ArticleCard.jsx` | ZenModeOverlay implementation |
| `client/src/components/DigestOverlay.jsx` | DigestOverlay implementation |
| `client/src/components/SelectionActionDock.jsx` | Action button pattern reference |
| `client/src/hooks/useSummary.js` | Zen-mode state management |
| `client/src/hooks/useDigest.js` | Digest state management |
| `client/src/hooks/usePullToClose.js` | Gesture detection |
| `client/src/hooks/useOverscrollUp.js` | Gesture detection |
