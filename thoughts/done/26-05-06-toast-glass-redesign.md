---
status: done
last_updated: 2026-05-06 13:38
---

# Toast glass redesign

This pass treated the summary toast as a sibling of the elaboration preview rather than a branded badge floating above the feed.

The old toast leaned on a saturated left rail, a small flat icon, and a conventional gradient card. Those choices made it read as plastic notification chrome, especially next to the preview's frosted overlay language. The redesign moved the toast toward the same material vocabulary as `ElaborationPreview`: translucent white, rim lighting, blue-tinted depth, blurred internal glow, and a single precise checkmark orb.

The important choice was to avoid making the toast a miniature modal. It remains a quick, tappable notification with one line of article identity, but the surface now has enough optical complexity to belong with the overlay layer. The label uses wide tracking for ceremony, while the title uses display-weight compression to echo the uploaded reference without turning the component into a large card.

The toast root became a real `button` because the whole surface already behaves as an action. That makes the visual affordance and semantics match: tapping anywhere opens the summary. The focus ring stayed brand-blue and the title is included in the accessible label.

The elaboration preview received a lighter finesse pass only. The viewport padding, richer backdrop blur, softer rim, and larger close target align it with the new toast material while preserving the existing content hierarchy and interaction model.

The animation was tightened rather than made showy. Entry now uses the existing spring token with a short blur-to-clear transition, and exit is faster. Reduced-motion users get effectively instantaneous toast animation.

One implementation challenge was keeping the effect expressive without introducing a new design abstraction. The final patch keeps everything local to the existing components and global CSS animation block, avoiding a new glass component or token layer before more surfaces prove they need one.
