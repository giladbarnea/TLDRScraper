---
last_updated: 2026-02-20 07:52
---
# Domain Map: Multi-Article Digest Feature

## 1. Client: Article Selection Mechanism

- `/home/user/TLDRScraper/client/src/components/Selectable.jsx`
- `/home/user/TLDRScraper/client/src/components/ArticleCard.jsx`
- `/home/user/TLDRScraper/client/src/contexts/InteractionContext.jsx`
- `/home/user/TLDRScraper/client/src/reducers/interactionReducer.js`
- `/home/user/TLDRScraper/client/src/reducers/gestureReducer.js`
- `/home/user/TLDRScraper/client/src/hooks/useLongPress.js`
- `/home/user/TLDRScraper/client/src/lib/interactionConstants.js`

## 2. Client: Selection Counter Pill / Selection UI

- `/home/user/TLDRScraper/client/src/components/SelectionCounterPill.jsx`
- `/home/user/TLDRScraper/client/src/contexts/InteractionContext.jsx`
- `/home/user/TLDRScraper/client/src/reducers/interactionReducer.js`

## 3. Client: ZenOverlay / ZenMode System

- `/home/user/TLDRScraper/client/src/components/ArticleCard.jsx` (contains `ZenModeOverlay` component)
- `/home/user/TLDRScraper/client/src/hooks/useOverscrollUp.js`
- `/home/user/TLDRScraper/client/src/hooks/usePullToClose.js`
- `/home/user/TLDRScraper/client/src/hooks/useScrollProgress.js`

## 4. Client: Summary/TLDR Flow

- `/home/user/TLDRScraper/client/src/components/ArticleCard.jsx`
- `/home/user/TLDRScraper/client/src/hooks/useSummary.js`
- `/home/user/TLDRScraper/client/src/reducers/summaryDataReducer.js`

## 5. Client: StorageApi / Hooks for Supabase Persistence

- `/home/user/TLDRScraper/client/src/lib/storageApi.js`
- `/home/user/TLDRScraper/client/src/lib/storageKeys.js`
- `/home/user/TLDRScraper/client/src/hooks/useSupabaseStorage.js`
- `/home/user/TLDRScraper/client/src/hooks/useArticleState.js`
- `/home/user/TLDRScraper/client/src/reducers/articleLifecycleReducer.js`

## 6. Backend: Summarizer Module (Gemini Integration)

- `/home/user/TLDRScraper/summarizer.py`
- `/home/user/TLDRScraper/tldr_service.py`

## 7. Backend: serve.py Routes

- `/home/user/TLDRScraper/serve.py`

## 8. Backend: tldr_app.py / tldr_service.py (App Logic / Service Layer)

- `/home/user/TLDRScraper/tldr_app.py`
- `/home/user/TLDRScraper/tldr_service.py`

## 9. Backend: storage_service.py (Supabase Persistence)

- `/home/user/TLDRScraper/storage_service.py`

## 10. Backend: supabase_client.py (DB Client)

- `/home/user/TLDRScraper/supabase_client.py`

## 11. Existing Batch / Multi-Article Processing Patterns

- `/home/user/TLDRScraper/newsletter_merger.py`
- `/home/user/TLDRScraper/adapters/newsletter_adapter.py`
- `/home/user/TLDRScraper/adapters/deepmind_adapter.py`

## Additional Related Files

### Client State Management
- `/home/user/TLDRScraper/client/src/lib/stateTransitionLogger.js`
- `/home/user/TLDRScraper/client/src/hooks/useLocalStorage.js`

### Client UI Components
- `/home/user/TLDRScraper/client/src/App.jsx`
- `/home/user/TLDRScraper/client/src/components/ArticleList.jsx`
- `/home/user/TLDRScraper/client/src/components/NewsletterDay.jsx`
- `/home/user/TLDRScraper/client/src/components/FoldableContainer.jsx`

### Client API Integration
- `/home/user/TLDRScraper/client/src/lib/scraper.js`

### Backend Utilities
- `/home/user/TLDRScraper/util.py`
- `/home/user/TLDRScraper/newsletter_config.py`
