---
name: Context Menu Implementation Review 1
reviews:
leads_to:
last_updated: 2026-04-27 21:21, b387f55
---

# Implementation Review 1

Written after [Context Menu Elaborate Action](thoughts/26-04-07-context-menu-research/implementation/0-f-elaborate-action.md) was done.

1. The strongest issue is still shared-surface leakage: a Zen-only feature altered the shared overlay primitive. [BaseOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/BaseOverlay.jsx#L28), [BaseOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/BaseOverlay.jsx#L52), and [BaseOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/BaseOverlay.jsx#L115) now encode menu-specific behavior, while [DigestOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/DigestOverlay.jsx#L4) does not use the menu at all. This is a direct expansion of point 2, “Co-locate the contract,” from [thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md](thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md): the contract is not local to the feature owner, so unrelated overlays now pay the complexity cost.

2. The core complexity is still distributed boundary logic, not business logic. [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L23), [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L53), [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L77), and [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L125) spread the state machine across refs plus document listeners. That matches point 4, “Make the state machine explicit,” in [thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md](thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md) exactly. My deeper extrapolation: even if this works today, implicit state at DOM/event boundaries is where future bug fixes will keep accreting flags instead of removing complexity.

3. Escape handling is still arbitration, not ownership. [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L133) wins with capture-phase suppression, and [BaseOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/BaseOverlay.jsx#L46) yields via `defaultPrevented`. That is point 3, “Use a stack, not arbitration,” from [thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md](thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md) almost verbatim. The novel extension: `ElaborationPreview` repeats the same pattern independently at [ElaborationPreview.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/ElaborationPreview.jsx#L61), so the stack problem is now duplicated across two overlay layers rather than resolved once.

4. Desktop and mobile are still over-unified. [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L33) and [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L47) put right-click and mobile selection into one hook with shared close semantics and shared menu state. That is point 5, “Split desktop and mobile,” from [thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md](thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md) directly. My extrapolation: capturing `selectedText` at open time was a good local fix, but it treats one race created by the unification; it does not reduce the underlying model complexity.

5. The feature still fights platform behavior in two places. First, the mobile path hand-rolls native-selection synchronization in [useOverlayContextMenu.js](/Users/giladbarnea/dev/TLDRScraper/client/src/hooks/useOverlayContextMenu.js#L55). Second, the shared overlay disables pull-to-close at [BaseOverlay.jsx](/Users/giladbarnea/dev/TLDRScraper/client/src/components/BaseOverlay.jsx#L25) to make text selection viable. That is point 1, “Stop fighting the platform,” from [thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md](thoughts/26-04-07-context-menu-research/implementation/0-e-initial-implementation.md). The deeper read: the bug is not only “custom menu is tricky”; it is that one hand-rolled boundary feature already forced a regression in another interaction primitive.

## Recommended order

1. **Split desktop and mobile paths first.**
   - Tackling point: **5. Split desktop and mobile.**
   - Why first: high impact, moderate diff, low product risk, and it directly reduces the timing/race complexity without waiting for BaseUI/Floating UI.
   - Shape: keep one exported `useOverlayContextMenu`, but internally compose `useDesktopContextMenu` and `useMobileSelectionMenu`.
   - Paves: makes later Floating UI migration easier because positioning can attach to both paths through one adapter; also makes the mobile reducer step smaller.
   - Avoids: investing more in one clever hook that you will later need to untangle.

2. **Make the mobile selection state explicit with a reducer.**
   - Tackling point: **4. Make the state machine explicit.**
   - Why second: after desktop/mobile split, the reducer is small and specific. Before the split, it risks becoming a generic monster.
   - Shape: replace `openedBySelectionRef` + `touchActive` with states like `idle | touching | selected | open | closing`.
   - Paves: turns bug reports into transition fixes instead of new flags.
   - Risk: medium, because mobile selection is fragile. Keep behavior-preserving tests/manual checklist.

3. **Define a shared overlay-menu contract, then wire Digest.**
   - Tackling point: **2. Co-locate the contract.**
   - Why third: since the intended product is Summary + Digest, the “shared BaseOverlay leakage” critique changes. The issue is not “shared is wrong”; it is “shared is half-expressed.”
   - Shape: create a small overlay-menu surface contract owned near `BaseOverlay`, e.g. `OverlaySelectableSurface` or `BaseOverlay` prop set that explicitly owns `data-overlay-content`, context-menu handler, and Escape relationship.
   - Paves: Digest integration becomes an instance of the same contract, not a second bespoke integration.
   - Avoids: later refactor from Zen-specialized code back into shared overlay code.

4. **Introduce Floating UI for positioning only.**
   - Tackling point: **1. Stop fighting the platform.**
   - Why not first: full BaseUI/Floating UI migration is bigger. Positioning is the safest slice and replaces custom viewport math in `OverlayContextMenu`.
   - Shape: swap `clampMenuPosition` for Floating UI positioning while keeping current rendering/actions.
   - Paves: BaseUI migration later, without forcing modal/focus changes yet.
   - Risk: low-medium; visual behavior changes, but interaction model stays intact.

5. **Add a real layer/focus stack or BaseUI dialog/menu primitive.**
   - Tackling point: **3. Use a stack, not arbitration.**
   - Why later: important, but larger and likely touches `BaseOverlay`, `OverlayContextMenu`, and `ElaborationPreview`. Better after contract and mobile state are clearer.
   - Shape: topmost layer owns Escape; preview/menu trap or manage focus correctly; no `stopImmediatePropagation` dance.
   - Paves: cleaner nested overlays long-term.
   - Risk: medium-high. This can break working Escape/backdrop behavior if done too early.

6. **Only then revisit pull-to-close.**
   - Tackling points: **1 + 2.**
   - Why later: it is currently disabled because native selection and touch gestures conflict. Fixing it before mobile selection is explicit risks reintroducing the same bug.
   - Shape: once selection state is explicit, pull-to-close can be conditionally disabled only during selection/touch-selection states, not globally.
   - Paves: restores Digest/summary gesture parity.
   - Risk: medium; touch gesture regression surface is large.

7. **Full BaseUI migration.**
   - Tackling points: **1 + 3.**
   - Why last: highest long-term payoff, but bigger diff. The earlier steps reduce custom complexity and make the migration less all-or-nothing.
   - Shape: replace custom menu/dialog/focus/Escape pieces with primitives, keeping domain actions and overlay content unchanged.
   - Risk: medium-high, but much lower after steps 1-5.

What I would not prioritize now: generic cleanup, docs-only work, or polishing `ElaborationPreview` styling. Those do not collapse future work. The best first move is splitting desktop/mobile because it reduces current complexity and makes every later step smaller.
