---
status: completed
plan: unified-feed-read-model-plan.md
parent_implementation: summary.md
branch: fix-data-inconsistency
pr: 661
last_updated: 2026-05-10 17:52
---

# Digest Collapse Key Scoping — PR 661 Fixup

A drive-by reviewer flagged two concerns on PR 661. One was real and load-bearing on the read-model invariants the parent plan establishes; one was theoretical with no demonstrable trigger today. Acting on both by reflex would have papered over an already-correct spot, so we fixed the first and explicitly deferred the second.

## What was actually wrong

`useDigest.collapse` was the last URL-as-identity site in the new read model. The digest record stored only the URLs of participating articles, and collapse re-resolved those URLs against the entire `articlesByKey` map. The plan's invariant that "two identical URLs on different dates remain distinct article keys" therefore held everywhere except here — collapsing a digest could mutate every same-URL slice across the store, including ones that were never selected. TLDR newsletters re-link popular articles across days, so this was a realistic foot-gun, not a contrived one.

## Decision: store keys, not URLs, on the digest

The selected articles already carry their keys at trigger time (selection has been key-scoped since the parent implementation). The fix threads those keys through to the persisted digest record so collapse needs no lookup at all — it just unrolls the keys it was given. We kept `articleUrls` on the digest record because `useElaboration` posts URLs to `/api/elaborate`; that contract is unchanged. The trigger-time "same selection? just expand" short-circuit was migrated to key comparison in the same edit because URL equality has the same identity-blurring problem there.

Removing `findArticleKeysByUrls` from `articleStore` was deliberate: leaving a URL→keys helper around invites the same bug to reappear elsewhere. With the digest collapse fixed, no caller needs it, and its absence is the simplest enforcement of the read-model invariant.

## Drift

The original plan never identified the digest collapse path as a remaining URL-as-identity site — at the time the plan was written, the focus was on the loader and rendering tree, where most URL identity lived. So this is a closure on a corner the plan didn't cover, not a deviation from it.

## What we deferred (Comment 1)

The reviewer also noted that `recomputeVisibleDates` derives from every key in `daysByDate` without a date-level pruning path, so a load that returns a strict subset of previously-rendered dates could leave stale day slices visible. Walking the actual flow, the current scrape and Supabase paths don't shrink the date set within a fixed range; the only realistic trigger is the DebugPanel cache-clear followed by a partial reload. We left this alone rather than add defensive day-deletion logic that would solve a hypothetical at the cost of more state machine. Worth revisiting if a reproducer surfaces.

## Verification

We seeded a real cross-date duplicate in Supabase by injecting one of 2026-05-07's TLDR Tech articles into 2026-05-08's payload (kept a backup for clean teardown). The pre-fix bug manifests cleanly with that seed; post-fix, collapsing a digest on either date leaves the other date's copy untouched. The existing store-level Vitest suite passes unchanged — these were the right tests to leave alone, since the bug lived above the store, in how the digest hook resolved keys.
