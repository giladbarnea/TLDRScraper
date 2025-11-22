# Design Descriptions for Planner Prompt

Replace `{design_message_and_description}` in PLANNER_PROMPT_TEMPLATE.md with one of these:

---

## Ultra Minimal (Branch: mock-design-ultra-minimal)

**Philosophy:** Typography-first approach with extreme whitespace. Inspired by Apple's quiet confidence and restraint. Zero decoration, maximum clarity.

**Key characteristics:**
- **Typography:** Light Inter for body text, IBM Plex Mono for metadata
- **Colors:** Near-white background (#FAFAFA), charcoal text (#1A1A1A), subtle gray accents
- **Spacing:** Generous padding (48-64px gaps), breathing room around all elements
- **Interactions:** Minimal hover effects - slight opacity changes, no dramatic animations
- **Tone:** Confident simplicity. Feels like reading a clean document, not using an app.

**Design branch:** `mock-design-ultra-minimal`

**What makes it special:**
- No borders, no shadows, no gradients
- Pure typographic hierarchy (size + weight + spacing)
- Monospaced metadata creates technical, honest feel
- Lots of negative space - content breathes
- Feels lightweight, fast, unobtrusive

---

## Japanese Zen (Branch: mock-design-japanese-zen)

**Philosophy:** Muji-inspired calm and understated elegance. Warm neutrals, gentle transitions, wabi-sabi aesthetic. Design that feels like a quiet Sunday morning.

**Key characteristics:**
- **Typography:** Noto Sans with light to regular weights, harmonious scales
- **Colors:** Warm palette - cream background (#F5F1EB), soft brown text (#3E3832), beige accents (#E8DFD3)
- **Spacing:** Balanced - not as extreme as Ultra Minimal, but still generous
- **Interactions:** Gentle hover transitions (300ms ease), subtle background shifts
- **Tone:** Peaceful, honest, human. Feels handcrafted, not manufactured.

**Design branch:** `mock-design-japanese-zen`

**What makes it special:**
- Warm color temperature throughout
- Soft, natural aesthetic (like linen paper)
- Humble visual hierarchy - nothing screams for attention
- Gentle rounded corners (8px)
- Feels like a physical object you'd want to hold

---

## Warm Breath (Branch: mock-design-warm-breath)

**Philosophy:** Kinfolk magazine aesthetic. Slow living, generous space, ultra-light serif typography. Design that invites you to slow down and read thoughtfully.

**Key characteristics:**
- **Typography:** Crimson Pro serif with ultra-light weights (300-400), generous line height (1.7)
- **Colors:** Soft warm whites (#FFFBF5), warm gray text (#5A5550), peachy accents (#F8EDE3)
- **Spacing:** Maximum breathing room - wide margins, tall line heights
- **Interactions:** Smooth, slow transitions (400-500ms), gentle fades
- **Tone:** Meditative, editorial, luxurious. Feels like reading a premium lifestyle magazine.

**Design branch:** `mock-design-warm-breath`

**What makes it special:**
- Serif typography (rare in tech apps - bold choice)
- Ultra-light weights create airy, spacious feel
- Warm peach/cream tones throughout
- Very generous line spacing - prioritizes readability
- Feels like taking a deep breath - unhurried, present

---

## Usage Example

For **Ultra Minimal** design migration, use:

```markdown
## The Design You're Migrating

**Design branch:** `mock-design-ultra-minimal`

**Philosophy:** Typography-first approach with extreme whitespace. Inspired by Apple's quiet confidence and restraint. Zero decoration, maximum clarity.

[... rest of description from above ...]
```
