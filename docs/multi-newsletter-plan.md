# Multi-Newsletter Refactoring Plan

**Status:** Final, Ready for Implementation
**Last Updated:** 2025-10-25
**Reviewers:** Claude (draft), AI Reviewer (critical review)

## Executive Summary

This document provides a comprehensive plan to refactor TLDRScraper from a TLDR-specific application to a newsletter-agnostic system that can integrate multiple sources without code changes.

**Critical Changes Required:**
- 12 hardcoded TLDR assumptions identified across backend and frontend
- 5 major omissions from initial draft (identity collisions, branding leaks, test maintenance)
- Implementation via Adapter Pattern with declarative configuration
- 5 phases of refactoring with minimal breaking changes

**Success Metric:** Adding a new newsletter source requires only (1) config object + (1) adapter class, with zero changes to existing scraper/merger/frontend code.

---

## 🔍 TLDR-SPECIFIC ASSUMPTIONS AUDIT

### **Backend (Python) - 11 Critical Points**

| # | File | Lines | What's Hardcoded | Impact | Fix Priority |
|---|------|-------|------------------|--------|--------------|
| 1 | `newsletter_scraper.py` | 575 | `["tech", "ai"]` - Newsletter types array | **CRITICAL** | Phase 2 |
| 2 | `newsletter_scraper.py` | 464 | `f"https://tldr.tech/{newsletter_type}/{date}"` | **CRITICAL** | Phase 1 |
| 3 | `newsletter_scraper.py` | 341-345 | Category mapping: `"tech"→"TLDR Tech"`, `"ai"→"TLDR AI"` | **CRITICAL** | Phase 1 |
| 4 | `newsletter_scraper.py` | 252 | `["TLDR AI", "TLDR Tech"]` - Preferred ordering | **HIGH** | Phase 2 |
| 5 | `newsletter_scraper.py` | 328 | `(N minute read)\|(GitHub Repo)` regex pattern | **CRITICAL** | Phase 1 |
| 6 | `newsletter_scraper.py` | 372-385 | Emoji extraction from symbol-only lines | **MEDIUM** | Phase 1 |
| 7 | `newsletter_scraper.py` | 209-213 | `"# TLDR Newsletter Articles..."` markdown header | **HIGH** | Phase 2 |
| 8 | `newsletter_scraper.py` | 462-471 | `"TLDR-Newsletter/1.0"` User-Agent in fetcher | **HIGH** | Phase 1 |
| 9 | `summarizer.py` | 88, 160, 285 | `"TLDR-Newsletter/1.0"` User-Agent (3 instances) | **MEDIUM** | Phase 1 |
| 10 | `util.py` | 22 | `TLDR_SCRAPER_*` env var prefix | **LOW** | Phase 5 |

### **Frontend (JavaScript) - 5 Critical Points**

| # | File | Lines | What's Hardcoded | Impact | Fix Priority |
|---|------|-------|------------------|--------|--------------|
| 11 | `dom-builder.js` | 179-199 | Issue identity key: `${date}__${category}` (missing `source_id`) | **CRITICAL** | Phase 3 |
| 12 | `dom-builder.js` | 304-305 | `/TLDR\s*AI\|TLDR\s*Tech/i` regex for reordering | **MEDIUM** | Phase 4 |
| 13 | `storage.js` | 24-26 | `tldr:scrapes:${date}` localStorage key prefix | **HIGH** | Phase 3 |
| 14 | `templates/index.html` | 6, 1090 | "TLDR Newsletter TLDR'er" branding | **LOW** | Phase 4 |
| 15 | `tests/*.spec.ts` | Multiple | Button labels, category expectations | **HIGH** | Phase 5 |

---

## 🎯 PROPOSED REFACTORING ARCHITECTURE

### **Core Concept: Newsletter Adapter Pattern**

```
┌─────────────────────────────────────────────────────────────┐
│                    NEWSLETTER CONFIG                        │
│  (Declarative Python dataclasses per newsletter source)    │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  TLDR Adapter   │     │ Future Adapters │
│  - tech         │     │  - Hacker News  │
│  - ai           │     │  - Morning Brew │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │  ADAPTER INTERFACE    │
         │  - fetch(date, type)  │
         │  - parse(html)        │
         │  - normalize()        │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │ NORMALIZED RESPONSE   │
         │  {                    │
         │    source_id: str     │
         │    articles: [...]    │
         │    issues: [...]      │
         │  }                    │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   MERGER SERVICE      │
         │  (Source-agnostic)    │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   CLIENT STORAGE      │
         │  newsletters:scrapes: │
         │    ${date}            │
         │  {                    │
         │    articles: [        │
         │      {sourceId, ...}  │
         │    ]                  │
         │  }                    │
         └───────────┬───────────┘
                     ▼
                  CLIENT
```

---

## 📋 DETAILED REFACTORING PLAN

### **Phase 1: Create Adapter Abstraction Layer**

#### **Step 1.1: Define Newsletter Config Schema**
**File:** `newsletter_config.py` (NEW)

```python
from dataclasses import dataclass

@dataclass
class NewsletterSourceConfig:
    source_id: str              # "tldr_tech", "tldr_ai", "hackernews"
    display_name: str           # "TLDR Tech", "Hacker News Daily"
    base_url: str               # "https://tldr.tech"
    url_pattern: str            # "{base_url}/{type}/{date}"
    types: list[str]            # ["tech", "ai"] or ["daily"]
    user_agent: str             # "Newsletter-Aggregator/1.0" (neutral default)

    # Parsing rules
    article_pattern: str        # Regex to identify articles
    section_emoji_enabled: bool # Does this source use emoji sections?

    # Display preferences
    category_display_names: dict[str, str]  # {"tech": "TLDR Tech"}
    sort_order: int             # For multi-source ordering
    color_theme: str | None     # UI theming (future)

# Hardcoded configs
NEWSLETTER_CONFIGS = {
    "tldr_tech": NewsletterSourceConfig(
        source_id="tldr_tech",
        display_name="TLDR Tech",
        base_url="https://tldr.tech",
        url_pattern="{base_url}/tech/{date}",
        types=["tech"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern=r"\((\d+) minute read\)|\(GitHub Repo\)",
        section_emoji_enabled=True,
        category_display_names={"tech": "TLDR Tech"},
        sort_order=2
    ),
    "tldr_ai": NewsletterSourceConfig(
        source_id="tldr_ai",
        display_name="TLDR AI",
        base_url="https://tldr.tech",
        url_pattern="{base_url}/ai/{date}",
        types=["ai"],
        user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
        article_pattern=r"\((\d+) minute read\)|\(GitHub Repo\)",
        section_emoji_enabled=True,
        category_display_names={"ai": "TLDR AI"},
        sort_order=1  # AI comes before Tech
    )
}
```

**Critical Fix from Review:** User-Agent is now configurable per-source, defaulting to neutral `Newsletter-Aggregator/1.0`.

#### **Step 1.2: Create Abstract Adapter Interface**
**File:** `newsletter_adapter.py` (NEW)

```python
from abc import ABC, abstractmethod
from newsletter_config import NewsletterSourceConfig

class NewsletterAdapter(ABC):
    def __init__(self, config: NewsletterSourceConfig):
        self.config = config

    @abstractmethod
    def fetch_issue(self, date: str, type: str) -> str:
        """Fetch raw HTML for a specific issue"""
        pass

    @abstractmethod
    def parse_articles(self, markdown: str, date: str, type: str) -> list[dict]:
        """Parse articles from markdown"""
        pass

    @abstractmethod
    def extract_issue_metadata(self, markdown: str) -> dict:
        """Extract title, subtitle, sections"""
        pass

    def scrape_date(self, date: str) -> dict:
        """Template method - orchestrates fetch + parse + normalize"""
        articles = []
        issues = []

        for newsletter_type in self.config.types:
            # Fetch
            html = self.fetch_issue(date, newsletter_type)
            markdown = self._html_to_markdown(html)

            # Parse
            articles.extend(self.parse_articles(markdown, date, newsletter_type))
            issue_meta = self.extract_issue_metadata(markdown)
            issues.append(issue_meta)

        return self._normalize_response(articles, issues)

    def _normalize_response(self, articles, issues):
        """Convert to standardized format with source_id"""
        return {
            "source_id": self.config.source_id,
            "articles": [
                {**article, "source_id": self.config.source_id}
                for article in articles
            ],
            "issues": [
                {**issue, "source_id": self.config.source_id}
                for issue in issues
            ]
        }
```

**Critical Fix from Review:** Ensure every article and issue includes `source_id` to prevent identity collisions.

#### **Step 1.3: Implement TLDR Adapter**
**File:** `tldr_adapter.py` (NEW)

Move existing logic from `newsletter_scraper.py` into this adapter:
- `fetch_issue()` → Uses current `_fetch_newsletter()` logic, but with `config.user_agent`
- `parse_articles()` → Uses current `_parse_articles_from_markdown()` logic
- `extract_issue_metadata()` → Extracts title/subtitle/sections

---

### **Phase 2: Refactor Scraper to Use Adapters**

#### **Step 2.1: Update `newsletter_scraper.py`**

**BEFORE:**
```python
def scrape_date_range(start_date, end_date):
    for date in date_range:
        for newsletter_type in ["tech", "ai"]:  # HARDCODED
            _fetch_newsletter(date, newsletter_type)
```

**AFTER:**
```python
from newsletter_config import NEWSLETTER_CONFIGS
from tldr_adapter import TLDRAdapter

def scrape_date_range(start_date, end_date, source_ids=None):
    """
    source_ids: Optional list of sources to scrape.
                If None, scrapes all configured sources.
    """
    if source_ids is None:
        source_ids = NEWSLETTER_CONFIGS.keys()

    all_results = []

    for source_id in source_ids:
        config = NEWSLETTER_CONFIGS[source_id]
        adapter = _get_adapter_for_source(config)

        for date in date_range:
            result = adapter.scrape_date(date)
            all_results.append(result)

    return _merge_responses(all_results)  # Source-agnostic merge

def _get_adapter_for_source(config):
    """Factory pattern - returns appropriate adapter"""
    if config.source_id.startswith("tldr_"):
        return TLDRAdapter(config)
    # elif config.source_id == "hackernews":
    #     return HackerNewsAdapter(config)
    else:
        raise ValueError(f"No adapter for {config.source_id}")
```

#### **Step 2.2: Create Source-Agnostic Merger**
**File:** `newsletter_merger.py` (NEW)

```python
from newsletter_config import NEWSLETTER_CONFIGS

def merge_responses(responses: list[dict]) -> dict:
    """
    Merges multiple source responses into single normalized response.
    Completely agnostic to source types - just combines lists.
    """
    all_articles = []
    all_issues = []

    for response in responses:
        all_articles.extend(response["articles"])
        all_issues.extend(response["issues"])

    # Sort by source sort_order (from config)
    all_issues.sort(key=lambda i: NEWSLETTER_CONFIGS[i["source_id"]].sort_order)

    return {
        "success": True,
        "articles": all_articles,
        "issues": all_issues,
        "output": _build_markdown_output(all_articles, all_issues),
        "stats": _calculate_stats(all_articles, all_issues)
    }

def _build_markdown_output(articles, issues):
    """Generate neutral markdown output"""
    # Extract date range from articles
    dates = sorted(set(a["date"] for a in articles))
    start, end = dates[0], dates[-1]

    # Neutral header (NO TLDR BRANDING)
    output = f"# Newsletter Articles ({start} to {end})\n\n"

    # List included sources
    sources = sorted(set(i["source_id"] for i in issues))
    source_names = [NEWSLETTER_CONFIGS[s].display_name for s in sources]
    output += f"**Sources:** {', '.join(source_names)}\n\n"

    # ... rest of markdown generation (source-agnostic)

    return output
```

**Critical Fix from Review:** Markdown header is now neutral and lists sources dynamically.

---

### **Phase 3: Update Data Models**

#### **Step 3.1: Generalize Article Schema**

**BEFORE:**
```python
{
    "category": "TLDR Tech",  # Hardcoded values
    "newsletter_type": "tech",
    ...
}
```

**AFTER:**
```python
{
    "source_id": "tldr_tech",         # Generic identifier (REQUIRED)
    "category": "TLDR Tech",          # Display name (from config)
    "newsletter_type": "tech",        # Subtype within source
    "source_metadata": {              # Source-specific extras
        "section_emoji": "🚀",
        "read_time_minutes": 3
    },
    ...
}
```

#### **Step 3.2: Update Frontend Storage Schema**
**File:** `storage.js`

**BEFORE:**
```javascript
// Key: tldr:scrapes:${date}
newsletterType: "tech" | "ai"
category: "TLDR Tech" | "TLDR AI"
```

**AFTER:**
```javascript
// Key: newsletters:scrapes:${date} (debranded prefix)
sourceId: string  // "tldr_tech", "hackernews_daily" (REQUIRED)
category: string  // Display name (now dynamic)
newsletterType: string | null  // Subtype within source (optional)

// Storage helper
function getStorageKey(date) {
    return `newsletters:scrapes:${date}`; // Changed from "tldr:scrapes:"
}
```

**Decision from Review Discussion:** We use Option A - debrand the prefix but keep the one-key-per-date architecture. This maintains the "agnostic merger" concept where the client doesn't need to know which sources exist.

**Migration Note:** Existing `tldr:scrapes:*` keys will remain in localStorage but won't be read by the new code. Users will need to re-scrape (acceptable for this refactor).

---

### **Phase 4: Frontend Refactoring**

#### **Step 4.1: Fix Issue Identity Collisions**
**File:** `dom-builder.js`

**CRITICAL FIX from Review:** The current key `${date}__${category}` will cause collisions when multiple sources share category names.

**BEFORE:**
```javascript
// Line 179-190
payload.issues.forEach(issue => {
    const key = `${payload.date}__${issue.category || ''}`;
    issueMetadataMap.set(key, { ... });
});

// Line 195-199
function getIssueKey(dateStr, category) {
    return `${dateStr}-${category}`.toLowerCase();
}
```

**AFTER:**
```javascript
// Triple-key to prevent collisions
payload.issues.forEach(issue => {
    const key = `${payload.date}__${issue.sourceId}__${issue.category || ''}`;
    issueMetadataMap.set(key, {
        date: payload.date,
        sourceId: issue.sourceId,  // NEW
        category: issue.category || '',
        // ... rest
    });
});

function getIssueKey(dateStr, sourceId, category) {
    return `${dateStr}-${sourceId}-${category}`.toLowerCase();
}

// Update all callers to pass sourceId
// Update DOM attributes to use triple-key:
newHeader.setAttribute('data-issue-key', issueKey);
newHeader.setAttribute('data-issue-toggle', issueKey);
```

**Changes required:**
- `buildPayloadIndices()` - Use triple-key in issueMetadataMap
- `getIssueKey()` - Accept sourceId parameter
- `transformWhiteySurface()` - Pass sourceId when building keys
- `sanitizeIssue()` in `storage.js` - Preserve sourceId field
- `buildDailyPayloadsFromScrape()` - Carry sourceId into payloads

#### **Step 4.2: Remove Hardcoded Category Checks**
**File:** `dom-builder.js`

**BEFORE (Line 304-305):**
```javascript
if (!aiHeading && /TLDR\s*AI/i.test(text)) aiHeading = node;
if (!techHeading && /TLDR\s*Tech/i.test(text)) techHeading = node;
// ... manual reordering logic
```

**AFTER:**
```javascript
// Remove this entire block - backend already sorted by config.sort_order
// Just render issues in the order received from API
```

#### **Step 4.3: Update UI Labels**
**File:** `templates/index.html`

**BEFORE:**
```html
<title>TLDR Newsletter TLDR'er</title>
<h1>TLDR Newsletter TLDR'er</h1>
```

**AFTER:**
```html
<title>Newsletter Aggregator</title>
<h1>Newsletter Aggregator</h1>
<!-- Or make it configurable via backend config -->
```

#### **Step 4.4: Make Rendering Source-Agnostic**

General principles:
- Remove all assumptions about specific category names
- Render based on `sourceId` + `category` from backend
- Use `source_metadata` for conditional rendering (e.g., show emoji only if present)

---

### **Phase 5: API Contract & Testing**

#### **Step 5.1: Add Source Selection to API**

**New endpoint signature:**
```python
POST /api/scrape
{
    "start_date": "2025-10-20",
    "end_date": "2025-10-25",
    "sources": ["tldr_tech", "tldr_ai"]  # Optional, defaults to all
}
```

**Response format (already flexible, just ensure source_id is present):**
```json
{
    "success": true,
    "articles": [
        {
            "source_id": "tldr_tech",
            "category": "TLDR Tech",
            "url": "...",
            ...
        }
    ],
    "issues": [
        {
            "source_id": "tldr_ai",
            "category": "TLDR AI",
            ...
        }
    ]
}
```

#### **Step 5.2: Update Tests**

**Critical Fix from Review:** Tests will break when UI labels and DOM structure change.

**Test Files to Update:**
- `tests/remove-order.spec.ts` - Line 135-139
- `tests/playwright/localStorage.spec.ts` - Line 137-139

**Changes Required:**
1. **Add data-testid attributes:**
   ```html
   <button data-testid="scrape-btn" ...>Scrape Newsletters</button>
   ```

2. **Update selectors in tests:**
   ```typescript
   // BEFORE
   await page.getByRole('button', { name: 'Scrape TLDR Newsletters' }).click();

   // AFTER
   await page.getByTestId('scrape-btn').click();
   ```

3. **Update mocks to include source_id:**
   ```typescript
   const mockArticle = {
       url: "...",
       source_id: "tldr_tech",  // NEW
       category: "TLDR Tech",
       // ...
   };
   ```

4. **Update issue key expectations:**
   ```typescript
   // Use triple-key format in assertions
   expect(issueKey).toBe("2025-10-25-tldr_tech-TLDR Tech");
   ```

---

## 🎬 IMPLEMENTATION SEQUENCE

### **Minimal Breaking Changes Approach:**

1. **Create new files** (no changes to existing code yet):
   - `newsletter_config.py` - Config schema + TLDR configs (with user_agent field)
   - `newsletter_adapter.py` - Abstract base class (ensures source_id in responses)
   - `tldr_adapter.py` - TLDR-specific implementation
   - `newsletter_merger.py` - Source-agnostic response merger (neutral markdown header)

2. **Refactor `newsletter_scraper.py`**:
   - Extract TLDR logic → `tldr_adapter.py`
   - Replace hardcoded loops with adapter factory pattern
   - Ensure all responses include `source_id` on articles and issues
   - Keep existing function signatures (backwards compatible)

3. **Update data models**:
   - Backend: Add `source_id` field to every article and issue
   - Frontend: Update `storage.js` to:
     - Change key prefix: `newsletters:scrapes:${date}` (debranded)
     - Preserve `sourceId` in `sanitizeIssue()`
   - Keep existing `category` + `newsletterType` for backwards compat

4. **Frontend updates**:
   - `dom-builder.js`:
     - Fix issue identity collisions with triple-key: `${date}__${sourceId}__${category}`
     - Update `buildPayloadIndices()`, `getIssueKey()`, all DOM attributes
     - Remove TLDR-specific reorder logic (lines 302-306)
   - `storage.js`: Update key helper to use neutral prefix
   - `templates/index.html`: Debrand titles

5. **Test updates**:
   - Add `data-testid` attributes to critical UI elements
   - Update test selectors to use testids instead of labels
   - Add `source_id` to all mock data
   - Update issue key expectations to triple-key format

6. **Test with existing TLDR sources** - ensure feature parity

7. **Add a new source** (proof of concept):
   - Create `hackernews_adapter.py` or similar
   - Add config to `NEWSLETTER_CONFIGS`
   - Verify system works without code changes to scraper/merger/frontend

---

## 🧪 SUCCESS CRITERIA

The refactoring is complete when:

✅ **No hardcoded newsletter names** in business logic

✅ **Adding a new source** requires:
   - 1 new config object in `newsletter_config.py`
   - 1 new adapter class implementing `NewsletterAdapter`
   - 0 changes to existing scraper/merger/frontend code

✅ **Backend is source-agnostic**:
   - Scraper loops over `NEWSLETTER_CONFIGS` not `["tech", "ai"]`
   - Merger doesn't know what sources are being merged
   - All responses include `source_id` on every article/issue
   - API response format works for any source

✅ **Frontend is "stupid"**:
   - Renders whatever `sourceId` + `category` it receives
   - No conditional logic for specific newsletter names
   - Storage schema handles arbitrary sources
   - Issue identity uses triple-key (no collisions)

✅ **Backwards compatible**:
   - UI still works with TLDR newsletters
   - Tests pass (after testid refactor)

✅ **No branding leaks**:
   - User-Agent is neutral and configurable
   - Markdown output header is neutral
   - localStorage keys use neutral prefix
   - UI titles are neutral

✅ **Tests remain green**:
   - All existing tests pass after testid migration
   - Test fixtures include `source_id`
   - Issue key assertions updated to triple-key format

---

## 📝 REVIEW NOTES

This plan incorporates critical feedback from AI review (2025-10-25):

**Major Fixes Integrated:**
1. ✅ Issue identity collision prevention (triple-key system)
2. ✅ TLDR-branded markdown header neutralization
3. ✅ User-Agent branding in newsletter fetcher (added to config)
4. ✅ Test maintenance strategy (testid pattern)
5. ✅ LocalStorage key debranding (Option A: neutral prefix, keep architecture)

**False Positives Corrected:**
- Storage type constraints were overstated (no actual enforcement)
- dom-builder TLDR assumptions limited to single reorder block

**Architectural Decision:**
- **LocalStorage Keys:** Use `newsletters:scrapes:${date}` (debranded prefix)
- **Rationale:** Maintains one-key-per-date architecture, keeps client agnostic, simpler hydration
- **Trade-off:** Existing cached data will be orphaned (acceptable for this refactor)
