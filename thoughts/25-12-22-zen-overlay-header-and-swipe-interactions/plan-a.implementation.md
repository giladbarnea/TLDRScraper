---
last_updated: 2025-12-29 21:08
---
# Plan A Implementation: Zen Overlay Header Redesign

## Changes Made

### 1. Updated Imports
Added `Check`, `ChevronDown`, `useState`; removed `ChevronLeft`

### 2. Updated ZenModeOverlay Signature
Now accepts `hostname`, `displayDomain`, `articleMeta`, and `onMarkDone` props

### 3. Added Scroll Tracking
`hasScrolled` state triggers at 10px scroll depth

### 4. Redesigned Layout
- Header is now `absolute` over content, allowing text to scroll behind
- Transparent at top → `bg-white/80 backdrop-blur-md` when scrolled
- Left: `ChevronDown` (collapse/save for later)
- Center: Source favicon + domain + reading time (clickable link to original article)
- Right: `Check` icon (marks done and closes)
- Progress bar attached to header bottom edge

### 5. Updated Invocation
Passes source metadata and `onMarkDone` handler that collapses overlay and toggles remove state
