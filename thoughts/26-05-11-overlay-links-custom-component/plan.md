---
session_id: 019e16a8-e1ad-72cc-b7c6-0c6e9830b97b
provider: pi
directory: ~/dev/TLDRScraper
history_path: ~/.pi/agent/sessions/--Users-giladbarnea-dev-TLDRScraper--/2026-05-11T10-50-27-118Z_019e16a8-e1ad-72cc-b7c6-0c6e9830b97b.jsonl
created: "2026-05-11 13:50"
modified: "2026-05-11 14:12"
messages: 1
custom_title: "TLDRScraper plan replace Overlay links with custom components"
last_updated: 2026-05-11 12:35
implementation: thoughts/26-05-11-overlay-links-custom-component/implementation.md
---
<assistant-response i="4" model="gpt-5.5">
## Assistant

I read the prepared baseline list, client docs, overlay/context-menu state-machine docs, and the pseudocode skill. Here’s the minimal plan.

## Plan

Replace **generated markdown content links inside `BaseOverlay` reading surfaces** with a React-controlled `OverlayLink` component. Keep the existing markdown pipeline, overlay shell, and `OverlayContextMenu` layer stack.

### What to do

1. Add an `OverlayMarkdown` renderer:
   - Convert markdown with existing `markdownToHtml()`.
   - Parse the sanitized HTML into DOM nodes.
   - Convert DOM nodes into React elements.
   - Replace only `<a>` nodes with `<OverlayLink href="…">…</OverlayLink>`.
   - Preserve non-link markup, KaTeX/MathML, prose classes, and sanitized attributes.

2. Add `OverlayLink`:
   - Render as a link-looking control, likely `span role="link" tabIndex={0}`, not a native `<a>`, to avoid native long-press link callouts.
   - Short press / click / Enter opens `href` in a new tab with `window.open(href, '_blank', 'noopener,noreferrer')`.
   - Long press opens the custom overlay context menu.
   - Movement beyond the existing gesture threshold cancels long-press and prevents accidental tab opening during scroll.
   - Right-click on desktop opens the same link context menu and does not bubble into the prose selection menu.

3. Let `BaseOverlay` own the link menu:
   - Add a tiny link-menu state beside the existing `overlayMenu` render site.
   - Provide `openLinkMenu()` to descendants through context.
   - Reuse `OverlayContextMenu` for the visual/floating/dismiss layer.
   - First action is a dummy link action, e.g. `Dummy action`, closing over the link URL.

4. Replace prose render sites:
   - `ZenModeOverlay`: replace `dangerouslySetInnerHTML` with `<OverlayMarkdown markdown={summaryMarkdown} />`.
   - `DigestOverlay`: same for digest markdown.
   - Keep error rendering unchanged.

5. Extract shared Floating UI position helpers if needed:
   - Reuse the current point-position-reference shape from `useOverlayContextMenu`.
   - Avoid duplicating coordinate object construction in two places.

## Out of scope

- No replacement of the Zen header’s original-article `<a>` link.
- No link replacement inside `ElaborationPreview` in this slice; it is a nested modal with separate z-index/focus ownership.
- No redesign of `OverlayContextMenu`.
- No new real link actions beyond the dummy action.
- No changes to summary, digest, article lifecycle, zen lock, storage, or persistence.
- No attempt to fix existing mobile text-selection bugs.

## State machines

### New: overlay link press

```
idle
  → pointer down: tracking
tracking
  → movement past threshold: canceled
  → pointer up before threshold: open tab
  → long-press threshold: open link menu, suppress following click
menu open
  → outside / Escape / action / overlay unmount: closed
```

Annoying cases handled:
- Long-press must not also open the tab on touchend/click.
- Scroll beginning on a link must not open either the menu or the tab.
- Right-click on a link must open the link menu, not the existing selected-text menu.
- Link text becomes a control; selecting link text itself is not a goal.

### Seams with existing machines

Added arrows:
- `OverlayLink long press/right click → BaseOverlay link menu OPEN`.
- `BaseOverlay link menu OPEN → OverlayContextMenu render path`.
- `OverlayLink short press → browser new tab`.

Removed/blocked arrows for link targets only:
- Native link long-press callout.
- Native anchor navigation.
- Link `contextmenu` bubbling into `BaseOverlay.overlayMenu.handleContextMenu`.

Unchanged:
- Text selection menu state machine.
- Floating UI topmost-layer Escape behavior.
- Zen/Digest overlay close/read/remove flows.
- Pull-to-close remains disabled; overscroll-up unchanged.
- Summary/digest lifecycle and persistence untouched.

## Component map

- `ZenModeOverlay` / `DigestOverlay`
  → render `OverlayMarkdown`
- `OverlayMarkdown`
  → markdown HTML to React tree
  → replaces `<a>` with `OverlayLink`
- `OverlayLink`
  → owns link press gesture
  → asks context to open link menu
- `BaseOverlay`
  → owns link menu state/provider
  → renders existing `OverlayContextMenu` for link menu
- `OverlayContextMenu`
  → unchanged shared floating menu surface

## Manual tests

1. **Short press a markdown link in Zen and Digest overlays.**  
   Expected: a new tab opens to the link URL; overlay remains open; no custom menu appears.  
   Falsifies if: same-tab navigation happens, no tab opens, overlay closes, or the menu appears.

2. **Long press a markdown link.**  
   Expected: custom menu appears with the dummy action; no tab opens; native browser callout does not appear.  
   Falsifies if: the tab opens, iOS/Android native link preview appears, or the existing “Elaborate” text-selection menu opens.

3. **Select non-link text and use the existing overlay context menu.**  
   Expected: existing text-selection menu still opens and Elaborate still works; Escape closes the top menu first, then the overlay.  
   Falsifies if: link menu opens for non-link text, Elaborate stops working, or Escape closes the reader while a menu is open.
</assistant-response>
