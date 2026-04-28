---
name: Split Desktop and Mobile Overlay Menu Paths
done: 2026-04-23, 6c389c5
implements: plans/1-split-mobile-and-desktop.plan.md
last_updated: 2026-04-27 21:21, b387f55
---

# Split Desktop and Mobile Overlay Menu Paths

Behavior-preserving refactor of `useOverlayContextMenu.js`. Consumers (`ZenModeOverlay`, `OverlayContextMenu`, `BaseOverlay`, `DigestOverlay`) untouched.

## Decisions

- Kept the three sub-hooks private in the same file rather than extracting to siblings. The plan allowed either; co-location keeps the contract visible and avoids growing `client/src/hooks/` with hooks that have no other consumer.
- Replaced `openedBySelectionRef` with a `source` field on menu state (`MenuOpenSource` enum) so the dismissal path reads from one authoritative place and future reducer work (plan 2) has a single state shape to adopt.

## Drift from plan

- Plan Phase 1 step 7 (docs update) was initially skipped and caught in peer review. Only `client/STATE_MACHINES.md` needed the edit — the `openedBySelectionRef` section there was stale. `client/ARCHITECTURE.md`'s Digest "planned consumer" language was unaffected by this pass and left alone.
- Post-review amendment: `openMenu`/`closeMenu` now write `menuStateRef.current` synchronously before `setMenuState`, not only via the `useEffect` mirror. The mirror is retained as a backstop. This preserves the synchronous read semantics the old `openedBySelectionRef` had — without it, document listeners that fire between `setState` and commit could read a stale `source`.

## Challenges / open

- Mobile verification surfaced a cosmetic iOS WebKit behavior: native selection highlight disappears the instant the menu portal mounts. Captured `selectedText` means Elaborate still receives the right text, so functionally clean. Not introduced by this refactor — pre-existing, confirmed no `user-select` CSS and no auto-focus on coarse pointer. Deferred; out of scope for a split refactor.
