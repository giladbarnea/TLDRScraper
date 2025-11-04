---
last-updated: 2025-11-04 20:55, ef64294
status: complete
---
# Remove Summarize Feature Implementation Plan

## Overview

Remove the entire Summarize feature from the TLDRScraper application, end-to-end through the call stack. This is a surgical removal that preserves the parallel TLDR feature (which shares infrastructure but operates independently).

## Current State Analysis

The Summarize feature is deeply integrated across the stack:

**Client (React 19):**
- `useSummary` hook manages both summary and TLDR (via `type` parameter)
- `ArticleCard` component renders Summarize button and expanded content
- localStorage caches summary data under each article object
- CSS styles for button states and expanded content

**Backend:**
- Flask endpoint `/api/summarize-url` in `serve.py:88-123`
- Application layer in `tldr_app.py:36-51`
- Service layer in `tldr_service.py:85-116`
- Core logic in `summarizer.py:292-309`
- GitHub-hosted prompt template fetching

**Key Discovery**: The `useSummary` hook is **dual-purpose** - it handles both `'summary'` and `'tldr'` via a `type` parameter. This means we cannot delete the entire hook, only remove summary-specific usage and keep the hook intact for TLDR.

## Desired End State

After completion, the project will have:
- ✅ TLDR feature fully functional and unchanged
- ❌ No Summarize button in UI
- ❌ No "Copy summary" functionality
- ❌ No `/api/summarize-url` endpoint
- ❌ No `summarize_url()` functions in backend
- ❌ No GitHub template fetching for `summarize.md`
- ❌ No `summary` object in article localStorage data

### Verification Criteria

Run these commands to verify complete removal:

```bash
# Client: No references to 'summary' (excluding comments, allowing 'summarize' in filenames)
grep -r "summary" client/src --include="*.js" --include="*.jsx" --include="*.css" | \
  grep -v "tldr" | grep -v "\/\/" | grep -v "\/\*" || echo "✓ No summary refs found"

# Backend: No summarize_url endpoint
grep -r "summarize-url" . --include="*.py" || echo "✓ No summarize endpoint found"

# Backend: No summarize functions
grep -r "def summarize_url" . --include="*.py" || echo "✓ No summarize functions found"

# Backend: No summarize prompt fetching
grep -r "_fetch_summarize_prompt\|summarize\.md" . --include="*.py" || echo "✓ No summarize prompts found"
```

## What We're NOT Doing

- **NOT removing** the `useSummary` hook entirely (TLDR needs it)
- **NOT removing** any TLDR functionality
- **NOT removing** `useArticleState` or localStorage mechanisms (TLDR needs them)
- **NOT removing** the shared `scrape_url()`, `url_to_markdown()`, or `_call_llm()` functions (TLDR needs them)
- **NOT removing** the cache merge logic
- **NOT removing** markdown rendering infrastructure (marked + DOMPurify)

## Implementation Approach

**Strategy**: Work **bottom-up** through the stack (storage → backend → frontend UI) to ensure we don't break dependent layers.

**Rationale**:
1. Remove storage schema first so data doesn't persist
2. Remove backend endpoints so UI can't accidentally call them
3. Remove UI last since it becomes non-functional once backend is gone

## Phase 1: Remove Summary from localStorage Schema

### Overview
Remove the `summary` object from article data structures in localStorage without affecting TLDR or other article properties.

### Changes Required:

#### 1. Client localStorage Data Migration
**File**: `client/src/lib/scraper.js`
**Changes**: Remove default summary object initialization

```javascript
// REMOVE lines 99-100:
// summary: { status: 'unknown', markdown: '', effort: 'low', checkedAt: null, errorMessage: null },
// Keep tldr: line 100
```

**File**: `client/src/hooks/useArticleState.js`
**Changes**: None needed - this is a generic state manager

**File**: `client/src/composables/useScraper.js` (if exists)
**Changes**: Same as above for Vue version

### Success Criteria:

#### Automated Verification:
- [x] Search for `summary:` in client/src/lib/scraper.js returns zero results: `grep -n "summary:" client/src/lib/scraper.js`
- [x] No syntax errors: `cd client && npm run build`

#### Manual Verification:
- [ ] Open browser DevTools → Application → Local Storage
- [ ] Check `newsletters:scrapes:*` keys - new articles should not have `summary` object
- [ ] Existing cached articles can keep their `summary` objects (won't hurt anything)

**Implementation Note**: After completing this phase and all automated verification passes, proceed immediately to Phase 2 (no manual pause needed - storage changes are non-breaking).

---

## Phase 2: Remove Backend Summarize Endpoint and Logic

### Overview
Remove the `/api/summarize-url` Flask endpoint and all backend functions that support summarization.

### Changes Required:

#### 1. Remove Flask Route
**File**: `serve.py`
**Changes**: Delete the entire `/api/summarize-url` route

```python
# DELETE lines 88-123:
@app.route("/api/summarize-url", methods=["POST"])
def summarize_url():
    """..."""
    # ... entire function body
```

#### 2. Remove Prompt Template Endpoint
**File**: `serve.py`
**Changes**: Remove the `/api/prompt` endpoint for summarize template debugging

```python
# DELETE lines 68-85:
@app.route("/api/prompt", methods=["GET"])
def get_summarize_prompt_template():
    """..."""
    # ... entire function body
```

#### 3. Remove Application Layer Functions
**File**: `tldr_app.py`
**Changes**: Remove summarize functions

```python
# DELETE lines 28-29:
def get_summarize_prompt_template() -> str:
    return tldr_service.fetch_summarize_prompt_template()

# DELETE lines 36-51:
def summarize_url(
    url: str,
    *,
    summary_effort: str = "low",
) -> dict:
    # ... entire function body
```

#### 4. Remove Service Layer Functions
**File**: `tldr_service.py`
**Changes**: Remove service functions

```python
# DELETE lines 77-78:
def fetch_summarize_prompt_template() -> str:
    return _fetch_summarize_prompt()

# DELETE lines 85-116:
def summarize_url_content(
    url: str,
    *,
    summary_effort: str = "low",
) -> dict:
    # ... entire function body
```

#### 5. Remove Core Summarizer Functions
**File**: `summarizer.py`
**Changes**: Remove summarize-specific functions and constants

```python
# DELETE line 17:
_PROMPT_CACHE = None

# DELETE lines 292-309:
def summarize_url(url: str, summary_effort: str = "low") -> str:
    """..."""
    # ... entire function body

# DELETE lines 385-397:
def _fetch_summarize_prompt() -> str:
    """..."""
    # ... entire function body

# UPDATE line 332-382 (_fetch_prompt):
# This function is generic and used by both summarize and TLDR.
# Remove the summarize-specific docstring example, but KEEP the function.
# Change docstring from:
#   """Fetch prompt template from GitHub (used by summarize and TLDR)"""
# To:
#   """Fetch prompt template from GitHub (used by TLDR)"""
```

**Note**: Keep the following functions intact (they're shared with TLDR):
- `url_to_markdown()` - Used by TLDR
- `scrape_url()` - Used by TLDR
- `_call_llm()` - Used by TLDR
- `_insert_markdown_into_template()` - Used by TLDR (with `<tldr this>` tags)
- `_fetch_prompt()` - Generic function, keep it
- `_TLDR_PROMPT_CACHE` - Keep it
- `SUMMARY_EFFORT_OPTIONS` - Keep it (TLDR uses it)
- `normalize_summary_effort()` - Keep it (TLDR uses it)

### Success Criteria:

#### Automated Verification:
- [x] No summarize endpoint exists: `grep -n "@app.route.*summarize-url" serve.py || echo "✓ Endpoint removed"`
- [x] No summarize functions in tldr_app: `grep -n "def summarize_url\|def get_summarize_prompt" tldr_app.py || echo "✓ Functions removed"`
- [x] No summarize functions in tldr_service: `grep -n "def summarize_url_content\|def fetch_summarize_prompt" tldr_service.py || echo "✓ Functions removed"`
- [x] No summarize functions in summarizer: `grep -n "def summarize_url\|def _fetch_summarize_prompt" summarizer.py || echo "✓ Functions removed"`
- [x] Python syntax valid: `cd /Users/giladbarnea/dev/TLDRScraper && python3 -m py_compile serve.py tldr_app.py tldr_service.py summarizer.py`
- [x] Server starts without errors: `source setup.sh && start_server_and_watchdog && sleep 3 && print_server_and_watchdog_pids`

#### Manual Verification:
- [x] Server running and logs show no errors
- [x] TLDR endpoint still works: `curl -X POST http://localhost:5001/api/tldr-url -H "Content-Type: application/json" -d '{"url": "https://example.com"}' -w "\n%{http_code}\n"`
- [x] Summarize endpoint returns 404: `curl -X POST http://localhost:5001/api/summarize-url -H "Content-Type: application/json" -d '{"url": "https://example.com"}' -w "\n%{http_code}\n"` (should see 404)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that:
1. The server starts successfully
2. TLDR functionality still works via API
3. Summarize endpoint correctly returns 404

Then proceed to Phase 3.

---

## Phase 3: Remove Frontend Summarize UI and Logic

### Overview
Remove all UI elements, event handlers, and state management for the Summarize feature from the React frontend.

### Changes Required:

#### 1. Remove Summarize from ArticleCard Component
**File**: `client/src/components/ArticleCard.jsx`
**Changes**: Remove summary hook usage and UI elements

```javascript
// REMOVE line 12:
const summary = useSummary(article.issueDate, article.url, 'summary')

// REMOVE lines 37-52: handleLinkClick function that toggles summary
// Replace with simpler version that just marks as read:
const handleLinkClick = (e) => {
  if (isRemoved) return
  if (e.ctrlKey || e.metaKey) return

  if (!isRead) {
    toggleRead()
  }
}

// REMOVE lines 106-112: Summarize button and split-button container
<div className="expand-btn-container">
  <button className={`article-btn expand-btn ...`}>
    {summary.buttonLabel}
  </button>
  <button className="article-btn expand-chevron-btn">▾</button>
</div>

// REMOVE lines 134-138: Copy summary button
{summary.isAvailable && (
  <button className="article-btn copy-summary-btn visible">
    ...
  </button>
)}

// REMOVE lines 169-172: Inline summary display
{summary.expanded && summary.html && (
  <div className="inline-summary">
    <strong>Summary</strong>
    <div dangerouslySetInnerHTML={{ __html: summary.html }} />
  </div>
)}
```

#### 2. Remove onCopySummary Prop Chain
**File**: `client/src/components/ArticleList.jsx`
**Changes**: Remove the prop (it was only used for summary copying)

```javascript
// REMOVE line 5: onCopySummary prop from function signature
function ArticleList({ articles, onCopySummary })
// Change to:
function ArticleList({ articles })

// REMOVE line 96: onCopySummary prop pass-through to ArticleCard
onCopySummary={onCopySummary}
```

**File**: `client/src/components/ResultsDisplay.jsx`
**Changes**: Remove handler and prop

```javascript
// REMOVE lines 18-20: handleCopySummary function
const handleCopySummary = () => { ... }

// REMOVE line 45: onCopySummary prop in ArticleList
<ArticleList articles={payload.articles} onCopySummary={handleCopySummary} />
// Change to:
<ArticleList articles={payload.articles} />

// REMOVE line 60: onCopySummary prop from DailyResults signature
function DailyResults({ payload, onCopySummary })
// Change to:
function DailyResults({ payload })

// REMOVE lines 101, 109: onCopySummary prop forwarding
onCopySummary={onCopySummary}
```

#### 3. Remove Summary-Specific CSS
**File**: `client/src/components/ArticleCard.css`
**Changes**: Remove summary button and content styles

```css
/* DELETE lines 159-196: Summarize button split-button styles */
.expand-btn-container { ... }
.expand-btn { ... }
.expand-chevron-btn { ... }
.expand-btn.loaded { ... }
.expand-btn.loaded:hover { ... }
.expand-btn.loaded.expanded { ... }

/* DELETE lines 223-240: Copy summary button styles */
.copy-summary-btn { ... }
.copy-summary-btn.visible { ... }
.copy-summary-btn.visible:hover { ... }

/* DELETE lines 268-297: Inline summary content styles */
.inline-summary { ... }
.inline-summary strong { ... }

/* KEEP lines 312-315: Media query for button sizing (TLDR uses it) */

/* KEEP all .tldr-btn styles - TLDR feature stays */
```

#### 4. Update useSummary Hook (Rename/Refactor)
**File**: `client/src/hooks/useSummary.js`
**Changes**: Add validation to prevent 'summary' type usage

```javascript
// UPDATE line 6: Add type validation at the top of the hook
export function useSummary(date, url, type = 'summary') {
  // ADD THIS CHECK:
  if (type === 'summary') {
    throw new Error('Summary feature has been removed. Use type="tldr" instead.')
  }

  // ... rest of hook unchanged
}
```

**Alternative (more aggressive)**: Rename the hook to `useTldr` and update all call sites. But this is optional since the validation above prevents misuse.

### Success Criteria:

#### Automated Verification:
- [x] No summary hook usage in ArticleCard: `grep -n "useSummary.*'summary'" client/src/components/ArticleCard.jsx || echo "✓ No summary usage"`
- [x] No onCopySummary prop in components: `grep -rn "onCopySummary" client/src/components || echo "✓ Prop removed"`
- [x] No summary CSS classes: `grep -n "\.expand-btn\|\.copy-summary-btn\|\.inline-summary" client/src/components/ArticleCard.css || echo "✓ CSS removed"`
- [x] Client builds without errors: `cd client && npm run build`
- [x] Type check passes (if using TypeScript): `cd client && npm run type-check` (N/A - not using TypeScript)

#### Manual Verification:
- [ ] Start the dev server: `cd client && npm run dev`
- [ ] Open http://localhost:3000 in browser
- [ ] Scrape some newsletters (any date range)
- [ ] Verify NO "Summarize" button appears on article cards
- [ ] Verify NO "Copy summary" button appears
- [ ] Verify TLDR button still works correctly (fetch, expand, collapse)
- [ ] Verify clicking article title marks it as read (no summary expansion)
- [ ] Verify no console errors about missing `summary` variable

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that:
1. The UI no longer shows any Summarize-related elements
2. TLDR functionality remains fully operational
3. No console errors or warnings appear

Then proceed to Phase 4 (cleanup).

---

## Phase 4: Cleanup and Documentation

### Overview
Remove any remaining references, update documentation, and verify the system is clean.

### Changes Required:

#### 1. Update Architecture Documentation
**File**: `ARCHITECTURE.md`
**Changes**: Remove Summarize feature documentation

```markdown
# DELETE lines 58-59: Summarize endpoint from routes diagram
POST /api/summarize-url

# DELETE lines 65: summarize_url() from app logic
- summarize_url()

# DELETE lines 73: summarize_url_content() from service layer
- summarize_url_content()

# DELETE lines 81-82: summarize_url() from summarizer
- summarize_url()

# DELETE Section "Feature 4: Summary Generation" (lines 134-143)
### 4. Summary Generation
...entire section...

# DELETE State Machine Section (lines 313-360)
### Feature 4: Summary Generation
...entire section...

# DELETE Call Graph Section (lines 643-804)
### Feature 4: Summary Generation - Complete Flow
...entire section...

# UPDATE line 915-921: Remove summary object from Article data structure
  // AI-generated content
  summary: { ... },  // DELETE THIS

  tldr: { ... }  // KEEP THIS
```

**File**: `README.md` (if it documents Summarize)
**Changes**: Remove any Summarize feature mentions

#### 2. Search and Destroy Remaining References
Run comprehensive searches:

```bash
# Find any remaining 'summarize' (case-insensitive) in Python files
grep -rni "summarize" --include="*.py" .

# Find any remaining 'summary' in client code (excluding node_modules)
grep -rni "summary" client/src --include="*.js" --include="*.jsx" --include="*.css"

# Find any remaining API references
grep -rn "summarize-url" .
```

Manually review results and remove any stragglers.

#### 3. Remove Unused Dependencies (if any)
Check if any dependencies were ONLY used for Summarize:

```bash
# Check client package.json
cat client/package.json | grep -E "marked|dompurify"

# If these are ONLY used by summary (not TLDR), remove them:
# cd client && npm uninstall marked dompurify
```

**Note**: Based on research, `marked` and `DOMPurify` are used by TLDR too, so keep them.

### Success Criteria:

#### Automated Verification:
- [x] No 'summarize' in Python (excluding comments): `grep -rn "summarize" --include="*.py" . | grep -v "#" | grep -v '"""' || echo "✓ Clean"`
- [x] No 'summary' in client (excluding node_modules, allowing tldr): Remaining references are in unused Vue composables and HTML summary tag (unrelated)
- [x] Full test suite passes (if exists): Client builds successfully

#### Manual Verification:
- [ ] Read updated ARCHITECTURE.md - no Summarize references
- [ ] Full end-to-end test: Scrape → View → Click TLDR → Verify works
- [ ] Check browser DevTools → Network tab - no requests to `/api/summarize-url`
- [ ] Check server logs - no warnings or errors about missing functions

**Implementation Note**: After completing this phase and all automated verification passes, perform a final comprehensive manual test:
1. Restart the server fresh: `kill_server_and_watchdog && start_server_and_watchdog`
2. Clear browser localStorage: DevTools → Application → Clear site data
3. Perform a full workflow: Scrape → Read articles → Generate TLDRs
4. Confirm no errors in console or server logs

If all tests pass, the implementation is complete!

---

## Testing Strategy

### Unit Tests (if they exist):
- Remove any tests for `summarize_url()` functions
- Update tests for `useSummary` hook to verify error is thrown for `type='summary'`
- Verify TLDR tests still pass

### Integration Tests:
- Remove any tests that POST to `/api/summarize-url`
- Add test to verify endpoint returns 404
- Verify TLDR integration tests still pass

### Manual Testing Steps:
1. **Clean slate**: Clear localStorage, restart server
2. **Scrape newsletters**: Any date range
3. **Verify UI**: No Summarize buttons visible
4. **Test TLDR**: Click TLDR button → Should work normally
5. **Test read state**: Click article title → Should mark as read (no summary)
6. **Check Network**: DevTools → No requests to `/api/summarize-url`
7. **Check Console**: No errors or warnings
8. **Check Logs**: Server logs show no errors

---

## Migration Notes

**No data migration needed**: Existing `summary` objects in localStorage are harmless. They will persist but won't be used by the UI. Over time, as users scrape new newsletters, the data will naturally age out.

**No user communication needed**: This is a feature removal, not a migration. The UI simply won't show the Summarize button anymore.

**Rollback strategy**: If needed, revert the commit. The feature is self-contained enough that a single revert will restore it.

---

## References

- Original research: Research agents' comprehensive scan (see conversation history)
- Architecture doc: `/Users/giladbarnea/dev/TLDRScraper/ARCHITECTURE.md`
- Key files:
  - Client: `client/src/hooks/useSummary.js:6-135` (dual-purpose hook)
  - Backend: `serve.py:88-123`, `tldr_app.py:36-51`, `tldr_service.py:85-116`, `summarizer.py:292-309`
  - Storage: `client/src/lib/scraper.js:99` (default data structure)
