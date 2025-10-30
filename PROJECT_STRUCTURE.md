---
last-updated: 2025-10-30 21:38, c50a78b
---

.
├── .claude
│   ├── agents
│   │   ├── codebase-analyzer.md -> agents/codebase-analyzer.md
│   │   ├── codebase-locator.md -> agents/codebase-locator.md
│   │   ├── codebase-pattern-finder.md -> agents/codebase-pattern-finder.md
│   │   ├── thoughts-analyzer.md -> agents/thoughts-analyzer.md
│   │   ├── thoughts-locator.md -> agents/thoughts-locator.md
│   │   └── web-search-researcher.md -> agents/web-search-researcher.md
│   └── commands
│       ├── create_plan_lite.md -> commands/create_plan_lite.md
│       ├── debug.md -> commands/debug.md
│       ├── implement_plan.md -> commands/implement_plan.md
│       └── research_codebase.md -> commands/research_codebase.md
├── .githooks
│   ├── pre-merge-commit
│   └── README.md
├── .github
│   └── workflows
│       ├── update-doc-frontmatter.yml
│       └── update-project-structure.yml
├── .gitignore
├── .replit
├── agent-commands
│   └── output
│       ├── hackernews-integration-plan.md
│       └── hackernews-integration-research.md
├── AGENTS.md
├── api
│   └── index.py
├── ARCHITECTURE.md
├── BUGS.md
├── client
│   ├── .gitignore
│   ├── .vscode
│   │   └── extensions.json
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── src
│   │   ├── App.vue
│   │   ├── components
│   │   │   ├── ArticleCard.vue
│   │   │   ├── ArticleList.vue
│   │   │   ├── CacheToggle.vue
│   │   │   ├── ResultsDisplay.vue
│   │   │   └── ScrapeForm.vue
│   │   ├── composables
│   │   │   ├── useArticleState.js
│   │   │   ├── useCacheSettings.js
│   │   │   ├── useLocalStorage.js
│   │   │   ├── useScraper.js
│   │   │   └── useSummary.js
│   │   └── main.js
│   └── vite.config.js
├── CLIENTSIDE_TESTING.md
├── docs
│   └── multi-newsletter-plan.md
├── experimental
│   └── ralph_article_scrape
│       ├── article_structure.json
│       ├── download_media.py
│       ├── gemini_api_troubleshooting.md
│       ├── parse_article.py
│       ├── ralph_article.html
│       ├── ralph_article_enhanced.md
│       ├── ralph_article_media.txt
│       ├── ralph_media
│       │   ├── download_results.json
│       │   ├── media_02.jpg
│       │   ├── media_05.jpg
│       │   ├── media_07.jpg
│       │   ├── media_08.png
│       │   ├── media_11.jpg
│       │   ├── media_12.jpg
│       │   ├── media_13.jpg
│       │   ├── media_14.jpg
│       │   ├── media_15.jpg
│       │   ├── media_16.jpg
│       │   ├── media_17.jpg
│       │   └── media_18.jpg
│       └── README.md
├── eza_x86_64-unknown-linux-gnu.tar.gz
├── hackernews_adapter.py
├── newsletter_adapter.py
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── package-lock.json
├── package.json
├── PROJECT_STRUCTURE.md
├── pyproject.toml
├── requirements.txt
├── scripts
│   └── update_doc_frontmatter.py
├── serve.py
├── setup-hooks.sh
├── setup.sh
├── summarizer.py
├── templates
│   └── index.html
├── tests
│   ├── playwright
│   │   └── localStorage.spec.ts
│   ├── remove-order.spec.ts
│   └── section-layout.spec.ts
├── thoughts
│   └── shared
│       └── plans
│           └── 2025-10-28-fix-cache-ui-state-sync.md
├── tldr_adapter.py
├── tldr_app.py
├── tldr_service.py
├── TLDRScraper.code-workspace
├── util.py
├── uv.lock
└── vercel.json
