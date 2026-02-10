---
last_updated: 2026-02-10 11:18
---
# UI Design Principles

This document captures the design thinking behind the interface. It's meant to guide future decisions by explaining *why* things are the way they are, so that new work stays cohesive rather than drifting.

## Values derive from a system, not from the moment

The difference between "looks fine" and "feels polished" is almost never about individual values. It's about whether the values relate to each other. A 17px heading next to a 15px body text is intentional if those sizes come from a scale. The same pairing is arbitrary if one was "what looked right in this component."

Every spacing, type size, radius, and color in the interface traces back to a small set of tokens defined in `index.css`. When adding something new, pull from the system. If nothing fits, that's a signal to question the decision before extending the scale.

## Hierarchy needs contrast on multiple axes

People don't perceive 18px vs 17px as "different level." They perceive it as "roughly the same." To make hierarchy legible at a glance, each level must differ from its neighbors in at least two properties — size, weight, color, case, or tracking.

The type scale applies this:

- **Day headings** are large (20px), bold, primary color, tight tracking (`CalendarDay.jsx:19`)
- **Newsletter titles** are medium (17px), semibold, same color — distinguished from days by size + weight (`NewsletterDay.jsx:100`)
- **Section labels** break the pattern entirely: small (12px), semibold, uppercase, tracked, muted color (`NewsletterDay.jsx:38`). They read as a categorically different element, not "a slightly smaller heading"
- **Article titles** return to normal case at 15px medium — the primary content the eye should land on (`ArticleCard.jsx:179`)

The section labels are the key move. Instead of trying to fit four heading levels into a narrow size range (which was the original 20→18→17px pile-up), treating sections as labels creates a clear visual break that makes the whole hierarchy legible.

## Every grouping level needs structural framing

Whitespace can signal hierarchy — bigger gap means higher-level boundary. But whitespace alone is fragile. A page of text labels separated by varying amounts of empty space feels hollow rather than structured.

The principle: each level of grouping gets its own visual device, not just its own spacing value.

- **Days** get a sticky frosted header with a bottom border — the heaviest structural chrome, appropriate for the top-level boundary (`CalendarDay.jsx:76`)
- **Newsletters** get a lighter bottom border on their header row (`NewsletterDay.jsx:97`). In the collapsed state, this turns floating labels into a clean list with separators. In the expanded state, it separates the group label from its cards
- **Articles** get cards — border, shadow, contained padding (`ArticleCard.jsx:335-343`)

The newsletter border was the critical missing piece. Without it, collapsed newsletters were just words in a void. With it, they read as rows in a structured list — similar to how iOS Settings or Notion sidebars give every item a visual "slot."

## Secondary content should be uniformly subordinate

When a meta row has internal contrast — the domain in one shade, the separator in another, the stats in a third — the eye parses it as three separate pieces of information competing for attention. This competes with the title above it.

The meta row uses a single muted color (`text-slate-400`) across all elements, with only `font-medium` on the domain for subtle emphasis (`ArticleCard.jsx:211-218`). The middle-dot separator (`·`) is lighter than the pipe (`|`) it replaced. The entire row reads as one subordinate unit rather than several small elements jostling for attention.

The same thinking applies to the state indicator icons (read checkmark, summary available arrow) which sit at `text-slate-300` — present if you look for them, invisible if you don't (`ArticleCard.jsx:191-196`).

## Color roles, not color choices

The interface uses four semantic text roles, not a per-component color assignment:

| Role | Shade | Used for |
|------|-------|----------|
| Primary | slate-900 | Headings, unread titles, primary text |
| Secondary | slate-500 | Date subtitle, form labels |
| Tertiary | slate-400 | Meta text, badges, section labels, read articles |
| Chrome | slate-200 | Borders, dividers, favicons frames |

This means a heading and an unread article title share the same color (they're both "primary text"), while a newsletter section label and article meta share the same color (they're both "tertiary"). The semantic role determines the shade, not the component.

Brand blue appears sparingly and with purpose: the TLDR. period, the loading spinner, the progress bar in zen mode, focus rings, and the selection checkmark. It marks interactive or state-change moments, not decoration.

The single orphan-color violation that existed (a purple progress bar in zen mode) was replaced with brand blue — every accent color should connect to the palette (`ArticleCard.jsx:119`).

## Spacing is hierarchy made visible

The spacing scale follows a 4px grid with values mapped to structural levels:

| Gap | Between | Reasoning |
|-----|---------|-----------|
| 48px | Calendar days | Largest structural boundary in the feed (`Feed.jsx`) |
| 16px | Newsletters within a day | Tight enough to feel grouped, with border-b providing the real structure (`CalendarDay.jsx:30`) |
| 12px | Cards | Dense enough for scanning, loose enough for tap targets (`ArticleCard.jsx:301`) |
| 16px | Internal padding on cards | On the 4px grid, proportional to card content (`ArticleCard.jsx:345`) |

The discipline is: one spacing mechanism per gap. The earlier design had `space-y-16` on the Feed *and* `mb-12` on each CalendarDay, both trying to control the same gap. Now each gap has exactly one owner. The parent's `space-y` sets inter-sibling gaps; children don't add their own bottom margins to the same boundary.

## Radius and shadow serve card definition

Border radius follows element scale with three values: 8px for small elements (inputs, buttons), 12px for medium (cards, containers), 16px for large (settings panel). The previous 20px arbitrary value on cards created a pillowy, iOS-widget feel that clashed with the otherwise flat design.

Shadows work with borders, not instead of them. The original cards had `shadow-[0_2px_12px_-4px_rgba(0,0,0,0.05)]` (5% opacity) and `border-white/40` (white-on-white). They were technically elevated but visually invisible. Now cards have both a `shadow-card` token and `border-slate-200/60` — the border gives crisp definition at small sizes, the shadow adds subtle depth at larger ones (`ArticleCard.jsx:337-338`).

## The zen overlay is the same design, not a different one

The full-screen summary overlay uses `font-serif` (Lora) for its prose content — an editorial choice that creates a reading-focused mood. But everything *around* the prose shares the same design language as the feed: same favicon size, same border color for the scroll-state header, same brand-blue for the progress bar, same `shadow-elevated` token.

The header respects the same chrome hierarchy: `px-4 py-3` padding, `border-slate-200/60` divider on scroll, muted slate buttons (`ArticleCard.jsx:77-82`). It's recognizably the same app, just in a different mode.

## What this means in practice

When making a design decision:

1. **Check the system first.** If you need a spacing value, use one from the scale. If you need a text color, use a semantic role. If nothing fits, the decision might be wrong — or the system needs a principled extension.
2. **Differentiate on 2+ axes.** If a new element is "like X but smaller," it probably needs more differentiation than just size.
3. **Give groups a frame.** If a set of items will ever appear collapsed or empty, they need structural chrome — not just whitespace — to hold the visual space.
4. **Keep secondary content uniform.** Variety within a subordinate element (different colors, weights, decorations in a meta row) makes it compete with the primary content above it.
5. **One owner per gap.** Either the parent controls inter-child spacing (via `space-y` or `gap`) or each child controls its own margin. Not both.
