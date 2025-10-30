---
last-updated: 2025-10-27 19:32, a787105
---

# HackerNews Integration Research

**Date**: 2025-10-27
**Research Question**: Can HackerNews be integrated seamlessly into the current newsletter abstraction using the 'haxor' Python library?

## Summary

The current newsletter scraper uses an **adapter pattern with a template method** design. After analyzing both the haxor library and the codebase, **HackerNews CAN be integrated** but requires **minor modifications to the abstraction** to accommodate API-based sources that don't follow date-specific URL patterns.

**Key Finding**: The current abstraction assumes HTML scraping with date-based URLs. HackerNews uses a JSON API with live feeds (not date archives), requiring a flexible override mechanism in the template method.

## Haxor Library Analysis

### Module Structure
- **Package name**: `haxor` (pip install)
- **Python module**: `hackernews` (import)
- **Main class**: `HackerNews`

### Key Classes

#### HackerNews (API Client)
```python
from hackernews import HackerNews
hn = HackerNews()
```

Methods:
- `top_stories(limit=None)` - current top stories
- `new_stories(limit=None)` - newest stories
- `ask_stories(limit=None)` - Ask HN stories
- `show_stories(limit=None)` - Show HN stories
- `job_stories(limit=None)` - job postings
- `get_item(item_id)` - get specific item by ID
- `get_last(num=10)` - get last N items

#### Item (Story/Comment Object)
Attributes available:
- `item_id`: int - unique ID
- `item_type`: str - "story", "comment", "job", "poll", "pollopt"
- `by`: str - username
- `submission_time`: datetime - when submitted
- `time`: datetime - duplicate of submission_time
- `title`: str - story title
- `url`: str - URL of the story
- `score`: int - points/upvotes
- `text`: str - comment text or story text
- `descendants`: int - number of comments
- `kids`: list[int] - list of comment IDs
- `parent`: int - parent item ID
- `deleted`: bool
- `dead`: bool
- `raw`: str - raw JSON string

### Time Filtering Capabilities

**CRITICAL LIMITATION**: The HackerNews API does NOT provide built-in time range filtering.

- API provides: Latest stories by category (top, new, ask, show, job)
- No archive access: Cannot fetch stories from a specific past date
- Client-side filtering required: Must fetch latest stories and filter by `submission_time`

### Data Acquisition Pattern
```python
# Fetch latest stories
stories = hn.top_stories(limit=100)  # Returns List[Item]

# Stories have datetime objects for filtering
for story in stories:
    if story.submission_time.date() == target_date:
        # Process story
```

## Current Codebase Architecture

### Core Abstractions

#### 1. NewsletterAdapter (Abstract Base Class)
**File**: `newsletter_adapter.py:19`

Defines three abstract methods:
```python
@abstractmethod
def fetch_issue(self, date: str, newsletter_type: str) -> str | None:
    """Fetch raw HTML for a specific issue"""

@abstractmethod
def parse_articles(self, markdown: str, date: str, newsletter_type: str) -> list[dict]:
    """Parse articles from markdown content"""

@abstractmethod
def extract_issue_metadata(self, markdown: str, date: str, newsletter_type: str) -> dict | None:
    """Extract issue metadata"""
```

Template method (orchestrator):
```python
def scrape_date(self, date: str) -> dict:
    """Template method - orchestrates fetch + parse + normalize"""
    # 1. Fetch HTML for each newsletter type
    # 2. Convert HTML to markdown
    # 3. Parse articles and metadata
    # 4. Normalize response with source_id
```

**Key assumptions**:
- Date-based fetching (line 100: `fetch_issue(date, newsletter_type)`)
- HTML input → markdown conversion (line 105: `_html_to_markdown()`)
- Fixed workflow: fetch → convert → parse → normalize

#### 2. NewsletterSourceConfig (Configuration Schema)
**File**: `newsletter_config.py:11`

```python
@dataclass
class NewsletterSourceConfig:
    source_id: str           # "tldr_tech", "hackernews"
    display_name: str        # "TLDR Tech", "Hacker News"
    base_url: str           # API base or website base
    url_pattern: str        # URL template (may not apply to APIs)
    types: list[str]        # Subtypes: ["tech", "ai"] or ["top", "new", "ask"]
    user_agent: str
    article_pattern: str    # Regex for article identification
    section_emoji_enabled: bool
    category_display_names: dict[str, str]
    sort_order: int
```

#### 3. TLDRAdapter (Concrete Implementation)
**File**: `tldr_adapter.py:45`

- `fetch_issue()`: Uses `requests.get()` with date-based URL (line 66-88)
- `parse_articles()`: Regex parsing of markdown (line 99-230)
- `extract_issue_metadata()`: Extracts title, subtitle, sections (line 232-338)

#### 4. newsletter_scraper (Orchestration)
**File**: `newsletter_scraper.py:16`

Factory pattern:
```python
def _get_adapter_for_source(config):
    if config.source_id.startswith("tldr_"):
        return TLDRAdapter(config)
    # elif config.source_id == "hackernews":
    #     return HackerNewsAdapter(config)  # Already commented out!
```

Scraping workflow (line 204-267):
```python
def scrape_date_range(start_date, end_date, source_ids=None):
    # For each date in range:
    #   For each source:
    #     Get adapter
    #     Call adapter.scrape_date(date)
    #     Merge responses
```

### Standard Response Format

All adapters must return:
```python
{
  "source_id": str,
  "articles": [
    {
      "title": str,
      "url": str,
      "category": str,  # Display name (e.g., "TLDR Tech")
      "date": str,      # YYYY-MM-DD format
      "source_id": str,
      "newsletter_type": str,  # Type within source (e.g., "tech", "top")
      "section_title": str | None,
      "section_emoji": str | None,
      "section_order": int | None,
      "removed": bool
    }
  ],
  "issues": [
    {
      "date": str,
      "newsletter_type": str,
      "category": str,
      "title": str | None,
      "subtitle": str | None,
      "sections": list[dict] | None,
      "source_id": str
    }
  ]
}
```

## Integration Analysis

### Architectural Mismatches

#### 1. Date-Based URL Pattern Assumption
**Current**: `fetch_issue(date, newsletter_type)` assumes URL like `{base_url}/{type}/{date}`

**HackerNews Reality**:
- API endpoints: `https://hacker-news.firebaseio.com/v0/topstories.json`
- No date parameter in URLs
- Returns latest stories only, not historical archives

**Impact**: Cannot directly implement `fetch_issue()` as designed

#### 2. HTML-to-Markdown Conversion
**Current**: Assumes HTML input, uses BeautifulSoup + MarkItDown (line 117-131 in newsletter_adapter.py)

**HackerNews Reality**:
- API returns structured JSON
- No HTML parsing needed
- Already have structured data (Item objects)

**Impact**: Conversion step unnecessary and wasteful

#### 3. Time Range Filtering
**Current**: Fetch content for specific date, get all content for that date

**HackerNews Reality**:
- Can only fetch latest N stories
- Must filter client-side by `submission_time`
- No guarantees about date coverage (if a date had 200 stories but API returns top 100, some are missed)

**Impact**: Need to fetch large batches and filter

#### 4. Newsletter Types vs Story Categories
**Current**: `types` in config represents subtypes within a source (e.g., ["tech", "ai"])

**HackerNews**: Story categories are fundamentally different:
- "top" - algorithmically ranked stories
- "new" - chronologically newest
- "ask" - Ask HN posts
- "show" - Show HN posts
- "job" - job postings

**Mapping Decision**: Treat HN story types as newsletter types
- `types: ["top", "new", "ask", "show", "job"]`
- `category_display_names: {"top": "HN Top", "new": "HN New", ...}`

### Compatibility Assessment

| Aspect | Compatible? | Notes |
|--------|-------------|-------|
| Response format | ✅ Yes | Can map Item → article dict |
| Source registration | ✅ Yes | Add to NEWSLETTER_CONFIGS |
| Factory pattern | ✅ Yes | Add elif in _get_adapter_for_source |
| Multi-source merging | ✅ Yes | Existing merger is source-agnostic |
| Template method | ⚠️ Partial | Need to override `scrape_date()` |
| Date-based fetching | ❌ No | Need flexible override mechanism |
| HTML parsing | ❌ No | Not applicable for API sources |

## Integration Approaches

### Option 1: Override Template Method ✅ RECOMMENDED

Make `scrape_date()` overridable:

```python
# In NewsletterAdapter base class
def scrape_date(self, date: str) -> dict:
    """Template method - can be overridden by subclasses"""
    # Current implementation for HTML-based sources
    # ...
```

```python
# In HackerNewsAdapter
def scrape_date(self, date: str) -> dict:
    """Override for API-based fetching and filtering"""
    articles = []

    for story_type in self.config.types:  # ["top", "new", "ask", ...]
        # Fetch latest stories from API
        stories = self._fetch_stories_by_type(story_type, limit=500)

        # Filter by date
        target_date = datetime.fromisoformat(date).date()
        filtered = [s for s in stories if s.submission_time.date() == target_date]

        # Convert to article format
        for story in filtered:
            articles.append(self._story_to_article(story, date, story_type))

    return self._normalize_response(articles, issues=[])
```

**Pros**:
- Minimal changes to abstraction
- Template method pattern supports overriding
- Keeps response format standardized
- Other sources unaffected

**Cons**:
- HackerNewsAdapter bypasses some base class logic
- Less code reuse for API-based sources

### Option 2: Separate API Adapter Hierarchy

Create two base classes:
- `HtmlNewsletterAdapter(NewsletterAdapter)` - current implementation
- `ApiNewsletterAdapter(NewsletterAdapter)` - new base for APIs

**Pros**:
- Clean separation of concerns
- Better code organization for future API sources

**Cons**:
- More refactoring required
- Need to move existing TLDR logic to HtmlNewsletterAdapter
- Higher risk of breaking existing functionality

### Option 3: Force-Fit into Current Pattern

Make HackerNews pretend to be HTML-based:
- Fetch stories
- Convert JSON to pseudo-HTML
- Convert back to markdown
- Parse with regex

**Pros**: None

**Cons**:
- Extremely inefficient
- Awkward and unnatural
- Wastes conversion cycles
- Not recommended

## Recommended Approach

**Use Option 1: Override Template Method**

### Implementation Strategy

1. **Make minimal changes to NewsletterAdapter**:
   - Remove `@abstractmethod` decorators from `fetch_issue`, `parse_articles`, `extract_issue_metadata`
   - Add default implementations that raise NotImplementedError
   - Keep `scrape_date()` as overridable (not abstract)

2. **Create HackerNewsAdapter**:
   - Override `scrape_date()` entirely
   - Implement `_fetch_stories_by_type(story_type, limit)`
   - Implement `_story_to_article(story, date, story_type)`
   - Use `_normalize_response()` from base class

3. **Add HackerNews config**:
   ```python
   "hackernews": NewsletterSourceConfig(
       source_id="hackernews",
       display_name="Hacker News",
       base_url="https://hacker-news.firebaseio.com/v0",
       url_pattern="",  # Not used for APIs
       types=["top", "new", "ask", "show", "job"],
       user_agent="Mozilla/5.0 (compatible; Newsletter-Aggregator/1.0)",
       article_pattern="",  # Not used for APIs
       section_emoji_enabled=False,
       category_display_names={
           "top": "HN Top",
           "new": "HN New",
           "ask": "HN Ask",
           "show": "HN Show",
           "job": "HN Jobs"
       },
       sort_order=3,  # After TLDR AI (1) and TLDR Tech (2)
   )
   ```

4. **Update factory**:
   ```python
   def _get_adapter_for_source(config):
       if config.source_id.startswith("tldr_"):
           return TLDRAdapter(config)
       elif config.source_id == "hackernews":
           return HackerNewsAdapter(config)
       else:
           raise ValueError(f"No adapter registered for source: {config.source_id}")
   ```

### Limitations to Accept

1. **No historical data**: Can only get stories that are currently in the API's "latest" feeds
2. **Incomplete coverage**: If a date had more stories than API returns, some will be missed
3. **No issue metadata**: HackerNews doesn't have newsletter-style issues, so `issues` array will be empty
4. **No sections**: HackerNews stories don't have sections like TLDR does

## Code References

### Key Files
- `newsletter_adapter.py` - Abstract base class (lines 19-154)
- `newsletter_config.py` - Configuration schema (lines 11-58)
- `newsletter_scraper.py` - Factory and orchestration (lines 16-267)
- `tldr_adapter.py` - Reference implementation (lines 45-421)
- `newsletter_merger.py` - Source-agnostic merger (lines 15-224)

### Entry Points
- `serve.py:36` - `/api/scrape` endpoint accepts `sources` parameter
- `tldr_app.scrape_newsletters()` - Main scraping function
- `newsletter_scraper.scrape_date_range()` - Core scraper

## Conclusion

**Yes, HackerNews can be integrated**, but the abstraction needs **minor modifications**:

1. Make `scrape_date()` overridable (remove abstract constraint from helper methods)
2. Allow adapters to bypass HTML conversion when not needed
3. Accept that API sources work differently from HTML sources

The recommended approach (Option 1) requires minimal changes while maintaining the existing architecture's integrity. The main trade-off is accepting HackerNews's limitations around historical data access.
