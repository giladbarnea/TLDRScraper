---
last_updated: 2026-04-16 12:03
---
.
├── .agents
├── .claude
│  ├── settings.backup.json
│  └── settings.json
├── .githooks
│  ├── post-checkout.disabled
│  ├── post-merge
│  ├── pre-commit
│  ├── README.md
│  ├── sync-subdir.sh
│  ├── sync-upstream-suggestions.md
│  └── util.sh
├── .github
│  └── workflows
│     ├── GEMINI_REMOTE_AUTH.md
│     ├── maintain-documentation.yml
│     ├── nightly-vercel-cleanup.yml
│     ├── weekly-branch-pr-cleanup.yml
│     ├── weekly-supabase-cleanup.yml
│     └── WORKFLOW_DIAGRAM.md
├── .pi
│  └── settings.json
├── adapters
│  ├── __init__.py
│  ├── aiwithmike_adapter.py
│  ├── anthropic_adapter.py
│  ├── anthropic_news_adapter.py
│  ├── bytebytego_adapter.py
│  ├── claude_blog_adapter.py
│  ├── cloudflare_adapter.py
│  ├── danluu_adapter.py
│  ├── deepmind_adapter.py
│  ├── google_research_adapter.py
│  ├── hackernews_adapter.py
│  ├── hillel_wayne_adapter.py
│  ├── jessitron_adapter.py
│  ├── lenny_newsletter_adapter.py
│  ├── lucumr_adapter.py
│  ├── martin_fowler_adapter.py
│  ├── netflix_adapter.py
│  ├── newsletter_adapter.py
│  ├── pointer_adapter.py
│  ├── pragmatic_engineer_adapter.py
│  ├── react_status_adapter.py
│  ├── savannah_adapter.py
│  ├── simon_willison_adapter.py
│  ├── softwareleadweekly_adapter.py
│  ├── stripe_engineering_adapter.py
│  ├── tldr_adapter.py
│  ├── trendshift_adapter.py
│  ├── will_larson_adapter.py
│  └── xeiaso_adapter.py
├── api
│  └── index.py
├── client
│  ├── scripts
│  │  └── lint.sh
│  ├── src
│  │  ├── components
│  │  │  ├── ArticleCard.jsx
│  │  │  ├── ArticleList.jsx
│  │  │  ├── BaseOverlay.jsx
│  │  │  ├── CalendarDay.jsx
│  │  │  ├── DigestButton.jsx
│  │  │  ├── DigestOverlay.jsx
│  │  │  ├── Feed.jsx
│  │  │  ├── FoldableContainer.jsx
│  │  │  ├── NewsletterDay.jsx
│  │  │  ├── OverlayContextMenu.jsx
│  │  │  ├── ReadStatsBadge.jsx
│  │  │  ├── ScrapeForm.jsx
│  │  │  ├── Selectable.jsx
│  │  │  ├── SelectionActionDock.jsx
│  │  │  ├── SelectionCounterPill.jsx
│  │  │  ├── ToastContainer.jsx
│  │  │  └── ZenModeOverlay.jsx
│  │  ├── contexts
│  │  │  └── InteractionContext.jsx
│  │  ├── hooks
│  │  │  ├── useArticleState.js
│  │  │  ├── useDigest.js
│  │  │  ├── useFeedLoader.js
│  │  │  ├── useLocalStorage.js
│  │  │  ├── useLongPress.js
│  │  │  ├── useOverlayContextMenu.js
│  │  │  ├── useOverscrollUp.js
│  │  │  ├── usePullToClose.js
│  │  │  ├── useScrollProgress.js
│  │  │  ├── useSummary.js
│  │  │  ├── useSupabaseStorage.js
│  │  │  ├── useSwipeToRemove.js
│  │  │  └── useTrackedState.js
│  │  ├── lib
│  │  │  ├── articleActionBus.js
│  │  │  ├── feedMerge.js
│  │  │  ├── interactionConstants.js
│  │  │  ├── markdownUtils.js
│  │  │  ├── quakeConsole.js
│  │  │  ├── requestUtils.js
│  │  │  ├── scraper.js
│  │  │  ├── selectionUtils.js
│  │  │  ├── stateTransitionLogger.js
│  │  │  ├── storageApi.js
│  │  │  ├── storageKeys.js
│  │  │  ├── toastBus.js
│  │  │  └── zenLock.js
│  │  ├── reducers
│  │  │  ├── articleLifecycleReducer.js
│  │  │  ├── gestureReducer.js
│  │  │  ├── interactionReducer.js
│  │  │  └── summaryDataReducer.js
│  │  ├── App.jsx
│  │  ├── index.css
│  │  └── main.jsx
│  ├── .gitignore
│  ├── ALL_STATES.md
│  ├── biome.json
│  ├── CLIENT_ARCHITECTURE.md
│  ├── index.html
│  ├── package-lock.json
│  ├── package.json
│  ├── postcss.config.js
│  ├── UI_DESIGN.md
│  └── vite.config.js
├── scripts
│  ├── setup
│  │  ├── build_client.sh
│  │  ├── common.sh
│  │  ├── create_digests_table.sql
│  │  ├── ensure_submodules.sh
│  │  ├── ensure_tooling.sh
│  │  └── ensure_uv_and_sync.sh
│  ├── auto-pr-merge.sh
│  ├── clean_vercel_deployments.py
│  ├── generate_context.py
│  ├── generate_tree.py
│  ├── install-codex-cli.sh
│  ├── install-gemini-cli.sh
│  ├── markdown_frontmatter.py
│  ├── print_root_markdown_files.sh
│  ├── resolve_quiet_setting.sh
│  ├── run-agent.sh
│  ├── run-codex.sh
│  ├── run-gemini.sh
│  └── update_doc_frontmatter.py
├── thoughts
│  ├── 25-12-21-failed-scrapes-are-retryable
│  │  └── discussion.md
│  ├── 26-04-03-selection-dock-state-machine
│  │  ├── plan.md
│  │  └── plan.review.md
│  ├── 26-04-04-workflow-machine
│  │  ├── discussion-raw.md
│  │  └── plan.md
│  └── 26-04-07-context-menu-research
│     ├── plans
│     │  ├── plan-final.md
│     │  ├── plan-g.md
│     │  └── plan-x.md
│     ├── research
│     │  └── description.md
│     └── relevant-files.md
├── .gitattributes
├── .gitignore
├── .gitmodules
├── .vercelignore
├── AGENTS.md
├── ARCHITECTURE.md
├── BUGS.md
├── CLAUDE.md
├── CODEX.md
├── GEMINI.md
├── GOTCHAS.md
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── serve.py
├── setup.sh
├── source_routes.py
├── storage_service.py
├── summarizer.py
├── supabase_client.py
├── tldr_app.py
├── tldr_service.py
├── TLDRScraper.code-workspace
├── util.py
├── uv.lock
└── vercel.json
