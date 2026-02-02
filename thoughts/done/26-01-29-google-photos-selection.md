---
status: completed
last_updated: 2026-02-02
---
# Google Photos-Style Selection

Replaced three-dot menu + BottomSheet with long-press multi-selection. All hierarchy levels (CalendarDay, NewsletterDay, Section, ArticleCard) became selectable via Selectable.jsx:6-77 wrapper using useLongPress.js for 500ms gesture detection. Selecting parent recursively selects all descendant articles. InteractionContext (not SelectionContext per plan) provides isSelected, itemLongPress, containerLongPress, clearSelection state management with localStorage sync. SelectionCounterPill.jsx:4-22 renders "✕ N" pill in header when isSelectMode is true. Visual feedback: ring-4 ring-slate-300 border and absolute-positioned brand-500 checkmark (Selectable.jsx:64-72). Gesture conflicts resolved: swipe-to-remove disabled during select mode (ArticleCard.jsx canDrag logic), long-press disabled on removed cards via disabled prop. Deleted ThreeDotMenuButton.jsx and BottomSheet.jsx. FoldableContainer.jsx rightContent prop removed.

COMPLETED SUCCESSFULLY.
