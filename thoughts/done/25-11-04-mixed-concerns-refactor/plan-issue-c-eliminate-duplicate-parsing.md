---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Mixed Concerns Refactoring Plan

## Executive Summary

**Issue C**: `tldr_adapter.py` parses the same markdown content twice, duplicating parsing logic between `parse_articles()` and `extract_issue_metadata()`.

This plan provides a pragmatic refactoring solution that improves code maintainability while preserving existing behavior and test compatibility.

### Issue C: tldr_adapter.py Parsing Same Content Twice

**Location**: `/home/user/TLDRScraper/tldr_adapter.py`

**Duplicate Logic**:

Both `parse_articles()` (lines 99-230) and `extract_issue_metadata()` (lines 232-338) independently:
1. Split markdown into lines
2. Compile heading pattern regex
3. Loop through all lines
4. Detect heading levels
5. Track section emoji/title/order
6. Build NewsletterSection objects

**Problems**:
- Performance: Parsing entire document twice per issue (2 passes through potentially 500+ line markdown documents)
- Maintainability: Same parsing logic in two places must be kept in sync
- Bug risk: Fix applied to one method may not be applied to the other

**Shared Logic** (duplicated):
- Lines 112-130 vs 245-257: Pattern compilation and section tracking setup
- Lines 138-183 vs 265-318: Heading detection and section building logic
- Lines 186-189 vs 321-324: Symbol-only line detection

**Current Usage**:
- Both called by: `NewsletterAdapter.scrape_date()` at lines 126 and 134
- Both receive: Same markdown string from `_html_to_markdown()`


### Solution C: Parse Markdown Once, Use Twice

Create a shared parsing method that both functions consume:

```python
@dataclass
class ParsedMarkdown:
    """Structured result from parsing markdown once."""
    issue_title: str | None
    issue_subtitle: str | None
    sections: list[NewsletterSection]
    sections_by_order: dict[int, NewsletterSection]
    article_candidates: list[dict]  # Raw links with section context


def _parse_markdown_structure(
    self,
    markdown: str,
    date: str,
    newsletter_type: str
) -> ParsedMarkdown:
    """Parse markdown once into structured format.

    Extracts all structure (headings, sections, links) in a single pass.
    """
    lines = markdown.split("\n")
    heading_pattern = re.compile(r"^(#+)\s*(.*)$")

    issue_title = None
    issue_subtitle = None
    sections: list[NewsletterSection] = []
    sections_by_order: dict[int, NewsletterSection] = {}
    article_candidates: list[dict] = []

    current_section_order: int | None = None
    pending_section_emoji = None
    section_counter = 0

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        # Detect headings
        heading_match = heading_pattern.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            if not text:
                continue

            # Level 1: issue title
            if level == 1 and issue_title is None:
                issue_title = text
                pending_section_emoji = None
                continue

            # Level 2 after title: subtitle
            if level <= 2 and issue_title is not None and issue_subtitle is None:
                issue_subtitle = text
                pending_section_emoji = None
                continue

            # Level 2+ headings: sections
            if level >= 2:
                # Symbol-only heading logic...
                # Section creation logic...
                # (unified from both methods)
                continue

        # Symbol-only line detection
        if self._is_symbol_only_line(line):
            pending_section_emoji = line.strip()
            continue

        # Extract all links as article candidates
        link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for title, url in link_matches:
            if not url.startswith("http"):
                continue
            if self._is_file_url(url):
                continue

            article_candidates.append({
                'title': title,
                'url': url,
                'section_order': current_section_order,
            })

    return ParsedMarkdown(
        issue_title=issue_title,
        issue_subtitle=issue_subtitle,
        sections=sections,
        sections_by_order=sections_by_order,
        article_candidates=article_candidates,
    )


def parse_articles(
    self,
    markdown: str,
    date: str,
    newsletter_type: str
) -> list[dict]:
    """Parse articles from markdown (using single-pass parsing)."""
    # Parse once
    parsed = self._parse_markdown_structure(markdown, date, newsletter_type)

    # Filter candidates by article pattern
    article_pattern = re.compile(self.config.article_pattern, re.IGNORECASE)
    category = self.config.category_display_names.get(
        newsletter_type, f"TLDR {newsletter_type.capitalize()}"
    )

    articles = []
    for candidate in parsed.article_candidates:
        if not article_pattern.search(candidate['title']):
            continue

        # Clean and format article
        cleaned_title = candidate['title'].strip()
        cleaned_title = re.sub(r"^#+\s*", "", cleaned_title)
        cleaned_title = re.sub(r"^\s*\d+\.\s*", "", cleaned_title)

        article = {
            "title": cleaned_title,
            "url": candidate['url'].strip(),
            "category": category,
            "date": util.format_date_for_url(date),
            "newsletter_type": newsletter_type,
        }

        # Add section info if available
        section_order = candidate['section_order']
        if section_order is not None:
            section = parsed.sections_by_order.get(section_order)
            if section:
                article["section_title"] = section.title
                if section.emoji:
                    article["section_emoji"] = section.emoji
                article["section_order"] = section_order

        articles.append(article)

    return articles


def extract_issue_metadata(
    self,
    markdown: str,
    date: str,
    newsletter_type: str
) -> dict | None:
    """Extract issue metadata (using single-pass parsing)."""
    # Parse once
    parsed = self._parse_markdown_structure(markdown, date, newsletter_type)

    # Return None if no metadata found
    if not parsed.issue_title and not parsed.issue_subtitle and not parsed.sections:
        return None

    category = self.config.category_display_names.get(
        newsletter_type, f"TLDR {newsletter_type.capitalize()}"
    )

    issue = NewsletterIssue(
        date=util.format_date_for_url(date),
        newsletter_type=newsletter_type,
        category=category,
        title=parsed.issue_title,
        subtitle=parsed.issue_subtitle,
        sections=parsed.sections,
    )

    return asdict(issue)
```

**Benefits**:
- Eliminates redundant parsing (performance improvement)
- Single source of truth for parsing logic
- Easier to maintain: fix once, benefits both functions
- Clearer separation: parsing vs. filtering/formatting
- Maintains exact same output (backward compatible)

## Implementation Plan


**Step 1**: Create `ParsedMarkdown` dataclass
- Define structure for parsed markdown result
- Fields: issue_title, issue_subtitle, sections, sections_by_order, article_candidates

**Step 2**: Create `_parse_markdown_structure()`
- Merge common logic from both methods
- Single loop through markdown lines
- Extract headings, sections, and link candidates
- Return `ParsedMarkdown` instance

**Step 3**: Refactor `parse_articles()` to use `_parse_markdown_structure()`
- Call `_parse_markdown_structure()` once
- Filter article_candidates by article_pattern
- Apply existing formatting logic
- Verify: Article output unchanged

**Step 4**: Refactor `extract_issue_metadata()` to use `_parse_markdown_structure()`
- Call `_parse_markdown_structure()` once
- Build NewsletterIssue from parsed result
- Verify: Metadata output unchanged

**Step 5**: Remove old duplicate code
- Clean up any unreachable code
- Ensure `_is_symbol_only_line()` still used appropriately

**Step 6**: Verification
- Run existing tests (if any)
- Manual testing with `curl http://localhost:5001/api/scrape`
- Compare article/issue data before/after (should be identical)

## Testing Strategy

### Automated Testing

**For Issue B refactor**:
- If unit tests exist for `_build_scrape_response()`, they should pass unchanged
- If integration tests exist for `/api/scrape`, they should pass unchanged

**For Issue C refactor**:
- If unit tests exist for `parse_articles()` or `extract_issue_metadata()`, they should pass unchanged
- If integration tests exist for TLDRAdapter, they should pass unchanged

### Manual Testing

**Setup**:
```bash
source ./setup.sh
start_server_and_watchdog
print_server_and_watchdog_pids
```

**Test Case 1**: Basic scrape
```bash
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-11-01",
    "end_date": "2024-11-01",
    "excluded_urls": []
  }' | jq '.'
```

**Verify**:
- Response has `success: true`
- `articles` array populated
- `issues` array populated
- `stats` object present with expected fields
- `output` contains markdown

**Test Case 2**: Multi-day scrape
```bash
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-11-01",
    "end_date": "2024-11-03",
    "excluded_urls": []
  }' | jq '.stats'
```

**Verify**:
- `dates_processed` equals 3
- `dates_with_content` <= 3
- Articles grouped correctly by date

**Test Case 3**: Excluded URLs
```bash
curl -X POST http://localhost:5001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-11-01",
    "end_date": "2024-11-01",
    "excluded_urls": ["example.com/article1", "example.com/article2"]
  }' | jq '.articles | length'
```

**Verify**:
- Excluded URLs not in response

**Cleanup**:
```bash
kill_server_and_watchdog
```


## Risks & Considerations

### Risk: Breaking Backward Compatibility

**Mitigation**:
- Preserve exact function signatures
- Preserve exact response structure
- Run regression tests after each step

## Conclusion

