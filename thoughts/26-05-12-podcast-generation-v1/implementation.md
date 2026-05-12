---
plan: null
last_updated: 2026-05-12 08:22
---

# Podcast Generation v1 — Implementation Notes

## Scope landed

This pass moved podcast generation from a single-source backend proof of concept toward a selected-article workflow. The server endpoint now accepts a selected URL list, and the client selection dock exposes a `Podcast` action beside `Digest` for multi-selection mode.

The first pass intentionally stopped before audio response handling. The follow-up pass now consumes the returned audio blob, creates an object URL, and mounts a minimal bottom audio player. It still does not persist playback state or surface errors to the user beyond console logging.

## Decisions

The backend follows the established digest/elaboration input shape: normalize the selected list first, canonicalize URLs, fetch source bodies in parallel, then pass one structured source document downstream. Reusing `tldr_service._fetch_article_markdowns_parallel` kept the scrape semantics aligned with the existing multi-article paths instead of introducing a parallel implementation in `podcast_service.py`.

The podcast source document now uses XML-like tags, matching the prompt style already used around digest and elaboration inputs. This is meant to make multi-source boundaries obvious to `podcast_creator` without adding another prompt abstraction yet.

The podcast cache key is now source-set based rather than single-URL based. The storage column name remains `canonical_url` because that is the deployed schema, but `docs/server/storage.md` now calls out that the column stores a stable source-set key for multi-source podcast episodes.

On the client, `SelectionActionDock` owns the button shape while `App.jsx` owns the request handler and audio-object URL lifecycle. `PodcastPlayer` is intentionally a tiny playback surface rather than a feature state machine: it controls a native audio element, skip controls, and dismissal only.

For player testing, `serve.py` temporarily short-circuits `/api/podcast` to return a known local MP3 fixture. That isolates client playback work from slow podcast generation and expensive upstream model calls.

## Challenges

The main ambiguity was where the podcast feature should live architecturally. Digest has a full persisted read model and overlay, while podcast currently has only a blocking server endpoint that returns raw audio bytes. Adding a hook now would imply a larger state machine than the current feature needs, so the implementation keeps the client wiring deliberately thin.

The other wrinkle is storage naming. Renaming the database column would be cleaner semantically, but it would turn a small feature pass into a migration. Treating `canonical_url` as a legacy physical column and documenting the logical cache-key meaning keeps the change focused.

## Drift from plan

There was no formal plan file for this v1 pass. The implementation was driven by the existing digest flow and the earlier podcast-generation v0 notes.

## Follow-ups

The next meaningful step is replacing the server fixture with real generated audio again, then deciding whether successful playback should clear selection like digest does. A dedicated `usePodcast` hook may become justified once generation progress, playback state, cache metadata, and error UX become real product states.
