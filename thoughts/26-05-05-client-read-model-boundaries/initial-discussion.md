---
last_updated: 2026-05-05 18:25, a006dd4
result_of: fix/newsletter-counter-and-container-reactivity
pertains_to: GOTCHAS.md 2026-05-05 ‘Derived multi-article UI can still go stale after a "store-backed" fix if the subscription shape is wrong’ entry
---

Yes — **one** meaningful smell stands out.

The store architecture itself is directionally good. The smell is that the client still has **two competing read models for the same concept of “article state”**:

- a payload-shaped `article` object flowing down the component tree, and
- the live `articleStore` slice keyed by `(date, url)`.

Both are rich enough that a component can plausibly read `removed`, `read`, `summary`, or even key-ish fields like `issueDate` from the wrong one and still look “correct” in code review. That is the problem. **Authority is not encoded strongly enough in the API surface.**

That is why this bug was easy to “fix” incorrectly. The code had already moved off one bad path, so it *looked* aligned with the architecture. But the architecture still allowed grouped UI to be derived in ad-hoc ways: sometimes from live selectors, sometimes from structural props, sometimes from a subscription shape that only *seemed* equivalent. The system is solid at the **per-article write model**, but weaker at the **grouped read model**.

What makes this feel like a real pattern rather than a one-off is that it rhymes with earlier failures. The `issueDate` bug was also an authority problem: a field looked like it came from upstream data, but its true owner was the day key. The dock staleness noted in the audit is likely the same family too: grouped UI depending on live fields without a first-class grouped selector/invalidation model. Different symptoms, same underlying leak.

So if I had to name the deeper smell precisely, I’d call it this:

> **The transport/render prop shape still exposes mutable state that is supposed to be owned by the live store.**

That makes the architecture rely on developer discipline instead of design constraints.

The healthiest long-term direction is not a rewrite. It is to make the boundary sharper:

Structural props should be just that — structural.  
Things like title, url, source, section, order, date grouping.

Mutable lifecycle/view state should be impossible, or at least unnatural, to read from props. It should come only from first-class selectors, including **group selectors** for grouped UI such as badges, all-removed state, and selected-summary affordances.

In other words: the real lesson here is not “be more careful with `useSyncExternalStore`.”  
It is:

**Make the wrong source of truth harder to access.**

That would remove an entire class of gotchas, not just this one.
