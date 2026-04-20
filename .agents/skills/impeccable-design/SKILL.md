---
name: impeccable-design
description: Unified frontend design skill covering the full spectrum of UI/UX work
user-invocable: true
argument-hint: "[sub-skill] [target]"
last_updated: 2026-04-20 08:01, 3c865a0
---

Unified design skill for producing distinctive, production-grade frontend interfaces. Contains 21 sub-skills covering every dimension of UI/UX quality.

## Mandatory First Step

Before doing any design work, always read `references/frontend-design/SKILL.md` — it defines the design principles, anti-patterns (the AI Slop Test), and the **Context Gathering Protocol**.

If no design context exists for the project yet, read `references/teach-impeccable/SKILL.md` and run it first. Design work without project context produces generic output.

## Sub-Skill Directory

| Sub-Skill | What it does | Read when... |
|-----------|-------------|-------------|
| `references/frontend-design/SKILL.md` | Core principles, anti-patterns, and context gathering | Always — mandatory first step |
| `references/teach-impeccable/SKILL.md` | One-time project context setup, writes `.impeccable.md` | No design context exists yet |
| `references/arrange/SKILL.md` | Layout, spacing, visual rhythm, hierarchy | Layout feels off, crowded, monotonous |
| `references/animate/SKILL.md` | Animations, micro-interactions, motion design | Adding animation, transitions, hover effects |
| `references/adapt/SKILL.md` | Responsive design, breakpoints, cross-device | Mobile layouts, viewport adaptation |
| `references/typeset/SKILL.md` | Typography: fonts, scale, hierarchy, readability | Font choices feel wrong, text hierarchy is weak |
| `references/colorize/SKILL.md` | Strategic color addition, palette expression | Design looks gray, dull, lacking warmth |
| `references/bolder/SKILL.md` | Amplify bland or generic designs | Design looks safe, lacks personality or impact |
| `references/quieter/SKILL.md` | Tone down overstimulating or aggressive designs | Too bold, too loud, overwhelming |
| `references/distill/SKILL.md` | Simplify and declutter | UI too complex, noisy, cluttered |
| `references/delight/SKILL.md` | Personality, joy, memorable moments | Adding polish, micro-interactions, fun |
| `references/clarify/SKILL.md` | UX copy, error messages, microcopy, labels | Confusing text, bad error messages |
| `references/polish/SKILL.md` | Final quality pass before shipping | Pre-launch review, alignment and consistency |
| `references/critique/SKILL.md` | UX evaluation with scoring and persona testing | Review/critique a design holistically |
| `references/audit/SKILL.md` | Technical audit: a11y, performance, theming, anti-patterns | Accessibility check, performance audit |
| `references/normalize/SKILL.md` | Realign UI to design system standards and tokens | Design drift, inconsistency, token misuse |
| `references/extract/SKILL.md` | Extract reusable components, design tokens, patterns | Refactoring repeated UI patterns |
| `references/harden/SKILL.md` | Error handling, i18n, overflow, edge cases | Making UI production-ready |
| `references/optimize/SKILL.md` | UI performance: loading, rendering, bundle size | Slow, laggy, janky UI |
| `references/onboard/SKILL.md` | Onboarding flows, empty states, first-run UX | First-time users, activation, empty states |
| `references/overdrive/SKILL.md` | Technically ambitious effects: shaders, spring physics, 60fps | Going all-out, extraordinary experiences |

## How to Use

**With an argument** — load the matching reference directly:
```
/impeccable-design animate     → reads references/animate/SKILL.md
/impeccable-design arrange     → reads references/arrange/SKILL.md
/impeccable-design audit       → reads references/audit/SKILL.md
```
Then follow the loaded reference's instructions.

**Without an argument** — read this file, assess the user's request, and load the most relevant sub-skill reference(s).

**Multiple sub-skills** — some tasks need more than one. For example, improving a bland landing page might call for `bolder`, `arrange`, and `typeset` in sequence.

## Sub-Skill Groups

### Quality Gates (run first or last)
- `audit` — technical health score across 5 dimensions
- `critique` — holistic UX evaluation with persona testing
- `polish` — final pre-ship quality pass

### Visual Dimension
- `colorize` — add or improve color
- `typeset` — improve typography
- `arrange` — fix layout and spacing
- `animate` — add purposeful motion

### Tone Adjustment
- `bolder` — more impact, more character
- `quieter` — less intensity, more refinement
- `distill` — less everything, more focus
- `delight` — more joy and personality

### Platform & Context
- `adapt` — responsive / cross-device
- `harden` — production-readiness
- `optimize` — performance

### UX & Content
- `clarify` — copy, labels, error messages
- `onboard` — first-run experience
- `normalize` — design system alignment
- `extract` — component extraction

### Power Tools
- `overdrive` — push past conventional limits
- `frontend-design` — core principles (always first)
- `teach-impeccable` — project context setup (run once)

## References Within frontend-design

The `frontend-design` reference has its own sub-references for deep dives:

```
references/frontend-design/reference/typography.md
references/frontend-design/reference/color-and-contrast.md
references/frontend-design/reference/spatial-design.md
references/frontend-design/reference/motion-design.md
references/frontend-design/reference/interaction-design.md
references/frontend-design/reference/responsive-design.md
references/frontend-design/reference/ux-writing.md
```
