---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Code Duplication Refactoring Plan

## Executive Summary

**Issue A**: ~140 lines of duplicated section parsing logic in `tldr_adapter.py`.

This issue can be resolved with straightforward refactoring that reduces complexity and maintenance burden without over-engineering.

## Issue A: Section Parsing Logic Duplication in TLDRAdapter

### Problem Analysis

**Location**: `/home/user/TLDRScraper/tldr_adapter.py`

**Duplicated code**:
- `parse_articles()` (lines 124-184)
- `extract_issue_metadata()` (lines 256-319)

Both methods contain nearly identical section parsing logic (~60 lines):
- Iterate over markdown lines
- Detect headings with regex pattern `^(#+)\s*(.*)$`
- Handle symbol-only lines (emoji markers)
- Extract emojis from heading text
- Track `pending_section_emoji` state
- Build `NewsletterSection` objects with order, title, emoji

**Key difference**: `parse_articles()` needs to attach section info to articles, while `extract_issue_metadata()` also extracts issue title/subtitle.

### Solution

Extract the common section parsing logic into a private helper method `_parse_sections()`.

**New method signature**:
```python
@staticmethod
def _parse_sections(
    lines: list[str],
    heading_pattern: re.Pattern,
    extract_issue_metadata: bool = False
) -> tuple[list[NewsletterSection], dict]:
    """Parse sections from markdown lines.

    Args:
        lines: List of markdown lines
        heading_pattern: Compiled regex for detecting headings
        extract_issue_metadata: If True, also extract issue title/subtitle

    Returns:
        Tuple of (sections list, metadata dict with optional 'title'/'subtitle')
    """
```

**Implementation approach**:
1. Extract the section parsing loop into `_parse_sections()`
2. Handle both use cases with `extract_issue_metadata` flag
3. Return sections list + metadata dict (title/subtitle when flag is True)
4. Update `parse_articles()` to call `_parse_sections(extract_issue_metadata=False)`
5. Update `extract_issue_metadata()` to call `_parse_sections(extract_issue_metadata=True)`

**Benefits**:
- Eliminates ~60 lines of duplication
- Centralizes section parsing logic
- Bug fixes only need to be applied once
- Easier to test (can test section parsing in isolation)

**Risks**: None. Pure refactoring with no behavior change.


## Implementation Plan


1. Create `_parse_sections()` helper method
2. Update `parse_articles()` to use it
3. Update `extract_issue_metadata()` to use it
4. Test with TLDR Tech and TLDR AI newsletters
5. Verify section emoji extraction still works correctly

## Testing Strategy

### Manual Testing Checklist

**Issue A (Section parsing)**:
- [ ] Scrape TLDR Tech newsletter - verify sections appear correctly
- [ ] Scrape TLDR AI newsletter - verify sections appear correctly
- [ ] Check articles have correct section titles and emojis
- [ ] Check issue metadata has correct sections list



All changes are pure refactoring with no external API changes:
- **Issue A**: If section parsing breaks, revert `tldr_adapter.py` to previous version
- **Issue B**: If storage breaks, revert all 6 files and `storageKeys.js`
