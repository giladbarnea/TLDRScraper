## 🔍 TLDR-SPECIFIC ASSUMPTIONS AUDIT

Based on my exploration, here are **ALL** the places where TLDR is hardcoded or assumed:

### **Backend (Python) - 8 Critical Points**

| # | File | Lines | What's Hardcoded | Impact |
|---|------|-------|------------------|--------|
| 1 | `newsletter_scraper.py` | 575 | `["tech", "ai"]` - Newsletter types array | **HIGH** - Defines which newsletters exist |
| 2 | `newsletter_scraper.py` | 464 | `f"https://tldr.tech/{newsletter_type}/{date}"` | **HIGH** - URL construction pattern |
| 3 | `newsletter_scraper.py` | 341-345 | Category mapping: `"tech"→"TLDR Tech"`, `"ai"→"TLDR AI"` | **HIGH** - Display names |
| 4 | `newsletter_scraper.py` | 252 | `["TLDR AI", "TLDR Tech"]` - Preferred ordering | **MEDIUM** - Sort order |
| 5 | `newsletter_scraper.py` | 328 | `(N minute read)\|(GitHub Repo)` regex pattern | **HIGH** - Article detection logic |
| 6 | `newsletter_scraper.py` | 372-385 | Emoji extraction from symbol-only lines | **MEDIUM** - Section metadata parsing |
| 7 | `summarizer.py` | 88, 160, 470 | `"TLDR-Newsletter/1.0"` User-Agent | **LOW** - HTTP headers |
| 8 | `util.py` | 22 | `TLDR_SCRAPER_*` env var prefix | **LOW** - Config naming |

### **Frontend (JavaScript) - 4 Critical Points**

| # | File | Lines | What's Hardcoded | Impact |
|---|------|-------|------------------|--------|
| 9 | `dom-builder.js` | 304-305 | `/TLDR\s*AI\|TLDR\s*Tech/i` regex for reordering | **MEDIUM** - Category sorting |
| 10 | `dom-builder.js` | Throughout | Assumes categories are "TLDR Tech" / "TLDR AI" | **HIGH** - Rendering logic |
| 11 | `storage.js` | Schema | `newsletterType: "tech"\|"ai"` type constraint | **HIGH** - Data model |
| 12 | `templates/index.html` | 6, 1090 | "TLDR Newsletter TLDR'er" branding | **LOW** - UI text |

---

## 🎯 PROPOSED REFACTORING ARCHITECTURE

### **Core Concept: Newsletter Adapter Pattern**

```
┌─────────────────────────────────────────────────────────────┐
│                    NEWSLETTER CONFIG                        │
│  (Declarative JSON/Python configs per newsletter source)   │
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
                  CLIENT
```

---

## 📋 DETAILED REFACTORING PLAN

### **Phase 1: Create Adapter Abstraction Layer**

#### **Step 1.1: Define Newsletter Config Schema**
**File:** `newsletter_config.py` (NEW)

```python
@dataclass
class NewsletterSourceConfig:
    source_id: str              # "tldr_tech", "tldr_ai", "hackernews"
    display_name: str           # "TLDR Tech", "Hacker News Daily"
    base_url: str               # "https://tldr.tech"
    url_pattern: str            # "{base_url}/{type}/{date}"
    types: list[str]            # ["tech", "ai"] or ["daily"]

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
        article_pattern=r"\((\d+) minute read\)|\(GitHub Repo\)",
        section_emoji_enabled=True,
        category_display_names={"ai": "TLDR AI"},
        sort_order=1  # AI comes before Tech
    )
}
```

#### **Step 1.2: Create Abstract Adapter Interface**
**File:** `newsletter_adapter.py` (NEW)

```python
from abc import ABC, abstractmethod

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
        """Convert to standardized format"""
        return {
            "source_id": self.config.source_id,
            "articles": articles,
            "issues": issues
        }
```

#### **Step 1.3: Implement TLDR Adapter**
**File:** `tldr_adapter.py` (NEW)

Move existing logic from `newsletter_scraper.py` into this adapter:
- `fetch_issue()` → Uses current `_fetch_newsletter()` logic
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
```

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
    "source_id": "tldr_tech",         # Generic identifier
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
newsletterType: "tech" | "ai"
category: "TLDR Tech" | "TLDR AI"
```

**AFTER:**
```javascript
sourceId: string  // "tldr_tech", "hackernews_daily"
category: string  // Display name (now dynamic)
newsletterType: string | null  // Subtype within source
```

---

### **Phase 4: Frontend Refactoring**

#### **Step 4.1: Remove Hardcoded Category Checks**
**File:** `dom-builder.js`

**BEFORE (Line 304-305):**
```javascript
if (/TLDR\s*AI|TLDR\s*Tech/i.test(category)) {
    // Special TLDR ordering
}
```

**AFTER:**
```javascript
// Use sort_order from backend response instead
// Backend already sorted issues by config.sort_order
```

#### **Step 4.2: Make Rendering Source-Agnostic**
**File:** `dom-builder.js`

- Remove all assumptions about specific category names
- Render based on `source_id` + `category` from backend
- Use `source_metadata` for conditional rendering (e.g., show emoji if present)

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
<!-- Or make it configurable via backend -->
```

---

### **Phase 5: API Contract Updates**

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

**Response format (unchanged - already flexible):**
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

---

## 🎬 IMPLEMENTATION SEQUENCE

### **Minimal Breaking Changes Approach:**

1. **Create new files** (no changes to existing code yet):
   - `newsletter_config.py` - Config schema + TLDR configs
   - `newsletter_adapter.py` - Abstract base class
   - `tldr_adapter.py` - TLDR-specific implementation
   - `newsletter_merger.py` - Source-agnostic response merger

2. **Refactor `newsletter_scraper.py`**:
   - Extract TLDR logic → `tldr_adapter.py`
   - Replace hardcoded loops with adapter factory pattern
   - Keep existing function signatures (backwards compatible)

3. **Update data models**:
   - Add `source_id` field to articles/issues
   - Keep existing `category` + `newsletter_type` for backwards compat
   - Frontend can migrate gradually

4. **Frontend updates**:
   - Update storage schema to use `sourceId`
   - Remove hardcoded category regexes
   - Make rendering source-agnostic

5. **Test with existing TLDR sources** - ensure feature parity

6. **Add a new source** (proof of concept):
   - Create `hackernews_adapter.py` or similar
   - Add config to `NEWSLETTER_CONFIGS`
   - Verify system works without code changes

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
   - API response format works for any source

✅ **Frontend is "stupid"**:
   - Renders whatever `source_id` + `category` it receives
   - No conditional logic for specific newsletter names
   - Storage schema handles arbitrary sources

✅ **Backwards compatible**:
   - Existing cached data still loads
   - Default behavior (no sources param) scrapes all configured sources
   - UI still works with TLDR newsletters
