# Design Migration Planning Task

## Context: Where We Are

We've created 3 refined mock design variations for the TLDRScraper app. These are standalone prototypes (TypeScript React apps) that demonstrate different aesthetic approaches to the same UI. They're stored in separate branches:
- `mock-design-ultra-minimal`
- `mock-design-japanese-zen`
- `mock-design-warm-breath`

Each mock is a **simplified, non-functional resemblance** of the real app:
- Contains hardcoded mock data
- No backend integration, no API calls
- Missing several components (ScrapeForm, CacheToggle, context buttons, stats, etc.)
- Simplified structure: just article display + basic interactions

**The mock files live in the repository root:**
- `App.tsx` (main component)
- `components/ArticleCard.tsx`
- `data/mockData.ts`
- `index.html`, `vite.config.ts`, `package.json`, etc.

**The real working app lives in `client/` directory:**
- Full React 19 application
- Complex state management via custom hooks
- Server integration (Flask backend + Supabase database)
- 7+ components with intricate interactions

## Your Task

We need to **migrate one mock design to the real production app**. This is not a copy/paste job - it's thoughtful extraction and application of design principles.

{design_message_and_description}

## The Challenge

The mock demonstrates design philosophy through:
- Typography choices and hierarchy
- Color palette and application
- Spacing/whitespace patterns
- Border styles, shadows, visual depth
- Interaction patterns (hover states, transitions)
- Overall tone and feel

**You must:**
1. Extract these design principles from the mock
2. Apply them systematically to every real component
3. Ensure 100% visual replacement of existing design
4. Maintain all existing functionality without breaking logic

**Critical constraints:**
- Mock is simplified - it doesn't show where ScrapeForm, CacheToggle, context buttons go
- Real app has complex state transitions, loading states, error states
- Real app has database-persisted state (read/unread/removed articles, TLDRs, cache)
- Real app has server interactions with loading indicators, progress bars
- Design must adapt to these complexities the mock doesn't address

## What You Need to Deeply Understand

Before planning, you must thoroughly research:

### 1. The Mock Design (check out the branch)
- Typography: Fonts, sizes, weights, line heights
- Colors: Palette, semantic usage (primary/accent/muted/error)
- Spacing: Padding, margins, gaps between elements
- Layout: Structure, alignment, responsive behavior
- Interactions: Hover effects, transitions, focus states
- Visual hierarchy: How importance is communicated
- Component patterns: How cards, buttons, forms are styled

### 2. The Real App Architecture
Run `./scripts/print_root_markdown_files.sh` for project context, then:

**Client Architecture:**
- All components in `client/src/components/`
- Custom hooks in `client/src/hooks/`
- What state each component manages
- Component hierarchy and data flow
- How components interact with each other

**State & Interactions:**
- Article states: unread → read → removed → tldr-hidden
- User interactions: scraping, caching, TLDR generation, article management
- Loading/error states for async operations
- Database persistence patterns (when/how state is saved)

**Component Inventory (must style each):**
- `App.jsx` - Root component, layout
- `ScrapeForm.jsx` - Date inputs, scrape button, progress bar
- `CacheToggle.jsx` - Cache enable/disable toggle
- `ResultsDisplay.jsx` - Stats, debug logs, results container
- `ArticleList.jsx` - Groups articles by date/issue
- `ArticleCard.jsx` - Individual article with title, meta, TLDR, actions

**Features Not in Mock:**
- Date range scraping UI
- Progress bar during scraping
- Cache status indicator
- Context download buttons (newly added to main)
- Stats display (article count, unique URLs, etc.)
- Debug logs toggle
- Newsletter issue grouping
- Section headers within issues

## Your Planning Process

1. **Check out the design branch** and deeply study the mock
2. **Analyze the real app** by reading `client/` source code
3. **Extract design system** from mock into reusable patterns:
   - CSS variables for colors, spacing, typography
   - Component styling patterns
   - Interaction patterns
4. **Map mock → real components:**
   - How should ScrapeForm look given the design language?
   - How should progress bars, toggles, buttons be styled?
   - How should stats/debug sections integrate?
   - Where do context buttons fit in the visual hierarchy?
5. **Plan systematic migration:**
   - Order of component styling (dependency-aware)
   - CSS organization strategy
   - Testing checkpoints (visual regression)
   - Risk areas (state transitions, complex interactions)

## Deliverable

A comprehensive plan that addresses:
- Design system extraction (variables, patterns)
- Component-by-component styling strategy
- Handling of elements not in mock (progress bars, stats, etc.)
- Testing/verification approach
- Risk mitigation for complex state interactions
- Estimated effort and sequencing

**The plan should enable any developer to execute the migration systematically, ensuring:**
- 100% visual design replacement
- Zero functional regressions
- Consistent application of design principles
- Polished, production-ready result
