---
plan: thoughts/26-05-11-overlay-links-custom-component/plan.md
last_updated: 2026-05-11 12:35
---
# Overlay custom links implementation notes

The implementation stayed close to the plan: generated overlay markdown links are now controlled React components, while the existing overlay shell and context-menu layer are still the authority for floating surfaces.

The main architectural decision was to put link-menu ownership in `BaseOverlay` instead of in `OverlayLink` or `OverlayMarkdown`.
That keeps menu layering next to the existing `OverlayContextMenu` render site and avoids introducing another portal owner inside prose content.
It also preserves the current Floating UI parent/child relationship between the reader and its transient menus.

`OverlayMarkdown` deliberately remains a small adapter around `markdownToHtml` rather than a new markdown pipeline.
This keeps sanitization, KaTeX support, and prose styling where they already lived, and limits the new responsibility to HTML-to-React conversion plus anchor substitution.
The tradeoff is a little DOM attribute normalization logic, but it is local and mechanical.

`OverlayLink` uses `useLongPress` and the existing interaction movement threshold so the feature inherits the same gesture timing vocabulary as selection.
That was simpler and safer than creating a second gesture constant set just for links.
Short press, long press, right-click, movement cancel, and post-long-press click suppression are all owned by `OverlayLink` because they are link-specific press semantics.

The only meaningful drift from the plan is the rendered element shape.
The plan suggested a non-anchor link-like element, possibly `span role="link"`.
During lint verification, `span role="link"` was rejected by the accessibility lint rules, so the implementation uses a styled `button` instead.
That keeps keyboard activation semantics without restoring native anchor long-press behavior.

`floatingPositionReference.createPointPositionReference` was extracted because both text-menu right-click and link-menu gestures need the same point reference shape.
This prevents small positioning-shape drift between `useOverlayContextMenu` and `OverlayLink`.

`OverlayLinkMenuContext` intentionally fails loudly when used outside `BaseOverlay`.
Custom overlay links are not a general app primitive yet; they depend on the overlay menu surface and should not silently degrade elsewhere.

The existing text-selection menu was left intact.
Link context-menu events stop before they reach `BaseOverlay.overlayMenu.handleContextMenu`, while normal non-link selections continue through the existing `useOverlayContextMenu` mobile and desktop paths.

`ElaborationPreview` was intentionally not migrated.
It is a separate modal layer with its own focus and dismissal behavior, and including it would have widened the blast radius without helping the requested overlay reader links.

Verification completed with `client` tests, production build, and lint script.
The lint script still reports existing project-wide fallow health/dead-code/duplication summaries, but exits successfully; no new blocking lint issue remains.

Manual feedback confirmed the feature works well.
The remaining important manual watchpoint is device-specific native long-press behavior, especially on iOS browsers, because that behavior cannot be proven by the build or test suite.
