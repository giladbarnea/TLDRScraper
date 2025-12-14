---
status: in_progress
last_updated: 2025-12-14 06:25
---
# Zen Mode Single Overlay Lock - Pre-Plan

## Problem Statement

When multiple TLDR requests are in-flight and one completes while the user is already viewing an expanded zen modal, the newly completed TLDR's modal overlays the one already open. This interrupts the user mid-read.

**Desired behavior:** At most one zen overlay active at any given time. A lock mechanism prevents TLDR requests from opening their modal if another modal is already displayed.

---

## Terminology

- **Zen mode / zen overlay / zen modal**: Full-screen modal overlay displaying TLDR content
- **Lock**: Conceptual mutex allowing at most one modal to be open

---

## State Machine

```
States: { UNLOCKED, LOCKED }
Initial state: UNLOCKED (always, including after page refresh)

Transitions:
┌──────────────────────────────────────────────────────────────┐
│  UNLOCKED + modal_display_attempt  →  LOCKED + modal opens   │
│  LOCKED   + modal_display_attempt  →  LOCKED (no-op)         │
│  LOCKED   + user_closes_modal      →  UNLOCKED               │
└──────────────────────────────────────────────────────────────┘
```

---

## Flow

### TLDR Request Lifecycle (existing, unchanged)

```
ArticleCard pressed
    → if cached: goto DISPLAY_ATTEMPT
    → if not cached: fire async request → on success: cache response → goto DISPLAY_ATTEMPT
```

### DISPLAY_ATTEMPT (the new gate)

```
if lock == UNLOCKED:
    lock = LOCKED
    open modal with content
else:
    // lock == LOCKED
    do nothing (content is already cached, user will see it next time they tap this card)
```

### Modal Close (existing, with lock release added)

```
user taps expanded modal to close
    → close modal
    → lock = UNLOCKED
```

---

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User taps A (not cached), then taps B (not cached), then taps C (cached) | C opens immediately (acquires lock). A completes → cached, no modal. B completes → cached, no modal. |
| User taps A (not cached), waits for it to complete | A completes → lock free → modal opens |
| User closes modal, taps A again (now cached) | Lock free → modal opens immediately |
| Page refresh while modal was open | Page loads with lock = UNLOCKED, article list view |
| User taps A, taps B, A finishes first and opens modal, user closes modal while B still in-flight | A opens (acquires lock). User closes A's modal (releases lock). B completes later → lock free → B's modal opens. |

---

## Key Constraints

1. **Full-screen modal**: When a modal is open, the article list is occluded. User cannot tap other articles or scroll the list.
2. **Lock acquisition timing**: Lock is acquired at display-attempt time (after request completes and content is ready), not at request initiation time.
3. **Lock release timing**: Only when user explicitly closes the modal.
4. **Caching unaffected**: All completed TLDRs are cached regardless of lock state. The lock only gates modal display.

---

## Open Questions for Planning Phase

1. Where should the lock state live? (React context, zustand store, component state lifted to common ancestor, module-level variable?)
2. Which component initiates the display-attempt and should perform the lock check?
3. Which component owns the modal close action and should release the lock?
4. Is there existing state that tracks "is modal open" that can serve as the lock, or is a separate lock state needed?
