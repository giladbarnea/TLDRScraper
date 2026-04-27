---
last_updated: 2026-04-27 21:22
---

.
├── .agents
│  └── skills
│     ├── architecture-create
│     │  └── SKILL.md
│     ├── architecture-sync-since-last-updated
│     ├── catchup
│     │  └── SKILL.md
│     ├── consensus
│     │  ├── scripts
│     │  │  └── run_consensus.py
│     │  └── SKILL.md
│     ├── impeccable-design
│     │  ├── references
│     │  └── SKILL.md
│     ├── peer-review
│     │  ├── references
│     │  │  ├── direct-peer-review-instructions.md
│     │  │  └── self-peer-review.md
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
│     ├── simplify-code
│     │  └── SKILL.md
│     ├── supabase-postgres-best-practices
│     ├── terse-output
│     │  ├── metadata.yaml
│     │  └── SKILL.md
│     ├── to-done
│     │  └── SKILL.md
│     ├── vercel
│     │  └── SKILL.md
│     └── web-a11y-guidelines
│        └── SKILL.md
├── .githooks
│  ├── post-merge
│  ├── pre-commit
│  ├── README.md
│  └── sync-upstream-suggestions.md
├── .github
│  └── workflows
│     ├── infra-cleanup.yml
│     ├── secret-scan.yml
│     ├── update-frontmatter.yml
│     ├── weekly-branch-pr-cleanup.yml
│     └── WORKFLOW_DIAGRAM.md
├── adapters
│  ├── __init__.py
│  ├── aiwithmike_adapter.py
│  ├── anthropic_adapter.py
│  ├── anthropic_news_adapter.py
│  ├── claude_blog_adapter.py
│  ├── danluu_adapter.py
│  ├── deepmind_adapter.py
│  ├── google_research_adapter.py
│  ├── hackernews_adapter.py
│  ├── hillel_wayne_adapter.py
│  ├── jessitron_adapter.py
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
│  │  │  ├── ElaborationPreview.jsx
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
│  │  ├── groupCart
│  │  │  └── GroupCartApp.jsx
│  │  ├── hooks
│  │  │  ├── useArticleState.js
│  │  │  ├── useDigest.js
│  │  │  ├── useElaboration.js
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
│  │  │  ├── mobileSelectionMenuReducer.js
│  │  │  └── summaryDataReducer.js
│  │  ├── App.jsx
│  │  ├── index.css
│  │  └── main.jsx
│  ├── .gitignore
│  ├── .nvmrc
│  ├── ARCHITECTURE.md
│  ├── biome.json
│  ├── index.html
│  ├── main-screen.png
│  ├── package-lock.json
│  ├── package.json
│  ├── postcss.config.js
│  ├── STATE_MACHINES.md
│  ├── summary-overlay.png
│  ├── UI_DESIGN.md
│  └── vite.config.js
├── db
│  ├── create_digests_table.sql
│  └── create_shopping_cart_entries_table.sql
├── hidden_apps
├── scripts
│  ├── dev
│  │  ├── auto-pr-merge.sh
│  │  ├── install-codex-cli.sh
│  │  ├── run-agent-via-litellm.sh
│  │  ├── run-agent.sh
│  │  └── run-codex.sh
│  └── ops
│     ├── clean_vercel_deployments.py
│     ├── ensure_submodules.sh
│     ├── generate_project_tree.py
│     ├── markdown_frontmatter.py
│     ├── structural-maintenance.sh
│     ├── synced_external_subdirs.txt
│     └── update_frontmatter.py
├── vendor
│  └── consensus
│     ├── consensus
│     │  ├── __init__.py
│     │  ├── core.py
│     │  └── web.py
│     ├── web
│     │  ├── src
│     │  │  ├── consensus.css
│     │  │  ├── ConsensusApp.jsx
│     │  │  └── main.jsx
│     │  ├── index.html
│     │  ├── package-lock.json
│     │  ├── package.json
│     │  └── vite.config.js
│     ├── .gitignore
│     ├── pyproject.toml
│     ├── README.md
│     ├── serve.py
│     └── uv.lock
├── .gitattributes
├── .gitignore
├── .gitmodules
├── .vercelignore
├── AGENTS.md
├── ARCHITECTURE.md
├── BUGS.md
├── CLAUDE.md
├── GOTCHAS.md
├── Justfile
├── litellm_config.yaml
├── newsletter_config.py
├── newsletter_merger.py
├── newsletter_scraper.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── serve.py
├── sessions.yaml
├── setup.sh
├── shopping_cart_service.py
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