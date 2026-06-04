---
last_updated: 2026-06-04 09:49
---

.
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
│  │  │  ├── visual-effects
│  │  │  │  ├── LiquidGlassDefs.jsx
│  │  │  │  ├── LiquidGlassSurface.jsx
│  │  │  │  └── LiquidGlassTouchLight.jsx
│  │  │  ├── AddUrlButton.jsx
│  │  │  ├── ArticleCard.jsx
│  │  │  ├── ArticleList.jsx
│  │  │  ├── BaseOverlay.jsx
│  │  │  ├── CalendarDay.jsx
│  │  │  ├── DebugPanel.jsx
│  │  │  ├── DigestOverlay.jsx
│  │  │  ├── ElaborationPreview.jsx
│  │  │  ├── Feed.jsx
│  │  │  ├── FoldableContainer.jsx
│  │  │  ├── LinkSummarizePreview.jsx
│  │  │  ├── NewsletterDay.jsx
│  │  │  ├── OverlayContextMenu.jsx
│  │  │  ├── OverlayLink.jsx
│  │  │  ├── OverlayLinkMenuContext.js
│  │  │  ├── OverlayMarkdown.jsx
│  │  │  ├── PodcastPlayer.jsx
│  │  │  ├── ReadStatsBadge.jsx
│  │  │  ├── ScrapeForm.jsx
│  │  │  ├── Selectable.jsx
│  │  │  ├── SelectionActionDock.jsx
│  │  │  ├── ToastContainer.jsx
│  │  │  ├── YamlView.jsx
│  │  │  └── ZenModeOverlay.jsx
│  │  ├── hooks
│  │  │  ├── useArticleState.js
│  │  │  ├── useDigest.js
│  │  │  ├── useElaboration.js
│  │  │  ├── useFeedLoader.js
│  │  │  ├── useLinkSummarize.js
│  │  │  ├── useLongPress.js
│  │  │  ├── useOverlayContextMenu.js
│  │  │  ├── useOverscrollUp.js
│  │  │  ├── usePullToClose.js
│  │  │  ├── useScrollProgress.js
│  │  │  ├── useSummary.js
│  │  │  ├── useSwipeToRemove.js
│  │  │  └── useTrackedState.js
│  │  ├── lib
│  │  │  ├── apiError.js
│  │  │  ├── dailyPayloadMutations.js
│  │  │  ├── faviconUrl.js
│  │  │  ├── floatingPositionReference.js
│  │  │  ├── interactionConstants.js
│  │  │  ├── markdownUtils.js
│  │  │  ├── quakeConsole.js
│  │  │  ├── requestUtils.js
│  │  │  ├── scraper.js
│  │  │  ├── stateTransitionLogger.js
│  │  │  ├── storageApi.js
│  │  │  ├── toastBus.js
│  │  │  ├── topLevelDomains.js
│  │  │  ├── urlDetection.js
│  │  │  ├── yamlLog.js
│  │  │  ├── yamlTokens.js
│  │  │  └── zenLock.js
│  │  ├── reducers
│  │  │  ├── articleLifecycleReducer.js
│  │  │  ├── gestureReducer.js
│  │  │  ├── interactionReducer.js
│  │  │  ├── mobileSelectionMenuReducer.js
│  │  │  └── summaryDataReducer.js
│  │  ├── store
│  │  │  ├── articleStore.js
│  │  │  └── articleStore.test.js
│  │  ├── App.jsx
│  │  ├── index.css
│  │  └── main.jsx
│  ├── .gitignore
│  ├── .nvmrc
│  ├── biome.json
│  ├── index.html
│  ├── main-screen.png
│  ├── package-lock.json
│  ├── package.json
│  ├── postcss.config.js
│  ├── summary-overlay.png
│  ├── UI_DESIGN.md
│  └── vite.config.js
├── experiments
│  └── liquid-glass
│     ├── 06-04-ios-weak-path-blur-gradient-specular
│     │  ├── index.html
│     │  ├── script.js
│     │  └── styles.css
│     ├── index.html
│     ├── script.js
│     └── styles.css
├── scripts
│  └── ops
│     ├── clean_vercel_deployments.py
│     ├── generate_project_tree.py
│     ├── markdown_frontmatter.py
│     ├── structural-maintenance.sh
│     ├── synced_external_subdirs.txt
│     └── update_frontmatter.py
├── .gitattributes
├── .gitignore
├── .gitmodules
├── .ignore
├── .vercelignore
├── AGENTS.md
├── CLAUDE.md
├── gemini_tts_adapter.py
├── GOTCHAS.md
├── Justfile
├── liquid-glass-0.png
├── liquid-glass-1.1.png
├── liquid-glass-1.2.png
├── liquid-glass-1.3.png
├── liquid-glass-1.4.png
├── liquid-glass-1.5.png
├── liquid-glass-1.6.png
├── liquid-glass-1.7.png
├── newsletter_config.py
├── newsletter_scraper.py
├── podcast_service.py
├── PROJECT_STRUCTURE.md
├── pyproject.toml
├── README.md
├── requirements.txt
├── serve.py
├── sessions.yaml
├── setup.sh
├── source_routes.py
├── speakers_config.json
├── storage_service.py
├── summarizer.py
├── supabase_client.py
├── tldr_app.py
├── tldr_service.py
├── util.py
├── uv.lock
└── vercel.json