# Technique suggestion: Domain C (Summary view reducer)

## Intent
Domain C focuses on the summary view UI (`collapsed` ↔ `expanded`). A reducer for this domain could keep the overlay/view logic explicit while staying closed and easy to coordinate with Domain B (summary data) and Domain A (lifecycle). The approach below is meant as a small, low-ceremony technique that might reduce coordination friction.

## Proposed technique (advisory)
### 1) Keep Domain C narrowly scoped
A minimal state shape could be something like:
- `mode: 'collapsed' | 'expanded'`
- `expandedBy: 'tap' | 'summary-loaded' | null` (optional, for analytics or debugging)

Events could be deliberately small:
- `SUMMARY_VIEW_OPEN_REQUESTED`
- `SUMMARY_VIEW_CLOSE_REQUESTED`
- `SUMMARY_DATA_AVAILABLE` (from Domain B)
- `ARTICLE_REMOVED` (from Domain A)

The reducer can stay closed by only reacting to those events and returning `{ state, commands }` without reading other domains directly.

### 2) Favor a “command emission” pattern over direct effects
When the view is opened from a tap, the reducer could emit a command such as `ENSURE_SUMMARY_DATA`. The runtime (hook) would interpret that command and ask Domain B to fetch if needed. This might keep Domain C simple while still making “open → fetch if missing → render” feasible.

### 3) Use outcome-based coordination
If Domain B emits `SUMMARY_DATA_AVAILABLE`, Domain C could treat that as a soft open signal (or ignore it, depending on desired behavior). This allows you to test two variants with minimal code churn:
- **Variant A:** Auto-open on `SUMMARY_DATA_AVAILABLE` (might feel “smart” but could surprise users).
- **Variant B:** Only open on explicit user action (might feel more predictable, especially on mobile).

A mediator could translate Domain B outcomes into Domain C events without the reducers reading each other.

### 4) Consider a “single-owner” overlay lock
If you need to prevent multiple expanded summaries, Domain C could track `expandedArticleId` in its state. That might reduce UI edge cases (e.g., overlapping overlays), but it may also make transitions slightly more verbose. You could treat this as an experiment: if the UI starts to feel inconsistent, a single-owner lock might be a low-risk fix.

## Hypothesized outcomes (not guaranteed)
- The reducer might make the summary overlay behavior easier to reason about, especially under rapid tap/swipe interactions.
- A command-based bridge could lower the risk of accidental coupling between Domain C and Domain B.
- A single-owner lock might reduce overlay glitches, though it could also introduce new UX expectations (e.g., tapping a different article implicitly closes the current overlay).

## Open questions worth discussing
- Should `SUMMARY_DATA_AVAILABLE` auto-expand or simply enable tap-to-expand?
- If the user removes an article while expanded, should the overlay close immediately or after a brief animation?
- Do we need telemetry for view transitions, or can we keep Domain C purely behavioral for now?
