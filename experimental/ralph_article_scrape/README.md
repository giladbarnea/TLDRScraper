# Ralph Article Scraping Experiment

**Date:** 2025-10-25
**Source:** https://ghuntley.com/ralph/
**Objective:** Experimental exploration of article scraping with media identification and AI-enhanced descriptions

## Overview

This experiment tested scraping web articles and enhancing them with AI-generated descriptions of embedded media (images, videos, tweets, etc.).

## Files Created

1. **ralph_article_enhanced.md** - Main deliverable: Complete article with media elements replaced by contextual descriptions
2. **ralph_article_media.txt** - Catalog of all media resources found in the article
3. **article_structure.json** - Structured JSON representation of article content and media
4. **parse_article.py** - Python HTML parser used to extract article structure
5. **ralph_article.html** - Original HTML source

## Process

### 1. Setup
- Installed Gemini CLI (`@google/gemini-cli` v0.10.0)
- Attempted to use Gemini API for AI descriptions

### 2. Challenges Encountered
- Gemini CLI encountered 403 Forbidden errors with the API
- Python `google-generativeai` library had dependency issues
- Both approaches failed due to API authentication problems

### 3. Fallback Solution
- Scraped article HTML directly using curl
- Parsed HTML using custom Python HTMLParser
- Created contextual descriptions manually based on:
  - Alt text from images
  - URL patterns
  - Article context
  - Embedded tweet metadata

## Media Elements Found

Total: **12 primary media elements**

### Main Article Media (5 items):
1. Hero image (Ralph Wiggum as software engineer)
2. Playground diagram (process illustration)
3. External link (Y Combinator report)
4. Tweet about programming language creation
5. Tweet about cost comparison ($50K → $297)

### Related Content (4 items):
6. CURSED programming language article image
7. Secure code generation patterns article image
8. Coding agent workshop article image
9. MCP servers and LLM allocations article image

### Additional Elements (3 items):
10. Author profile icon
11. Decorative thumbnail
12. Analytics pixel

## Key Findings

### Article Content
The article discusses "Ralph" - a technique using AI coding agents in automated loops:
- Described as "a Bash loop" at its core
- Used for greenfield software projects
- Case study: $50K contract completed for $297
- Example: Building the CURSED programming language

### Scraping Capabilities
Successfully extracted:
- ✅ Article text content
- ✅ Image URLs and alt text
- ✅ Embedded tweet URLs and dates
- ✅ External links
- ✅ Related content metadata

### Limitations
- Could not programmatically generate AI descriptions (API issues)
- Manual description writing was time-intensive
- No actual image content analysis performed
- Tweet content not fully scraped (only URLs)

## Potential Improvements

1. **API Resolution**: Fix Gemini API authentication to enable automated descriptions
2. **Image Download**: Download images locally for multimodal AI analysis
3. **Tweet Extraction**: Use Twitter API to get full tweet content
4. **Better Parsing**: Use BeautifulSoup or more robust parser
5. **Markdown Generation**: Automate markdown creation from structured data

## Usage

To view the enhanced article:
```bash
cat ralph_article_enhanced.md
```

To examine the media catalog:
```bash
cat ralph_article_media.txt
```

To explore the structured data:
```bash
python3 -m json.tool article_structure.json
```

## Conclusion

While the Gemini CLI integration didn't work as planned, the experiment successfully demonstrated:
- Web scraping with media identification
- Content structure extraction
- Manual AI-style description generation
- Markdown enhancement with contextual descriptions

The enhanced markdown file provides a fully text-based version of the article where all visual and embedded media are replaced with detailed textual descriptions, making the content accessible and searchable.
