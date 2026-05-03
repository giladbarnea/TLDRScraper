---
name: server/summaries
description: Backend summary generation pipeline and LLM prompt templates.
last_updated: 2026-05-03 15:10, bb6b54a
---
# Server: Summaries

[→ Client: Summaries & Digests](../client/summaries-and-digests.md) | [→ State Machines: Articles & Summaries](../state-machines/articles-and-summaries.md)

### Feature 3: Summary Generation - Complete Flow

```
User requests a summary from the client
  │
  ├─ useSummary decides whether summary content already exists
  │    │
  │    ├─ Summary already cached
  │    │    │
  │    │    └─ Reuse cached markdown and open the reading surface
  │    │
  │    └─ Summary missing
  │         │
  │         └─ POST /api/summarize-url
  │              │
  │              └─ Server receives request...
  │                   │
  │                   ├─ serve.py summarize_url_endpoint()
  │                   │    │
  │                   │    └─ tldr_app.py summarize_url(url, summarize_effort)
  │                   │         │
  │                   │         └─ tldr_service.py summarize_url_content(url, summarize_effort)
  │                   │              │
  │                   │              ├─ util.canonicalize_url(url)
  │                   │              │
  │                   │              └─ summarizer.py summarize_url(url, summarize_effort)
  │                   │                   │
  │                   │                   ├─ url_to_markdown(url)
  │                   │                   ├─ _fetch_summary_prompt()
  │                   │                   ├─ Build prompt from template + markdown
  │                   │                   └─ _call_llm(prompt, summarize_effort)
  │                   │
  │                   └─ Return { success, summary_markdown, canonical_url, summarize_effort }
  │
  └─ Client persists the summary on the article payload and can open the reading surface immediately
```

---
