---
last_updated: 2026-02-20 07:52
---
# Article Digest (Selected Articles) — Advisory Plan

This plan is intentionally advisory: a few choices (storage model, digest identity, UX affordances, and token strategy) could go multiple ways, and it might be worth deciding them explicitly before implementation.

---

## Pass 1 — High-Level Architecture (End-to-End)

### Intended user-facing behavior (inputs → outputs)

**Primary input:**
- A user selection set of articles in the Feed (leveraging the existing selection mode and selected IDs).

**Secondary inputs (optional, but likely useful):**
- Digest “effort” / depth (mirroring the existing summary effort concept).
- A small set of “digest options” (tone, length, grouping preference), if you want this to evolve beyond a single default.

**Primary output:**
- A single, multi-article digest rendered in the existing Zen-style overlay UI (same overall “reading mode” affordances: close, pull-to-close, progress, etc.).

**Secondary outputs (useful for robustness/UX):**
- An explicit list of which URLs were included vs. skipped (scrape failed, duplicate, blocked, etc.).
- A stable digest identifier that allows cache hits and persistence across sessions.

### Data flow (user action → rendered digest)

1. User enters Select mode via long-press and selects N articles (potentially spanning multiple dates/sources).
2. User triggers “Generate digest” from a small UI affordance that is only visible when selection is non-empty.
3. Client packages the selected articles (at minimum URLs; ideally also title + a bit of metadata) and sends a single request to a new backend endpoint.
4. Backend canonicalizes URLs, fetches/derives content, builds a multi-article prompt, calls Gemini 3, and returns digest markdown plus metadata.
5. Backend persists the digest result in Supabase (for cache hits, later retrieval, and to avoid recomputation).
6. Client opens a Zen-style overlay showing the digest (markdown → sanitized HTML pipeline), and optionally offers “apply actions” to the underlying articles (mark read, remove, clear selection).

### Where the digest “lives” in the current architecture

The digest feature likely touches and composes these existing systems:
- **Selection system** (existing global interaction state, selected IDs, and header pill UI).
- **Zen overlay pattern** (portal-based full-screen reading UI with gestures).
- **Summary pipeline patterns** (async request state, markdown → HTML rendering, optimistic UI conventions).
- **Storage layer** (Supabase-backed persistence via Flask endpoints, with client-side reactive caching).
- **Gemini summarizer integration** (prompt templating + API calls).

The digest is conceptually “derived content,” like per-article summaries, but with a key distinction: it’s derived from a *set* of articles, not one article or one date.

---

## Pass 2 — Module-Level Enrichment (Interfaces & Contracts)

### Client — Selection-driven trigger UI

**What could change:**
- Add a “Generate digest” action that only appears when the selection set is non-empty.
- Reuse the existing “selection counter” placement as the pattern anchor (header-level action), or consider a floating action button if you want it more prominent on mobile.

**Interface-level data gathering:**
- One approach would be to derive selected article objects by filtering the already-rendered payloads by selected IDs (rather than trying to enrich the interaction context with full article objects).
- Digest inputs could include:
  - `url` (required)
  - `title` (strongly recommended for prompt quality)
  - `issueDate` / `date` (optional; good for grouping or ordering)
  - `sourceId` / `category` / `section` (optional; helps the model structure the digest)

**UX guardrails worth considering:**
- A selection size cap (or “you selected 47 items—digest might be slow/expensive” confirmation).
- A quick “clear selection” behavior after a successful digest, or keeping it for follow-up actions (both are defensible).

### Client — Digest async state + overlay rendering

**Pattern to mirror:**
- The existing summary hook (`useSummary`) appears to combine:
  - a persisted data lifecycle (unknown/loading/available/error),
  - and an ephemeral view lifecycle (overlay expanded/collapsed),
  - plus a single-overlay-at-a-time lock.

**Digest-specific divergence:**
- Digest state is keyed by a *set* of URLs, so the digest hook (`useDigest`) would likely be keyed by a stable digest identifier rather than `(date, url)`.
- The Zen overlay header content might need to shift from “single domain favicon + metadata” to “N articles selected” and possibly a compact list or chips of sources.

**Digest overlay actions (optional):**
- “Mark all as read” and/or “remove all” could be offered as explicit actions; gesture-driven “complete” could also be mapped to a bulk action, but that might be risky without a confirmation step.

**Zen lock decision point:**
- One approach would be to share the same “only one overlay open” lock across article summary overlays and the digest overlay (simplest mental model).
- Another approach would be separate locks (allows more flexibility, but can increase edge cases).

### Client ↔ Backend — New API contract

**Endpoint (proposed shape):**
- `POST /api/digest` (or similar) that accepts a list of selected articles and returns a digest plus a digest identifier.

**Request body (example shape):**
```json
{
  "articles": [
    { "url": "https://example.com/a", "title": "…", "issue_date": "2026-02-20", "source_id": "tldr_tech" },
    { "url": "https://example.com/b", "title": "…", "issue_date": "2026-02-19", "source_id": "hackernews" }
  ],
  "digest_effort": "low",
  "digest_options": {
    "max_sections": 6,
    "include_links": true
  }
}
```

**Response body (example shape):**
```json
{
  "success": true,
  "digest_id": "…",
  "digest_markdown": "…",
  "included_urls": ["…"],
  "skipped": [{ "url": "…", "reason": "fetch_failed" }],
  "digest_effort": "low",
  "generated_at": "2026-02-20T12:34:56Z"
}
```

**Notes:**
- Returning `included_urls` and `skipped` could keep the client honest about what actually made it into the digest.
- If you want cache hits, returning a stable `digest_id` is useful even when the digest is newly generated.

### Backend — Digest orchestration (Gemini 3, multi-article)

**What could change:**
- Add a new route to `serve.py` that follows the same envelope conventions and error mapping as existing endpoints.
- Add a new app/service path that mirrors the current “route → app → service” layering, but for digest generation.

**Prompting strategy decision point (token risk):**
- Multi-article content can blow up prompt size quickly; a conservative approach might be:
  - constrain N (max articles),
  - and constrain per-article extracted content,
  - or use a two-stage approach (per-article compression → combined digest).
- If you go two-stage, you may want the API response to expose that some articles were summarized more aggressively than others (so users aren’t surprised).

**Template strategy:**
- One approach would be to introduce a dedicated multi-article digest prompt template (separate from the single-URL summary template) so you can evolve it without destabilizing single-article summaries.

### Supabase persistence — Where the digest should be stored

This is a core decision because selection is not necessarily “per date”.

**Option A: Embed digest into `daily_cache` payload**
- Could work well if you scope digests to “one digest per day” (or “per selected set within one day”).
- Becomes awkward if selection spans multiple days (you’d need to pick an anchoring date or store it multiple places).

**Option B: Store digest as a key/value in `settings`**
- Minimal plumbing, but semantically off (digests are content, not settings) and may make future querying/listing harder.

**Option C (often cleanest for set-based identity): A dedicated `digests` table**
- Digest identity could be `digest_id` (stable hash of canonical URLs + prompt version + effort).
- Row payload could include:
  - `digest_id`
  - `article_urls` (ordered canonical URLs)
  - `digest_markdown`
  - `status` + `error`
  - `generated_at`
  - optional: `source_snapshot` (titles + metadata for later display without re-fetching)

**Advisory recommendation:**
- If you expect cross-date selection to be common, a dedicated `digests` table might reduce coupling and avoid awkward anchoring rules.
- If you want the smallest MVP and you’re comfortable initially constraining selection to a single date, embedding into the daily payload could be simplest.

### Storage keys & caching semantics

If you introduce a dedicated digest store, you might consider:
- A stable digest key prefix (e.g., `digests:{digest_id}`) for client storage routing.
- Cache behavior: treat digests as immutable-by-default (regenerate by creating a new `digest_id` via prompt version bump or options changes), which can simplify race concerns.

---

## Watch-outs (Flows that might break / deserve extra attention)

- **Selection → “open item” decision logic**: introducing a new “digest action” in Select mode could accidentally interfere with existing short-press vs long-press suppression if the new UI is nested in interactive containers.
- **Zen overlay lock semantics**: if digest and per-article overlays share a global lock, it’s easy to create “nothing opens” states unless ownership and release rules stay simple and visible to users.
- **Supabase write amplification**: if the digest is embedded into the daily payload, frequent article-level state writes could repeatedly rewrite large digest text and increase the likelihood of read-modify-write races.
- **Prompt size / latency**: multi-article scraping + markdown conversion + Gemini call could become slow enough that client loading states, abort behavior, and retries become a real UX issue.
- **Canonicalization mismatches**: digest identity and caching likely depend on canonical URLs; any mismatch between client URLs and backend canonicalization could cause surprising cache misses or duplicates.

