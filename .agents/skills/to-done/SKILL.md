---
name: to-done
description: Move an effort from `thoughts/` to the `thoughts/done/` directory after completion
argument-hint: thought-path
last_updated: 2025-12-14 17:16, 3e74d8a
---
Move $1 to `thoughts/done/<same-name>.md`, and aggressively compress it by at least 20x.

Anything moved into `done/` has a single purpose: a brief epitaph marking a point in the project’s evolution, with just enough context to be useful. By definition, it won’t meaningfully impact future work. Still, it’s valuable for anyone on the project to have shallow knowledge of past decisions—it squares away the perpetual “why things are the way they are” question, and helps us avoid developing in circles.

Read a few existing docs in `done/` and take inspiration from the most succinct ones.

Use `git mv` rather than `mv`.