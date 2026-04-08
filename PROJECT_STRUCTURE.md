---
last_updated: 2026-04-08 20:31
---
.
├── .agents
│  ├── agents
│  │  ├── codebase-analyzer-multiple-subsystems.md
│  │  ├── codebase-analyzer-single-subsystem.md
│  │  ├── codebase-locator.md
│  │  ├── react-antipattern-auditor.md
│  │  └── web-deep-researcher.md
│  └── skills
│     ├── architecture-create
│     │  └── SKILL.md
│     ├── architecture-sync-since-last-updated
│     │  └── SKILL.md
│     ├── catchup
│     │  └── SKILL.md
│     ├── co-develop
│     │  └── SKILL.md
│     ├── consensus
│     │  ├── scripts
│     │  │  └── run_consensus.py
│     │  └── SKILL.md
│     ├── frontend-design-anthropic
│     │  ├── metadata.json
│     │  └── SKILL.md
│     ├── frontend-design-openai
│     │  ├── metadata.json
│     │  └── SKILL.md
│     ├── i-adapt
│     │  └── SKILL.md
│     ├── i-animate
│     │  └── SKILL.md
│     ├── i-arrange
│     │  └── SKILL.md
│     ├── i-audit
│     │  └── SKILL.md
│     ├── i-bolder
│     │  └── SKILL.md
│     ├── i-clarify
│     │  └── SKILL.md
│     ├── i-colorize
│     │  └── SKILL.md
│     ├── i-critique
│     │  └── SKILL.md
│     ├── i-delight
│     │  └── SKILL.md
│     ├── i-distill
│     │  └── SKILL.md
│     ├── i-extract
│     │  └── SKILL.md
│     ├── i-frontend-design
│     │  └── SKILL.md
│     ├── i-harden
│     │  └── SKILL.md
│     ├── i-normalize
│     │  └── SKILL.md
│     ├── i-onboard
│     │  └── SKILL.md
│     ├── i-optimize
│     │  └── SKILL.md
│     ├── i-overdrive
│     │  └── SKILL.md
│     ├── i-polish
│     │  └── SKILL.md
│     ├── i-quieter
│     │  └── SKILL.md
│     ├── i-teach-impeccable
│     │  └── SKILL.md
│     ├── i-typeset
│     │  └── SKILL.md
│     ├── plan
│     │  └── SKILL.md
│     ├── prompt-subagent
│     │  └── SKILL.md
│     ├── react-best-practices
│     │  ├── AGENTS.md
│     │  ├── metadata.json
│     │  ├── README.md
│     │  └── SKILL.md
│     ├── reconcile
│     │  └── SKILL.md
│     ├── research-codebase
│     │  └── SKILL.md
│     ├── review-plan
│     │  └── SKILL.md
│     ├── simplify-code
│     │  └── SKILL.md
│     ├── to-done
│     │  └── SKILL.md
│     ├── vercel
│     │  └── SKILL.md
│     └── web-a11y-guidelines
│        └── SKILL.md
├── .claude
│  ├── hooks
│  │  ├── block-gh-command.sh
│  │  ├── block-until-reads.sh
│  │  ├── README.md
│  │  └── require-reads.sh
│  ├── settings.backup.json
│  └── settings.json
├── .githooks
│  ├── post-checkout
│  ├── post-merge
│  ├── pre-commit
│  ├── README.md
│  ├── sync-subdir.sh
│  ├── sync-upstream-suggestions.md
│  └── util.sh
├── .github
│  ├── commands
│  └── workflows
│     ├── claude.yml
│     ├── GEMINI_REMOTE_AUTH.md
│     ├── maintain-documentation.yml
│     ├── nightly-vercel-cleanup.yml
│     ├── test-gemini-wif.yml
│     ├── weekly-branch-pr-cleanup.yml
│     ├── weekly-supabase-cleanup.yml
│     └── WORKFLOW_DIAGRAM.md
├── .jbeval
│  └── datasets
├── .pi
│  ├── APPEND_SYSTEM.md
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
│  ├── hackernews_adapter.py
│  ├── hillel_wayne_adapter.py
│  ├── infoq_adapter.py
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
│  │  │  ├── CalendarDay.jsx
│  │  │  ├── DigestButton.jsx
│  │  │  ├── DigestOverlay.jsx
│  │  │  ├── Feed.jsx
│  │  │  ├── FoldableContainer.jsx
│  │  │  ├── NewsletterDay.jsx
│  │  │  ├── ReadStatsBadge.jsx
│  │  │  ├── ResultsDisplay.jsx
│  │  │  ├── ScrapeForm.jsx
│  │  │  ├── Selectable.jsx
│  │  │  ├── SelectionActionDock.jsx
│  │  │  ├── SelectionCounterPill.jsx
│  │  │  └── ToastContainer.jsx
│  │  ├── consensus
│  │  │  ├── consensus.css
│  │  │  └── ConsensusApp.jsx
│  │  ├── contexts
│  │  │  └── InteractionContext.jsx
│  │  ├── hooks
│  │  │  ├── useArticleState.js
│  │  │  ├── useDigest.js
│  │  │  ├── useLocalStorage.js
│  │  │  ├── useLongPress.js
│  │  │  ├── useOverscrollUp.js
│  │  │  ├── usePullToClose.js
│  │  │  ├── useScrollProgress.js
│  │  │  ├── useSummary.js
│  │  │  ├── useSupabaseStorage.js
│  │  │  └── useSwipeToRemove.js
│  │  ├── lib
│  │  │  ├── articleActionBus.js
│  │  │  ├── interactionConstants.js
│  │  │  ├── quakeConsole.js
│  │  │  ├── scraper.js
│  │  │  ├── stateTransitionLogger.js
│  │  │  ├── storageApi.js
│  │  │  ├── storageKeys.js
│  │  │  └── toastBus.js
│  │  ├── reducers
│  │  │  ├── articleLifecycleReducer.js
│  │  │  ├── gestureReducer.js
│  │  │  ├── interactionReducer.js
│  │  │  └── summaryDataReducer.js
│  │  ├── App.jsx
│  │  ├── index.css
│  │  └── main.jsx
│  ├── .gitignore
│  ├── biome.json
│  ├── CLIENT_ARCHITECTURE.md
│  ├── index.html
│  ├── package-lock.json
│  ├── package.json
│  ├── postcss.config.js
│  ├── UI_DESIGN.md
│  └── vite.config.js
├── ios
│  └── TLDRScraper.xcodeproj
│     └── project.xcworkspace
│        └── xcshareddata
│           └── swiftpm
│              └── configuration
├── scripts
│  ├── setup
│  │  ├── build_client.sh
│  │  ├── common.sh
│  │  ├── create_digests_table.sql
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
├── tests
│  ├── unit
│  │  ├── test_canonicalize_url.py
│  │  ├── test_should_rescrape.py
│  │  └── test_trendshift_adapter.py
│  ├── test_google_adk_smoke.py
│  ├── test_scrape_cache_server.py
│  └── test_some_server_functionalities.py
├── thoughts
│  ├── 25-12-21-failed-scrapes-are-retryable
│  │  └── discussion.md
│  ├── 26-04-03-selection-dock-state-machine
│  │  ├── plan.md
│  │  └── plan.review.md
│  ├── 26-04-04-workflow-machine
│  │  ├── discussion-raw.md
│  │  └── plan.md
│  ├── 26-04-07-context-menu-research
│  │  ├── plans
│  │  │  ├── plan-final.md
│  │  │  ├── plan-g.md
│  │  │  └── plan-x.md
│  │  ├── research
│  │  │  └── description.md
│  │  └── relevant-files.md
│  └── 26-04-08-client-code-dedup
│     └── locations
│        ├── data-persistence.md
│        ├── domain-hooks.md
│        ├── interaction-selection.md
│        └── overlays-gestures.md
├── .gitattributes
├── .gitignore
├── .vercelignore
├── AGENTS.md
├── ARCHITECTURE.md
├── BUGS.md
├── CLAUDE.md
├── CODEX.md
├── consensus.py
├── GEMINI.md
├── GOTCHAS.md
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── serve.py
├── setup-hooks.sh
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
