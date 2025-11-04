.
├── .claude
│   ├── agents
│   │   ├── codebase-analyzer.md
│   │   ├── codebase-locator.md
│   │   └── codebase-pattern-finder.md
│   └── commands
│       ├── create_plan_lite.md
│       ├── implement_plan.md
│       ├── research_codebase.md
│       └── research_codebase_nt.md
├── .gitattributes
├── .githooks
│   ├── post-checkout
│   ├── post-merge
│   ├── post-rewrite
│   ├── pre-merge-commit
│   └── README.md
├── .github
│   └── workflows
│       ├── copy-agents-to-claude.yml
│       ├── update-doc-frontmatter.yml
│       └── update-project-structure.yml
├── .gitignore
├── AGENTS.md
├── api
│   └── index.py
├── ARCHITECTURE.md
├── BUGS.md
├── CLAUDE.md
├── client
│   ├── .gitignore
│   ├── .vscode
│   │   └── extensions.json
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── components
│   │   │   ├── ArticleCard.css
│   │   │   ├── ArticleCard.jsx
│   │   │   ├── ArticleList.css
│   │   │   ├── ArticleList.jsx
│   │   │   ├── CacheToggle.css
│   │   │   ├── CacheToggle.jsx
│   │   │   ├── ResultsDisplay.css
│   │   │   ├── ResultsDisplay.jsx
│   │   │   ├── ScrapeForm.css
│   │   │   └── ScrapeForm.jsx
│   │   ├── hooks
│   │   │   ├── useArticleState.js
│   │   │   ├── useLocalStorage.js
│   │   │   └── useSummary.js
│   │   ├── lib
│   │   │   └── scraper.js
│   │   ├── main.js
│   │   └── main.jsx
│   └── vite.config.js
├── docs
│   └── react-19
│       ├── react-19-2.md
│       ├── react-19-release.md
│       ├── react-19-upgrade-guide.md
│       ├── react-19-use.md
│       ├── react-compiler-1-0.md
│       ├── react-compiler-debugging.md
│       ├── react-compiler-install.md
│       ├── react-dom-hooks-useFormStatus.md
│       ├── react-separating-events-from-effects.md
│       ├── react-useActionState.md
│       ├── react-useOptimistic.md
│       └── react-useTransition.md
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
├── GOTCHAS.md
├── hackernews_adapter.py
├── newsletter_adapter.py
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── package-lock.json
├── package.json
├── pyproject.toml
├── README.md
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
│   ├── section-layout.spec.ts
│   └── unit
│       └── test_canonicalize_url.py
├── thoughts
│   ├── 25-11-04-code-duplication
│   │   └── plan.md
│   ├── 25-11-04-mixed-concerns-refactor
│   │   └── plan.md
│   └── done
│       ├── 25-10-30-multi-newsletter
│       │   └── plan.md
│       ├── 2025-11-04-remove-summarize
│       │   └── plans
│       │       └── remove-summarize-feature.md
│       └── shared
│           └── plans
│               ├── 2025-10-28-fix-cache-ui-state-sync.md
│               ├── hackernews-integration-plan.md
│               ├── hackernews-integration-research.md
│               └── vue-to-react-19-migration-plan.md
├── tldr_adapter.py
├── tldr_app.py
├── tldr_service.py
├── TLDRScraper.code-workspace
├── util.py
├── uv.lock
└── vercel.json
