---
status: done
last_updated: 2026-05-06 13:48
---

# Toast glass redesign

This pass treated the summary toast as a sibling of the elaboration preview rather than a branded badge floating above the feed.

The first glass pass overcorrected: it used too much scale, too much blue, and too much ceremony. The corrected toast intentionally removes brand color and oversized effects. It now uses a neutral translucent surface, chrome-weight borders, a small slate checkmark, and quiet shadowing so it behaves like system chrome rather than a marketing badge.

The important choice was to keep the toast subordinate. It remains a quick, tappable notification with one line of article identity; the label is readable but not letterspaced into a headline, and the title sits at normal interface scale instead of display scale.

The toast root became a real `button` because the whole surface already behaves as an action. That makes the visual affordance and semantics match: tapping anywhere opens the summary. The focus ring is neutral and the title is included in the accessible label.

The elaboration preview received a lighter finesse pass only. The viewport padding, richer backdrop blur, softer neutral rim, and larger close target align it with the new toast material while preserving the existing content hierarchy and interaction model.

The animation was tightened rather than made showy. Entry now uses the existing spring token with a small slide/fade, and exit is faster. Reduced-motion users get effectively instantaneous toast animation.

One implementation challenge was keeping the effect expressive without introducing a new design abstraction. The final patch keeps everything local to the existing components and global CSS animation block, avoiding a new glass component or token layer before more surfaces prove they need one.
